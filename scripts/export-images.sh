#!/usr/bin/env bash
# Export each architecture from the exact GHCR digest just published by CI.
set -euo pipefail

image="${1:?image name required}"
digest="${2:?published digest required}"
destination="${3:-dist}"
mkdir -p "$destination"
manifest="$(mktemp)"
trap 'rm -f "$manifest"' EXIT
docker buildx imagetools inspect "$image@$digest" --raw > "$manifest"

for architecture in amd64 arm64; do
    child_digest="$(jq -r --arg arch "$architecture" \
        '.manifests[] | select(.platform.os == "linux" and .platform.architecture == $arch) | .digest' \
        "$manifest")"
    if [[ ! "$child_digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
        echo "Expected one linux/$architecture image in the published manifest." >&2
        exit 1
    fi

    # Pull the single-platform manifest, rather than a mutable latest tag.
    # This also avoids requiring docker save --platform on older daemons.
    docker pull --platform="linux/$architecture" "$image@$child_digest"
    docker tag "$image@$child_digest" "$image:latest"
    actual_architecture="$(docker image inspect "$image:latest" --format '{{.Architecture}}')"
    if [[ "$actual_architecture" != "$architecture" ]]; then
        echo "Architecture mismatch: expected $architecture, got $actual_architecture." >&2
        exit 1
    fi
    docker save --output "$destination/opencode-linux-$architecture.tar" "$image:latest"
done

(
    cd "$destination"
    sha256sum opencode-linux-amd64.tar opencode-linux-arm64.tar > SHA256SUMS
)
