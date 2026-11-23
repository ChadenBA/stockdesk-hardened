# AFTER - the CI "checks" job commands, run locally on 2026-11-23 (Node v22.23.5)

```
$ npm ci --ignore-scripts
up to date, audited 1 package in 241ms
found 0 vulnerabilities
exit=0

$ npm test
  ...
# Subtest: POST adjust refuses a negative stock
ok 10 - POST adjust refuses a negative stock
  ---
  duration_ms: 7.444522
  type: 'test'
  ...
1..10
# tests 10
# suites 0
# pass 10
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 271.247248
exit=0

$ gitleaks dir --no-banner --redact --config .gitleaks.toml .
10:58AM INF scanned ~38927 bytes (38.93 KB) in 20.3ms
10:58AM INF no leaks found
exit=0

$ actionlint
exit=0

$ hadolint Dockerfile
exit=0

$ kubeconform -strict -summary k8s/
Summary: 8 resources found in 4 files - Valid: 8, Invalid: 0, Errors: 0, Skipped: 0
exit=0

$ trivy config --skip-check-update --exit-code 1 --severity HIGH,CRITICAL --ignorefile .trivyignore.yaml .
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)
exit=0

$ python3 -I -c import sys,yaml; [list(yaml.safe_load_all(open(f))) for f in sys.argv[1:]]; print('YAML ok') .github/workflows/ci.yml .github/dependabot.yml docker-compose.yml docker-compose.debug.yml k8s/deployment.yaml k8s/networkpolicy.yaml k8s/admin/namespace.yaml k8s/admin/ci-rbac.yaml .trivyignore.yaml
YAML ok
exit=0

```

Notes: `--skip-check-update` is only used locally (the trivy checks bundle is downloaded from a registry my environment cannot reach; the built-in checks were used). In CI, trivy downloads the current checks.
