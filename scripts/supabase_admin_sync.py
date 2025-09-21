"""Admin-only Supabase sync helpers using the service role key.

This module is intentionally kept outside the Streamlit runtime. It expects
`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables to be
present and should only be used for trusted CLI/admin tasks.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Tuple

from supabase import create_client


def _service_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running admin sync commands."
        )
    return create_client(url, key)


def push_json(table: str, local_fp: Path) -> Tuple[bool, str]:
    """Read a local JSON file and upsert rows into a Supabase table."""
    try:
        sb = _service_client()
        payload = json.loads(local_fp.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = [payload]
        sb.table(table).upsert(payload).execute()
        return True, f"Upserted {len(payload)} rows into {table}"
    except Exception as exc:  # pragma: no cover - network/admin failures
        return False, str(exc)


def pull_json(table: str, local_fp: Path) -> Tuple[bool, str]:
    """Fetch rows from a Supabase table and write them to a local JSON file."""
    try:
        sb = _service_client()
        res = sb.table(table).select("*").execute()
        data = res.data if hasattr(res, "data") else res
        local_fp.parent.mkdir(parents=True, exist_ok=True)
        local_fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True, f"Downloaded {len(data)} rows from {table}"
    except Exception as exc:  # pragma: no cover - network/admin failures
        return False, str(exc)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supabase admin sync utilities")
    parser.add_argument("action", choices=["push", "pull"], help="Direction of sync")
    parser.add_argument("table", help="Target table name")
    parser.add_argument("path", help="Local JSON file path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    path = Path(args.path)
    if args.action == "push":
        ok, msg = push_json(args.table, path)
    else:
        ok, msg = pull_json(args.table, path)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
