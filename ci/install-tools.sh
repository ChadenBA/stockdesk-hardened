#!/usr/bin/env bash
# Install the CI scanners from their GitHub release assets, pinned by version
# AND by SHA-256. The checksum is verified before anything is unpacked or run,
# so a moved tag or a swapped release asset makes the job fail instead of
# executing unknown code. No third-party GitHub Action is used for scanning.
#
# Usage: ci/install-tools.sh <tool> [<tool> ...]
# Installs into $TOOLS_DIR (default: $RUNNER_TEMP/bin) and, in GitHub Actions,
# adds that directory to $GITHUB_PATH.
#
# Checksums: taken from each project's published checksum file on 2026-11-23
# (actionlint, kubeconform, gitleaks, trivy). hadolint publishes no checksum
# file for this release: its value is the SHA-256 of the binary downloaded on
# 2026-11-23 (trust on first use) -> TODO verify against another source.
# Dependabot does not update these pins: bump them by hand (see README).
set -euo pipefail

declare -A URL SHA MEMBER
URL[actionlint]="https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz"
SHA[actionlint]="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"
MEMBER[actionlint]="actionlint"

URL[hadolint]="https://github.com/hadolint/hadolint/releases/download/v2.15.1/hadolint-linux-x86_64"
SHA[hadolint]="c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507"
MEMBER[hadolint]=""

URL[kubeconform]="https://github.com/yannh/kubeconform/releases/download/v0.8.0/kubeconform-linux-amd64.tar.gz"
SHA[kubeconform]="9bc2bffbf71f261128533edaf912153948b7ff238f9a531ae6d34466ec287883"
MEMBER[kubeconform]="kubeconform"

URL[gitleaks]="https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz"
SHA[gitleaks]="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
MEMBER[gitleaks]="gitleaks"

URL[trivy]="https://github.com/aquasecurity/trivy/releases/download/v0.76.2/trivy_0.76.2_Linux-64bit.tar.gz"
SHA[trivy]="bc0fc726e017b8927a62b2d3531d7a84ee01769daf5c99ed866dced54089fdbf"
MEMBER[trivy]="trivy"

dest="${TOOLS_DIR:-${RUNNER_TEMP:-/tmp}/bin}"
mkdir -p "$dest"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for tool in "$@"; do
  [[ -n "${URL[$tool]:-}" ]] || { echo "unknown tool: $tool" >&2; exit 2; }
  curl -sSfL --proto '=https' --tlsv1.2 -o "$tmp/$tool.asset" "${URL[$tool]}"
  echo "${SHA[$tool]}  $tmp/$tool.asset" | sha256sum --check --quiet -
  if [[ -n "${MEMBER[$tool]}" ]]; then
    tar -xzf "$tmp/$tool.asset" -C "$tmp" "${MEMBER[$tool]}"
    install -m 0755 "$tmp/${MEMBER[$tool]}" "$dest/$tool"
  else
    install -m 0755 "$tmp/$tool.asset" "$dest/$tool"
  fi
  echo "installed $tool (sha256 verified) -> $dest/$tool"
done

if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "$dest" >> "$GITHUB_PATH"
fi
