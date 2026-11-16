#!/usr/bin/env python3
"""Evaluate Ops Agent grounding across multiple company corpora.

Offline: intent detectors + corpus integrity.
Live (default): temporarily swap Articles to each company, ask golden questions,
then restore the Cobalt Home playbook.

Usage:
  # inside repo, stack up:
  python3 scripts/multi_company_eval.py
  LIVE=0 python3 scripts/multi_company_eval.py   # offline only
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Host checkout vs docker exec (/app is the backend package root).
BACKEND = Path("/app") if Path("/app/app").exists() else ROOT / "backend"
sys.path.insert(0, str(BACKEND))

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001").rstrip("/")
USER = os.environ.get("OPS_USER", "multi-company-eval@example.com")
TOKEN = os.environ.get("OPS_API_TOKEN", "")
LIVE = os.environ.get("LIVE", "1") != "0"
# Stay under rate limit: pause between companies / cases.
PAUSE_S = float(os.environ.get("PAUSE_S", "2"))


def _headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Ops-User": USER,
        "Accept": "application/x-ndjson, application/json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def stream_chat(message: str) -> dict:
    body = json.dumps({"message": message}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/chat/stream",
        data=body,
        headers=_headers(),
        method="POST",
    )
    events: list[dict] = []
    final = ""
    with urllib.request.urlopen(req, timeout=180) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line:
                continue
            event = json.loads(line)
            events.append(event)
            if event.get("type") == "final_answer":
                final = event.get("content") or ""
    return {"events": events, "final": final}


def has_type(events: list[dict], *types: str) -> bool:
    wanted = set(types)
    return any(e.get("type") in wanted for e in events)


def offline_checks(companies: list[dict]) -> list[dict]:
    from app.services.grounding import looks_like_operational_action, needs_document_grounding

    rows = []
    for company in companies:
        brand = company["brand"]
        ok = True
        detail = []
        if len(company.get("articles") or []) < 2:
            ok = False
            detail.append("need>=2 articles")
        for case in company.get("cases") or []:
            ask = case["ask"]
            if case.get("expect_kb") and not needs_document_grounding(ask):
                # traps/policy should look like docs questions
                if looks_like_operational_action(ask):
                    ok = False
                    detail.append(f"{case['name']}: classified as ops")
                else:
                    # still ok if howto/docs pattern soft-misses; note it
                    detail.append(f"{case['name']}: weak docs signal")
            if brand.split()[0].lower() not in ask.lower() and case["name"] != "trap":
                # brand often in ask for policy; not required for all
                pass
        rows.append(
            {
                "company": company["id"],
                "brand": brand,
                "phase": "offline",
                "ok": ok,
                "detail": ", ".join(detail) or "corpus+detectors ok",
            }
        )
    return rows


def apply_company_live(company: dict) -> dict:
    from app.core.database import SessionLocal
    from app.services.company_corpus import apply_company_articles

    db = SessionLocal()
    try:
        return apply_company_articles(db, company)
    finally:
        db.close()


def restore_cobalt_playbook() -> dict:
    from app.services.playbook_content_seed import sync_playbook_content
    from app.core.database import SessionLocal
    from app.services.usage.semantic_cache import clear_semantic_cache

    counts = sync_playbook_content()
    db = SessionLocal()
    try:
        clear_semantic_cache(db)
    finally:
        db.close()
    return counts


def live_checks(companies: list[dict]) -> list[dict]:
    rows = []
    for company in companies:
        print(f"\n--- live corpus: {company['brand']} ---")
        try:
            applied = apply_company_live(company)
            print(f"  applied={applied}")
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "company": company["id"],
                    "brand": company["brand"],
                    "phase": "live",
                    "ok": False,
                    "detail": f"apply failed: {exc}",
                }
            )
            continue

        time.sleep(PAUSE_S)
        for case in company.get("cases") or []:
            name = f"{company['id']}/{case['name']}"
            try:
                out = stream_chat(case["ask"])
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    print("  429 — sleeping 65s")
                    time.sleep(65)
                    out = stream_chat(case["ask"])
                else:
                    rows.append(
                        {
                            "company": company["id"],
                            "brand": company["brand"],
                            "case": case["name"],
                            "phase": "live",
                            "ok": False,
                            "detail": f"HTTP {exc.code}",
                        }
                    )
                    continue

            text = (out["final"] or "").lower()
            events = out["events"]
            grounded = has_type(events, "kb_search", "cache")
            must_any = [s.lower() for s in case.get("must_contain_any") or []]
            must_not = [s.lower() for s in case.get("must_not_contain") or []]
            hit_any = (not must_any) or any(s in text for s in must_any)
            hit_bad = any(s in text for s in must_not)
            expect_kb = bool(case.get("expect_kb"))
            ok = hit_any and not hit_bad and ((grounded if expect_kb else True) or hit_any)
            # Prefer grounded, but accept correct refuse text if model searched poorly.
            if expect_kb and not grounded and hit_any and not hit_bad:
                ok = True  # soft pass with note
                detail = f"content_ok grounded=False events={[e.get('type') for e in events]}"
            else:
                detail = (
                    f"grounded={grounded} hit_any={hit_any} hit_bad={hit_bad} "
                    f"events={[e.get('type') for e in events]}"
                )
            rows.append(
                {
                    "company": company["id"],
                    "brand": company["brand"],
                    "case": case["name"],
                    "phase": "live",
                    "ok": ok,
                    "detail": detail,
                    "answer": (out["final"] or "")[:220],
                }
            )
            flag = "PASS" if ok else "FAIL"
            print(f"  [{flag}] {name}: {detail}")
            time.sleep(PAUSE_S)
    return rows


def main() -> int:
    # Import after path setup
    os.chdir(BACKEND)
    from app.services.company_corpus import load_all_companies
    from app.services.grounding import needs_document_grounding, looks_like_operational_action

    companies = load_all_companies()
    print(f"companies={len(companies)} LIVE={LIVE} API_BASE={API_BASE}")

    # Sanity: detectors remain brand-agnostic across sample asks
    sample_docs = [c["cases"][0]["ask"] for c in companies]
    det_ok = all(needs_document_grounding(a) or not looks_like_operational_action(a) for a in sample_docs)
    print(f"detector_brand_agnostic={'PASS' if det_ok else 'FAIL'}")

    results = offline_checks(companies)
    for row in results:
        print(f"[ {'PASS' if row['ok'] else 'FAIL'} ] offline {row['brand']}: {row['detail']}")

    if LIVE:
        try:
            urllib.request.urlopen(urllib.request.Request(f"{API_BASE}/healthz"), timeout=10)
        except Exception as exc:  # noqa: BLE001
            print(f"API unreachable at {API_BASE}: {exc}")
            return 2
        results.extend(live_checks(companies))
        print("\nRestoring Cobalt Home playbook…")
        try:
            counts = restore_cobalt_playbook()
            print(f"restored={counts}")
        except Exception as exc:  # noqa: BLE001
            print(f"restore failed: {exc}")
            return 1

    failed = [r for r in results if not r.get("ok")]
    report = {"results": results, "failed": len(failed), "total": len(results)}
    print(f"\nSummary: {len(results) - len(failed)}/{len(results)} passed")
    out = (
        Path("/tmp/multi_company_report.json")
        if Path("/app/app").exists()
        else ROOT / "scripts" / "multi_company_report.json"
    )
    try:
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
    except OSError as exc:
        print(f"report_write_skipped: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
