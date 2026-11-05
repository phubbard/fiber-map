#!/usr/bin/env bash
# Pull the latest code, build the page, publish site/ to the web root. Meant for cron:
#   15 6 * * * $HOME/code/fiber-map/deploy.sh >> $HOME/logs/fiber-map.log 2>&1
# Override the destination with FIBERMAP_DEST; set FIBERMAP_NTFY to a ntfy.sh topic
# to be told about failures (cron mail usually goes nowhere).
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
DEST="${FIBERMAP_DEST:-$HOME/html/fiber-map}"
NTFY="${FIBERMAP_NTFY:-}"

notify_failure() {
    echo "$(date -Is) deploy FAILED (exit $?)" >&2
    if [ -n "$NTFY" ]; then
        curl -fsS -m 10 -H "Title: fiber-map deploy failed on $(hostname)" -H "Priority: high" \
            -d "see $HOME/logs/fiber-map.log" "https://ntfy.sh/$NTFY" >/dev/null || true
    fi
}
trap notify_failure ERR

if [ -d .git ]; then
    git pull -q --ff-only || echo "git pull failed; building with the current checkout" >&2
fi

python3 -m fibermap build

# Refuse to --delete inside a directory that is clearly not ours.
if [ -d "$DEST" ] && [ ! -e "$DEST/index.html" ] && [ -n "$(ls -A "$DEST")" ]; then
    echo "refusing to publish: $DEST exists, is not empty and has no index.html" >&2
    exit 1
fi
mkdir -p "$DEST"
rsync -a --delete --exclude '*.tmp' site/ "$DEST"/
echo "$(date -Is) published $(find "$DEST" -type f | wc -l | tr -d ' ') files to $DEST"
