#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _settings() -> tuple[str, str]:
    base_url = os.getenv("MOLIYA_AGENT_URL", "http://127.0.0.1:8088").rstrip("/")
    token = os.getenv("MOLIYA_INTERNAL_TOKEN", "")
    if not token:
        raise RuntimeError("MOLIYA_INTERNAL_TOKEN sozlanmagan")
    return base_url, token


def _request(
    method: str, path: str, *, payload: dict[str, object] | None = None
) -> dict[str, object]:
    base_url, token = _settings()
    data = (
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if payload is not None
        else None
    )
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
        with urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except json.JSONDecodeError:
            detail = body
        raise RuntimeError(f"Backend {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Backendga ulanib bo'lmadi: {exc.reason}") from exc


def _draft(args: argparse.Namespace) -> None:
    result = _request(
        "POST",
        "/v1/drafts",
        payload={
            "actor_id": args.actor,
            "source_id": args.source_id or str(uuid.uuid4()),
            "text": args.text,
            "received_at": None,
        },
    )
    draft = result["draft"]
    print("PREVIEW")
    print(result["preview"])
    print(f"DRAFT_ID={draft['id']}")
    print(f"STATUS={draft['status']}")


def _confirm(args: argparse.Namespace) -> None:
    result = _request(
        "POST",
        f"/v1/drafts/{args.draft_id}/confirm",
        payload={"actor_id": args.actor},
    )
    print("CONFIRMED")
    print(f"DRAFT_ID={result['draft']['id']}")
    print(f"WRITTEN_ROWS={result['written_rows']}")
    print(f"ALREADY_CONFIRMED={str(result['already_confirmed']).lower()}")


def _reject(args: argparse.Namespace) -> None:
    result = _request(
        "POST",
        f"/v1/drafts/{args.draft_id}/reject",
        payload={"actor_id": args.actor},
    )
    print("REJECTED")
    print(f"DRAFT_ID={result['draft']['id']}")


def _report(args: argparse.Namespace) -> None:
    query = urlencode({"actor_id": args.actor, "month": args.month})
    result = _request("GET", f"/v1/reports/monthly?{query}")
    print(f"OY={result['month']}")
    print(f"TUSHUM={result['income_uzs']:,} UZS")
    print(f"VAZVRAT={result['refund_uzs']:,} UZS")
    print(f"SOF_TUSHUM={result['net_revenue_uzs']:,} UZS")
    print(f"TAN_NARX={result['cost_of_goods_uzs']:,} UZS")
    print(f"YALPI_FOYDA={result['gross_profit_uzs']:,} UZS")
    print(f"XARAJAT={result['expense_uzs']:,} UZS")
    print(f"SOF_FOYDA={result['net_profit_uzs']:,} UZS")


def _health(_args: argparse.Namespace) -> None:
    base_url, _token = _settings()
    try:
        with urlopen(f"{base_url}/health", timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Health check bajarilmadi: {exc}") from exc
    print(
        f"status={result['status']} parser={result['parser_mode']} "
        f"sheet={result['sheet_mode']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes uchun Moliya backend client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health")
    health.set_defaults(handler=_health)

    draft = subparsers.add_parser("draft")
    draft.add_argument("--actor", required=True)
    draft.add_argument("--source-id")
    draft.add_argument("--text", required=True)
    draft.set_defaults(handler=_draft)

    confirm = subparsers.add_parser("confirm")
    confirm.add_argument("--actor", required=True)
    confirm.add_argument("--draft-id", required=True)
    confirm.set_defaults(handler=_confirm)

    reject = subparsers.add_parser("reject")
    reject.add_argument("--actor", required=True)
    reject.add_argument("--draft-id", required=True)
    reject.set_defaults(handler=_reject)

    report = subparsers.add_parser("report")
    report.add_argument("--actor", required=True)
    report.add_argument("--month", required=True)
    report.set_defaults(handler=_report)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
        return 0
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
