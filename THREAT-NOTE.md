# StockDesk - threat note

**What we protect.** (1) Stock data and the right to change it (`POST /adjust`).
(2) The credentials: DB password, API key, registry token, cluster credentials.
(3) The delivery chain itself: what code gets built, pushed and run.
(4) The shared test cluster and the other workloads on it.

**Who could attack.** An insider or the external contractor among the 40
repository readers (can open PRs, read logs); the former contractor who set it
up (may still hold credentials); a compromised upstream dependency or GitHub
Action; anyone on the Internet if the LoadBalancer is public; soon, a supplier
or a leaked supplier key.

**Trust boundaries.** PR code (untrusted) / `main` after review (trusted) -
CI runner / registry / cluster - cluster / Internet.

| # | Attack path | Cut by | What remains |
|---|---|---|---|
| 1 | **Pwn request.** A reader opens a fork PR whose `npm test` script exfiltrates `DEPLOY_TOKEN` and the write-all token, or plants a backdoor that is pushed as `:latest` and deployed. A crafted PR title does the same through shell injection. | `pull_request` (no secrets, read-only token); `permissions: {}`; secrets only in the `test` environment, on `main`; title injection removed; deploy only from `main`. | Someone with write access can still merge a malicious workflow to `main` unless branch protection and reviewers are on (plan-dependent, R24). |
| 2 | **Leaked secrets reused.** Anyone with a clone, a fork, an image pull, the CI logs or `kubectl logs` reads the DB password / API key / token and uses them. | Secrets removed from files, images (`.dockerignore`), logs (redaction) and CI logs; the deploy no longer restores the old Secret; gitleaks with Corvane's formats in CI. | **Nothing in the code revokes them: rotation by admins** (RISKS.md, plan in 10 steps). History stays in existing clones. |
| 3 | **Remote debugger.** Port 9229, published by the LoadBalancer, gives code execution in the pod: read the environment, reach the DB, move in the cluster. | Inspector removed; `ClusterIP`; non-root, read-only, no capabilities, seccomp, no SA token, Pod Security `restricted`; NetworkPolicy. | The old LoadBalancer in `default` until an admin deletes it. NetworkPolicy only works if the CNI enforces it. |
| 4 | **Supply chain.** A moved tag (`corvane-labs/...@main`, or a hijacked scanner tag as in the March 2026 trivy-action incident) runs attacker code with the cluster credentials; or an overwritten `:latest` image is deployed. | No third-party action; GitHub actions pinned to commit SHAs; scanners pinned by SHA-256; deploy by digest of the scanned image; namespace-scoped deployer instead of a possibly cluster-admin kubeconfig. | A pin freezes whatever was chosen; images not signed (no cosign / admission check); `kubectl` on the runner not pinned. |

**Not covered yet.** Supplier exposure: TLS, per-supplier keys, rate limits
(R13, R20) - recommended, not built. Runtime detection and alerting.
