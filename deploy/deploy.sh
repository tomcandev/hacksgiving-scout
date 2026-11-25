#!/usr/bin/env bash
# Deploy hacksgiving-scout to a Fly.io Sprite and (re)start the daily service.
#   ./deploy/deploy.sh [sprite-name]
set -euo pipefail
SPRITE="${1:-hacksgiving-scout}"
REPO_URL="${REPO_URL:-https://github.com/tomcandev/hacksgiving-scout.git}"
DIR=/home/sprite/hacksgiving-scout
sx() { sprite exec -s "$SPRITE" --no-stdin -- "$@"; }

sprite list | grep -qx "$SPRITE" || sprite create --skip-console "$SPRITE"

sx sh -c "if [ -d $DIR/.git ]; then git -C $DIR pull --ff-only; else rm -rf $DIR && git clone --depth 1 $REPO_URL $DIR; fi"
sx sh -c "cd $DIR && python3 -m unittest discover -s tests -t . -q"

sx sh -c "sprite-env services delete scout >/dev/null 2>&1 || true"
sx sprite-env services create scout \
  --cmd /usr/bin/python3 --args -u,-m,scout.main,loop --dir "$DIR" \
  --env "SCOUT_HOUR=${SCOUT_HOUR:-8},SCOUT_REPO=${SCOUT_REPO:-tomcandev/hacksgiving-scout}" \
  --duration 3s
sx sprite-env services list
echo "Deployed. Run once now with:"
echo "  sprite exec -s $SPRITE --dir $DIR -- python3 -m scout.main run"
