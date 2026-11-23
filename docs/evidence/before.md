# BEFORE - scans of the original repository (commit bdf884725a55e5a3ff1ab63c98bf97761f941e77)

```
# actionlint on original ci.yml
.github/workflows/ci.yml:35:34: "github.event.pull_request.title" is potentially untrusted. avoid using it directly in inline scripts. instead, pass it through an environment variable. see https://docs.github.com/en/actions/reference/security/secure-use#good-practices-for-mitigating-script-injection-attacks for more details [expression]
   |
35 |         run: echo "Building '${{ github.event.pull_request.title }}' for ${{ github.actor }}"
   |                                  ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.github/workflows/ci.yml:38:9: shellcheck reported issue in this script: SC2086:info:2:37: Double quote to prevent globbing and word splitting [shellcheck]
   |
38 |         run: |
   |         ^~~~
.github/workflows/ci.yml:43:9: shellcheck reported issue in this script: SC2086:info:1:17: Double quote to prevent globbing and word splitting [shellcheck]
   |
43 |         run: |
   |         ^~~~
.github/workflows/ci.yml:43:9: shellcheck reported issue in this script: SC2086:info:1:27: Double quote to prevent globbing and word splitting [shellcheck]
   |
43 |         run: |
   |         ^~~~
.github/workflows/ci.yml:43:9: shellcheck reported issue in this script: SC2086:info:2:13: Double quote to prevent globbing and word splitting [shellcheck]
   |
43 |         run: |
   |         ^~~~
.github/workflows/ci.yml:43:9: shellcheck reported issue in this script: SC2086:info:2:23: Double quote to prevent globbing and word splitting [shellcheck]
   |
43 |         run: |
   |         ^~~~
```

```
# hadolint on original Dockerfile
Dockerfile:1 DL3007 warning: Using latest is prone to errors if the image will ever update. Pin the version explicitly to a release tag
```

```
# trivy config (built-in checks) on original repo
Dockerfile (dockerfile)
Failures: 3 (UNKNOWN: 0, LOW: 1, MEDIUM: 1, HIGH: 1, CRITICAL: 0)
DS-0001 (MEDIUM): Specify a tag in the 'FROM' statement for image 'node'
DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument
DS-0026 (LOW): Add HEALTHCHECK instruction in your Dockerfile
Failures: 19 (UNKNOWN: 0, LOW: 11, MEDIUM: 5, HIGH: 3, CRITICAL: 0)
KSV-0001 (MEDIUM): Container 'stockdesk' of Deployment 'stockdesk' should set 'securityContext.allowPrivilegeEscalation' to false
KSV-0003 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should add 'ALL' to 'securityContext.capabilities.drop'
KSV-0004 (LOW): Container 'stockdesk' of 'deployment' 'stockdesk' in 'default' namespace should set securityContext.capabilities.drop
KSV-0011 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should set 'resources.limits.cpu'
KSV-0012 (MEDIUM): Container 'stockdesk' of Deployment 'stockdesk' should set 'securityContext.runAsNonRoot' to true
KSV-0013 (MEDIUM): Container 'stockdesk' of Deployment 'stockdesk' should specify an image tag
KSV-0014 (HIGH): Container 'stockdesk' of Deployment 'stockdesk' should set 'securityContext.readOnlyRootFilesystem' to true
KSV-0015 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should set 'resources.requests.cpu'
KSV-0016 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should set 'resources.requests.memory'
KSV-0018 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should set 'resources.limits.memory'
KSV-0020 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should set 'securityContext.runAsUser' > 10000
KSV-0021 (LOW): Container 'stockdesk' of Deployment 'stockdesk' should set 'securityContext.runAsGroup' > 10000
KSV-0030 (LOW): Either Pod or Container should set 'securityContext.seccompProfile.type' to 'RuntimeDefault'
KSV-0104 (MEDIUM): container "stockdesk" of deployment "stockdesk" in "default" namespace should specify a seccomp profile
KSV-0106 (LOW): container should drop all
KSV-0110 (LOW): deployment stockdesk in default namespace should set metadata.namespace to a non-default namespace
KSV-0118 (HIGH): container stockdesk in default namespace is using the default security context
KSV-0118 (HIGH): deployment stockdesk in default namespace is using the default security context, which allows root privileges
KSV-0125 (MEDIUM): Container stockdesk in deployment stockdesk (namespace: default) uses an image from an untrusted registry.
```

```
# gitleaks on the original files (rule, file:line; values redacted)
## default rules only
6 findings
  generic-api-key          .env:7
  generic-api-key          docker-compose.yml:17
  kubernetes-secret-yaml   k8s/secret.yaml:2
  generic-api-key          k8s/secret.yaml:11
  generic-api-key          k8s/secret.yaml:11
  generic-api-key          k8s/secret.yaml:12
## with .gitleaks.toml (adds Corvane token formats)
9 findings
  generic-api-key          .env:7
  stockdesk-api-key        .env:8
  corvane-deploy-token     .github/workflows/ci.yml:14
  generic-api-key          docker-compose.yml:17
  kubernetes-secret-yaml   k8s/secret.yaml:2
  generic-api-key          k8s/secret.yaml:11
  generic-api-key          k8s/secret.yaml:11
  generic-api-key          k8s/secret.yaml:12
  stockdesk-api-key        k8s/secret.yaml:12
```

