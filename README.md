# StockDesk - hardened delivery chain (DevSecOps case study)

StockDesk is Corvane's small stock-tracking API (Node.js, no dependency).
This repository is the original one plus my review of its delivery chain
before it is opened to external suppliers. Corvane and every value in it are
fictional. **No real secret is in this repository**; the first commit is the
repository *as provided* (with its fictional leaked values) so that the
difference is easy to read.

| Read first | |
|---|---|
| [RISKS.md](RISKS.md) | Prioritised risks, what I did about each, and the **rotation plan for the exposed secrets** |
| [docs/RISK-PRIORITISATION.md](docs/RISK-PRIORITISATION.md) | How risks are ranked: likelihood x impact scoring scales, levels and responses, tie-breakers, residual risk after the merge and after admin actions |
| [THREAT-NOTE.md](THREAT-NOTE.md) | One page: assets, attackers, four attack paths, what cuts them |
| [DESIGN-NOTE.md](DESIGN-NOTE.md) | One page: assumptions, choices, tests, what I cut, AI use |
| `git log --stat` | One commit per step; messages reference the risk IDs |
| [docs/evidence/](docs/evidence/) | Scanner output before and after |

## What changed, at a glance

```
pull_request (fork or branch)           push to main
 read-only token, no secrets             same checks, then (environment "test"):
 ├─ checks: npm test, gitleaks,          ├─ push the exact scanned image, tag = commit SHA
 │  actionlint, hadolint,                └─ deploy by digest with kubectl
 │  kubeconform, trivy config               (namespace stockdesk, scoped deployer)
 └─ image: build, trivy scan, SBOM
```

- **Pipeline** (`.github/workflows/ci.yml`): `pull_request` instead of `pull_request_target`, least privilege, no secret in the file or the logs, no injection, deploy only from `main` through an environment, actions pinned to commit SHAs, scanners pinned by SHA-256 (`ci/install-tools.sh`), Dependabot.
- **Image** (`Dockerfile`, `.dockerignore`): `node:22-alpine`, non-root UID 10001, no debugger, only `package.json` and `src/` copied, no package manager at run time.
- **Kubernetes** (`k8s/`): dedicated namespace with Pod Security `restricted`, hardened securityContext, read-only filesystem, `ClusterIP` instead of a public LoadBalancer, separate liveness/readiness, resources, NetworkPolicy. `k8s/admin/` holds what an admin applies once (namespace, scoped CI identity).
- **App** (`src/server.js`): no secret in the startup log, `/livez`, graceful SIGTERM, constant-time key check, 1 KB body limit. Same port **3000**, same environment variable names.
- **Repo**: `.env` and `k8s/secret.yaml` removed, `.env.example`, `.gitignore`; `docker-compose.yml` is now local-dev only.

## Run and test

Requirements: Node.js 22 (`.nvmrc`; works with 18+). No Docker needed to test.

```bash
npm test                              # 10 tests: 5 original + 5 new (test/security.test.js)
cp .env.example .env && node src/server.js   # local run, port 3000
curl localhost:3000/livez             # liveness, no DB needed
curl localhost:3000/health            # readiness, 503 without a database
```

With Docker (local development only):

```bash
cp .env.example .env                  # set your own local values
docker compose up --build             # app on 127.0.0.1:3000, Postgres not published
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build   # + inspector on 127.0.0.1:9229
```

## Check the files (the same commands as the CI "checks" job)

```bash
python3 -c "import sys, yaml; [list(yaml.safe_load_all(open(f))) for f in sys.argv[1:]]; print('YAML ok')" \
  .github/workflows/ci.yml docker-compose.yml k8s/*.yaml k8s/admin/*.yaml
TOOLS_DIR=./.tools ci/install-tools.sh actionlint hadolint kubeconform gitleaks trivy && export PATH="$PWD/.tools:$PATH"
gitleaks dir --redact --config .gitleaks.toml .
actionlint && hadolint Dockerfile && kubeconform -strict -summary k8s/
trivy config --exit-code 1 --severity HIGH,CRITICAL --ignorefile .trivyignore.yaml .
```

## What I could and could not verify

| Status | What |
|---|---|
| **Tested** (run, result seen) | `npm ci` + `npm test`: 10/10 pass. The new log test fails if the old log line is restored (checked). Real process: `/livez` 200, `/health` 503 without DB, exit code 0 on SIGTERM, no secret in the log. YAML parse of every YAML file. `ci/install-tools.sh` downloads and verifies all five scanners. The deploy step's image-reference guard (5 inputs: 1 accepted, 4 rejected); it caught a gap in my first version, now fixed. `.dockerignore` checked with Docker's own matcher (moby/patternmatcher v0.6.1): only `package.json`, `package-lock.json`, `src/*` reach the build. |
| **Statically reviewed by tools** | actionlint (with shellcheck): clean. hadolint: clean. kubeconform `-strict`: 8/8 resources valid. trivy config: clean, 3 accepted findings documented in `.trivyignore.yaml`. gitleaks: no leak in the tree; finds 9 leaks in the original (6 with default rules). Output in `docs/evidence/`. |
| **Not tested** | `docker build` (no Docker here), the image scan, an actual GitHub Actions run, any deployment, the securityContext / Pod Security / NetworkPolicy behaviour on a real cluster, `docker compose up`. |
| **To verify (TODO)** | Image digests for `node:22-alpine` and `postgres:17-alpine` (registries unreachable from my environment; tags used for now). hadolint SHA-256: no upstream checksum published, value is from my download (trust on first use). The `docker buildx imagetools ... {{.Manifest.Digest}}` output format on the runner. `kubectl` version on `ubuntu-24.04` runners (not pinned). Format of the KUBECONFIG secret (raw YAML assumed). Ingress controller namespace and DB location in the NetworkPolicy. |

Commit SHAs of the GitHub actions are real: resolved with `git ls-remote` and
cross-checked by cloning each action at that tag (2026-11-23). Scanner
versions and SHA-256 values come from each project's release page / checksum
file the same day.

## Admin set-up (once, before the first deploy)

1. Delete the old resources in `default` (they are not pruned): `kubectl -n default delete service/stockdesk deployment/stockdesk secret/stockdesk-env`.
2. `kubectl apply -f k8s/admin/namespace.yaml -f k8s/admin/ci-rbac.yaml`
3. Create the Secret with **rotated** values, from a file outside the repo (not on the command line, to keep them out of shell history):
   `kubectl -n stockdesk create secret generic stockdesk-env --from-env-file=/secure/path/stockdesk.env`
   (keys: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `API_KEY` - unchanged names).
4. GitHub: create environment `test`, deployment branches = `main` only, required reviewers if available; add environment secrets `DEPLOY_TOKEN` (new, push-only) and `KUBECONFIG` (for `ci-deployer`). Delete the old repository-level `KUBECONFIG` secret.
5. Testers reach the API with `kubectl -n stockdesk port-forward svc/stockdesk 8080:80` until an Ingress exists.

## Known limitations

See RISKS.md (statuses Open / Reduced) and DESIGN-NOTE.md ("What I cut"). In
short: secrets must still be rotated by admins; supplier exposure (TLS,
per-supplier keys) is a recommendation, not built; images are not signed;
scanner pins in `ci/install-tools.sh` are not updated by Dependabot.
