#!/usr/bin/env python3
"""Install local Google OAuth secrets into the production environment safely."""

from __future__ import annotations

import argparse
import secrets
import shlex
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_REDIRECT_URI = (
    "https://moliya.34-29-145-102.sslip.io/v1/integrations/google/callback"
)
SECRET_KEYS = (
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_PICKER_API_KEY",
)

REMOTE_UPDATER = r'''#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

target = Path(sys.argv[1])
incoming = Path(sys.argv[2])
updates: dict[str, str] = {}
for raw_line in incoming.read_text(encoding="utf-8").splitlines():
    if not raw_line or raw_line.lstrip().startswith("#") or "=" not in raw_line:
        continue
    key, value = raw_line.split("=", 1)
    updates[key] = value

lines = target.read_text(encoding="utf-8").splitlines()
seen: set[str] = set()
result: list[str] = []
for line in lines:
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
    if match and match.group(1) in updates:
        key = match.group(1)
        result.append(f"{key}={updates[key]}")
        seen.add(key)
    else:
        result.append(line)
for key, value in updates.items():
    if key not in seen:
        result.append(f"{key}={value}")

fd, temporary_name = tempfile.mkstemp(prefix=".moliya-env-", dir=target.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(result) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary_name, 0o600)
    os.replace(temporary_name, target)
finally:
    if os.path.exists(temporary_name):
        os.unlink(temporary_name)
'''


def checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", default="pet-project-2")
    parser.add_argument("--zone", default="us-central1-c")
    parser.add_argument("--local-env", type=Path, default=PROJECT_ROOT / ".env")
    args = parser.parse_args()

    values = read_env(args.local_env)
    missing = [key for key in SECRET_KEYS if not (values.get(key) or "").strip()]
    if missing:
        raise SystemExit("Missing required local settings: " + ", ".join(missing))

    updates = {key: str(values[key]).strip() for key in SECRET_KEYS}
    updates["GOOGLE_OAUTH_REDIRECT_URI"] = PRODUCTION_REDIRECT_URI
    for key, value in updates.items():
        if "\n" in value or "\r" in value:
            raise SystemExit(f"Invalid newline in {key}")

    release_id = secrets.token_hex(8)
    remote_incoming = f"/tmp/moliya-google-oauth-{release_id}.env"
    remote_updater = f"/tmp/moliya-google-oauth-{release_id}.py"
    remote_staged = f"/home/busin/.hermes/.moliya-google-oauth-{release_id}.env"
    remote_target = "/home/busin/.hermes/moliya-agent.env"
    runtime_dir = "/run/user/1001"

    with tempfile.TemporaryDirectory(prefix="moliya-google-oauth-") as directory:
        directory_path = Path(directory)
        incoming_path = directory_path / "oauth.env"
        updater_path = directory_path / "update_env.py"
        incoming_path.write_text(
            "".join(f"{key}={value}\n" for key, value in updates.items()),
            encoding="utf-8",
        )
        incoming_path.chmod(0o600)
        updater_path.write_text(REMOTE_UPDATER, encoding="utf-8")
        updater_path.chmod(0o700)

        checked(
            [
                "gcloud",
                "compute",
                "scp",
                str(incoming_path),
                f"{args.instance}:{remote_incoming}",
                "--zone",
                args.zone,
            ]
        )
        checked(
            [
                "gcloud",
                "compute",
                "scp",
                str(updater_path),
                f"{args.instance}:{remote_updater}",
                "--zone",
                args.zone,
            ]
        )

    quoted = {value: shlex.quote(value) for value in (
        remote_incoming,
        remote_updater,
        remote_staged,
        remote_target,
        runtime_dir,
    )}
    incoming_q, updater_q, staged_q, target_q, runtime_q = (
        quoted[remote_incoming],
        quoted[remote_updater],
        quoted[remote_staged],
        quoted[remote_target],
        quoted[runtime_dir],
    )
    cleanup_command = (
        f"rm -f {incoming_q} {updater_q}; "
        f"sudo -n rm -f {staged_q} {updater_q}.owned"
    )
    remote_command = " && ".join(
        [
            f"trap {shlex.quote(cleanup_command)} EXIT",
            f"sudo -n install -m 0600 -o busin -g busin {incoming_q} {staged_q}",
            f"sudo -n install -m 0755 -o busin -g busin {updater_q} {updater_q}.owned",
            f"sudo -u busin cp {target_q} {target_q}.oauth-backup-$(date -u +%Y%m%dT%H%M%SZ)",
            (
                "sudo -u busin /home/busin/moliya-agent/.venv/bin/python "
                f"{updater_q}.owned {target_q} {staged_q}"
            ),
            f"sudo -u busin chmod 0600 {target_q}",
            (
                f"sudo -u busin env XDG_RUNTIME_DIR={runtime_q} systemctl --user restart "
                "moliya-agent.service moliya-telegram-bot.service"
            ),
            (
                f"sudo -u busin env XDG_RUNTIME_DIR={runtime_q} systemctl --user is-active "
                "moliya-agent.service moliya-telegram-bot.service"
            ),
        ]
    )
    try:
        result = checked(
            [
                "gcloud",
                "compute",
                "ssh",
                args.instance,
                "--zone",
                args.zone,
                "--command",
                remote_command,
            ]
        )
    except subprocess.CalledProcessError as exc:
        # Never echo subprocess output: a future CLI version could include sensitive input.
        raise SystemExit(f"Production OAuth configuration failed (exit {exc.returncode})") from None

    active_lines = [line for line in result.stdout.splitlines() if line.strip() == "active"]
    if len(active_lines) != 2:
        raise SystemExit("Production services did not both report active")
    print("production_oauth=installed")
    print("production_services=active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
