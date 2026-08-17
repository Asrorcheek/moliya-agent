#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: deploy_remote.sh RELEASE_TAR EXPECTED_SHA256" >&2
  exit 2
fi

release=$1
expected_sha=$2
app_dir=${MOLIYA_REMOTE_APP_DIR:-/home/busin/moliya-agent}
env_file=${MOLIYA_REMOTE_ENV_FILE:-/home/busin/.hermes/moliya-agent.env}
runtime_dir=${MOLIYA_REMOTE_RUNTIME_DIR:-/run/user/1001}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_dir=/home/busin/backups/moliya-agent-$timestamp
stage_dir=/home/busin/.moliya-release-$timestamp
services_stopped=false

cleanup() {
  rm -rf "$stage_dir"
  if [[ "$services_stopped" == true ]]; then
    sudo -u busin env XDG_RUNTIME_DIR="$runtime_dir" \
      systemctl --user start moliya-agent.service moliya-telegram-bot.service || true
  fi
}
trap cleanup EXIT

actual_sha=$(sha256sum "$release" | awk '{print $1}')
if [[ "$actual_sha" != "$expected_sha" ]]; then
  echo "Release checksum mismatch" >&2
  exit 1
fi

install -d -m 0700 -o busin -g busin "$backup_dir" "$stage_dir"
sudo -u busin tar -czf "$backup_dir/source.tar.gz" \
  --exclude=.venv --exclude=data --exclude=web-dist \
  -C "$app_dir" .
sudo -u busin cp "$env_file" "$backup_dir/moliya-agent.env"
sudo -u busin chmod 0600 "$backup_dir/moliya-agent.env"

sudo -u busin env APP_DIR="$app_dir" BACKUP_DB="$backup_dir/moliya.db" \
  "$app_dir/.venv/bin/python" - <<'PY'
import os
import sqlite3

source = sqlite3.connect(os.path.join(os.environ["APP_DIR"], "data", "moliya.db"))
target = sqlite3.connect(os.environ["BACKUP_DB"])
with target:
    source.backup(target)
target.close()
source.close()
PY

sudo -u busin tar -xzf "$release" -C "$stage_dir"

# Install declared runtime dependencies before importing the staged application.
# This keeps deployments working when pyproject.toml adds a new dependency.
mapfile -t project_dependencies < <(
  "$app_dir/.venv/bin/python" -c \
    'import sys, tomllib; print("\n".join(tomllib.load(open(sys.argv[1], "rb"))["project"]["dependencies"]))' \
    "$stage_dir/backend/pyproject.toml"
)
if [[ ${#project_dependencies[@]} -gt 0 ]]; then
  sudo -u busin "$app_dir/.venv/bin/python" -m pip install \
    "${project_dependencies[@]}" >/dev/null
fi

sudo -u busin env STAGE_SRC="$stage_dir/backend/src" ENV_FILE="$env_file" \
  "$app_dir/.venv/bin/python" - <<'PY'
import os
import sys
from dotenv import dotenv_values

sys.path.insert(0, os.environ["STAGE_SRC"])
for key, value in dotenv_values(os.environ["ENV_FILE"]).items():
    if value is not None:
        os.environ[key] = value
from moliya_agent.api import create_app
from moliya_agent.config import Settings

settings = Settings.from_env()
create_app(settings)
print("staging_validation=ok")
PY

sudo -u busin env XDG_RUNTIME_DIR="$runtime_dir" \
  systemctl --user stop moliya-telegram-bot.service moliya-agent.service
services_stopped=true

for directory in src docs deploy scripts hermes-skill tests; do
  sudo -u busin rsync -a --delete "$stage_dir/backend/$directory/" "$app_dir/$directory/"
done
for file in pyproject.toml README.md Dockerfile compose.yaml .env.example; do
  sudo -u busin install -m 0644 "$stage_dir/backend/$file" "$app_dir/$file"
done
sudo -u busin install -d -m 0755 "$app_dir/web-dist"
sudo -u busin rsync -a --delete "$stage_dir/web-dist/" "$app_dir/web-dist/"

sudo -u busin "$app_dir/.venv/bin/python" -m pip install --no-deps -e "$app_dir" >/dev/null
sudo -u busin env XDG_RUNTIME_DIR="$runtime_dir" systemctl --user daemon-reload
sudo -u busin env XDG_RUNTIME_DIR="$runtime_dir" \
  systemctl --user start moliya-agent.service moliya-telegram-bot.service
services_stopped=false

printf 'backup=%s\n' "$backup_dir"
printf 'deploy=ok\n'
