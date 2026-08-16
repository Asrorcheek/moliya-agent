#!/usr/bin/env bash
set -euo pipefail

instance=${MOLIYA_GCLOUD_INSTANCE:-pet-project-2}
zone=${MOLIYA_GCLOUD_ZONE:-us-central1-c}
remote_release=/tmp/moliya-agent-release.tar.gz
remote_script=/tmp/moliya-deploy-remote.sh
project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
release_dir=$(mktemp -d /tmp/moliya-release.XXXXXX)
release_tar=$(mktemp /tmp/moliya-agent-release.XXXXXX.tar.gz)

cleanup() {
  rm -rf "$release_dir"
  rm -f "$release_tar"
}
trap cleanup EXIT

cd "$project_dir/app"
npm ci
npm run typecheck
npm run build

mkdir -p "$release_dir/backend" "$release_dir/web-dist"
cd "$project_dir"
cp -a pyproject.toml README.md Dockerfile compose.yaml .env.example \
  src docs deploy scripts hermes-skill tests "$release_dir/backend/"
cp -a app/dist/. "$release_dir/web-dist/"
find "$release_dir" -type d -name __pycache__ -prune -exec rm -rf {} +
tar -czf "$release_tar" -C "$release_dir" backend web-dist
release_sha=$(sha256sum "$release_tar" | awk '{print $1}')

gcloud compute scp "$release_tar" "$instance:$remote_release" --zone "$zone"
gcloud compute scp "$project_dir/scripts/deploy_remote.sh" \
  "$instance:$remote_script" --zone "$zone"
gcloud compute ssh "$instance" --zone "$zone" --command="sudo -n bash $remote_script $remote_release $release_sha"
gcloud compute ssh "$instance" --zone "$zone" --command="rm -f $remote_release $remote_script"

echo "Deployment complete"
