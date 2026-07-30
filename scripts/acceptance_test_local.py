#!/usr/bin/env python3
"""Run a disposable local API + Hermes client acceptance test."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HERMES_CLIENT = PROJECT_ROOT / "hermes-skill/moliya/scripts/moliya_client.py"
TOKEN = "local-acceptance-token-only"
ACTOR = "hermes"
TEST_MONTH = "2026-07"
RECEIVED_AT = "2026-07-30T12:00:00+05:00"


def free_local_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def api_request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: dict[str, object] | None = None,
    token: str = TOKEN,
) -> tuple[int, dict[str, object]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Moliya-Token": token,
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def wait_until_healthy(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"API muddatidan oldin to'xtadi.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
        try:
            status, health = api_request(base_url, "GET", "/health")
        except URLError:
            time.sleep(0.1)
            continue
        if status == 200 and health.get("status") == "ok":
            return
        time.sleep(0.1)
    raise RuntimeError("API 15 soniyada tayyor bo'lmadi")


def draft_payload(source_id: str, text: str) -> dict[str, object]:
    return {
        "actor_id": ACTOR,
        "source_id": source_id,
        "text": text,
        "received_at": RECEIVED_AT,
    }


def run_checks(base_url: str, environment: dict[str, str]) -> None:
    status, health = api_request(base_url, "GET", "/health")
    assert status == 200
    assert health == {
        "status": "ok",
        "parser_mode": "rule",
        "sheet_mode": "memory",
    }

    client = subprocess.run(
        [sys.executable, str(HERMES_CLIENT), "health"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "status=ok parser=rule sheet=memory" in client.stdout

    report_query = urlencode({"actor_id": ACTOR, "month": TEST_MONTH})
    status, _ = api_request(
        base_url,
        "GET",
        f"/v1/reports/monthly?{report_query}",
        token="wrong-token",
    )
    assert status == 401

    intruder_query = urlencode({"actor_id": "intruder", "month": TEST_MONTH})
    status, _ = api_request(
        base_url, "GET", f"/v1/reports/monthly?{intruder_query}"
    )
    assert status == 403

    source_id = f"acceptance:main:{uuid.uuid4()}"
    payload = draft_payload(
        source_id, "Bugun 2 mln tushum, 500 ming xarajat"
    )
    status, created = api_request(
        base_url, "POST", "/v1/drafts", payload=payload
    )
    assert status == 200
    draft = created["draft"]
    assert isinstance(draft, dict)
    draft_id = str(draft["id"])
    assert draft["status"] == "pending"
    parsed = draft["parsed"]
    assert isinstance(parsed, dict)
    assert len(parsed["entries"]) == 2

    status, duplicate = api_request(
        base_url, "POST", "/v1/drafts", payload=payload
    )
    assert status == 200
    duplicate_draft = duplicate["draft"]
    assert isinstance(duplicate_draft, dict)
    assert duplicate_draft["id"] == draft_id

    status, confirmed = api_request(
        base_url,
        "POST",
        f"/v1/drafts/{draft_id}/confirm",
        payload={"actor_id": ACTOR},
    )
    assert status == 200
    assert confirmed["written_rows"] == 2
    assert confirmed["already_confirmed"] is False

    status, retried = api_request(
        base_url,
        "POST",
        f"/v1/drafts/{draft_id}/confirm",
        payload={"actor_id": ACTOR},
    )
    assert status == 200
    assert retried["written_rows"] == 0
    assert retried["already_confirmed"] is True

    status, clarification = api_request(
        base_url,
        "POST",
        "/v1/drafts",
        payload=draft_payload(
            f"acceptance:clarification:{uuid.uuid4()}",
            "Bugun xarajat qildim",
        ),
    )
    assert status == 200
    clarification_draft = clarification["draft"]
    assert isinstance(clarification_draft, dict)
    clarification_parsed = clarification_draft["parsed"]
    assert isinstance(clarification_parsed, dict)
    assert clarification_parsed["needs_clarification"] is True

    status, _ = api_request(
        base_url,
        "POST",
        f"/v1/drafts/{clarification_draft['id']}/confirm",
        payload={"actor_id": ACTOR},
    )
    assert status == 422

    status, rejectable = api_request(
        base_url,
        "POST",
        "/v1/drafts",
        payload=draft_payload(
            f"acceptance:reject:{uuid.uuid4()}",
            "Bugun 300 ming xarajat",
        ),
    )
    assert status == 200
    rejectable_draft = rejectable["draft"]
    assert isinstance(rejectable_draft, dict)
    reject_id = str(rejectable_draft["id"])

    status, rejected = api_request(
        base_url,
        "POST",
        f"/v1/drafts/{reject_id}/reject",
        payload={"actor_id": ACTOR},
    )
    assert status == 200
    rejected_draft = rejected["draft"]
    assert isinstance(rejected_draft, dict)
    assert rejected_draft["status"] == "rejected"

    status, _ = api_request(
        base_url,
        "POST",
        f"/v1/drafts/{reject_id}/confirm",
        payload={"actor_id": ACTOR},
    )
    assert status == 409

    status, report = api_request(
        base_url, "GET", f"/v1/reports/monthly?{report_query}"
    )
    assert status == 200
    assert report["income_uzs"] == 2_000_000
    assert report["expense_uzs"] == 500_000
    assert report["net_profit_uzs"] == 1_500_000


def main() -> int:
    port = free_local_port()
    base_url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="moliya-acceptance-") as temp_dir:
        environment = os.environ.copy()
        environment.update(
            {
                "ENVIRONMENT": "development",
                "MOLIYA_BIND_HOST": "127.0.0.1",
                "MOLIYA_BIND_PORT": str(port),
                "MOLIYA_INTERNAL_TOKEN": TOKEN,
                "MOLIYA_ALLOWED_ACTORS": ACTOR,
                "MOLIYA_PARSER_MODE": "rule",
                "MOLIYA_SHEET_MODE": "memory",
                "MOLIYA_DB_PATH": str(Path(temp_dir) / "moliya.db"),
                "MOLIYA_AGENT_URL": base_url,
            }
        )
        process = subprocess.Popen(
            [sys.executable, "-m", "moliya_agent.main"],
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            wait_until_healthy(base_url, process)
            run_checks(base_url, environment)
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()

    print("Local API + Hermes acceptance: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
