#!/usr/bin/env python3
"""Usability + traffic soak against a running Ops Agent API.

Measures API capacity (cheap reads) and chat realism (FAQ / ops / traps)
under rising concurrency. Reports latency percentiles, errors, rate limits,
and grounding/cache signals.

Usage:
  python3 scripts/load_usability.py
  API_BASE=http://127.0.0.1:8001 CONCURRENCY=10 CHAT_ROUNDS=24 python3 scripts/load_usability.py
"""

from __future__ import annotations

import json
import os
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8001").rstrip("/")
USER = os.environ.get("OPS_USER", "load-test@example.com")
TOKEN = os.environ.get("OPS_API_TOKEN", "")
# Chat turns are LLM-costly; keep defaults moderate.
CHAT_ROUNDS = int(os.environ.get("CHAT_ROUNDS", "30"))
API_ROUNDS = int(os.environ.get("API_ROUNDS", "200"))
CONCURRENCY_LEVELS = [
    int(x) for x in os.environ.get("CONCURRENCY_LEVELS", "1,5,10,20").split(",") if x.strip()
]


def _headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Ops-User": USER,
        "Accept": "application/x-ndjson, application/json",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


@dataclass
class Sample:
    name: str
    ok: bool
    latency_ms: float
    status: int = 0
    error: str = ""
    events: list[str] = field(default_factory=list)
    final_len: int = 0


FAQ_PROMPTS = [
    "What's the difference between Classic and Connect locks, and which apps do they use?",
    "Can we create a Shopify RMA for an Amazon purchase?",
    "When should we escalate to a human queue?",
    "What’s Meridian’s return window policy for Shopify vs Amazon?",
]

OPS_PROMPTS = [
    "What is the health status of lock serial MD-GUARD-20022?",
    "Look up devices for alex.rivera@example.com",
]

TRAP_PROMPTS = [
    "Do we have a MeridianVIP lifetime free lock replacement program?",
]


def api_get(path: str, timeout: float = 30.0) -> Sample:
    t0 = time.perf_counter()
    req = urllib.request.Request(f"{API_BASE}{path}", headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ms = (time.perf_counter() - t0) * 1000
            return Sample(name=f"GET {path}", ok=200 <= resp.status < 300, latency_ms=ms, status=resp.status, final_len=len(body))
    except urllib.error.HTTPError as exc:
        ms = (time.perf_counter() - t0) * 1000
        return Sample(name=f"GET {path}", ok=False, latency_ms=ms, status=exc.code, error=str(exc.reason))
    except Exception as exc:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        return Sample(name=f"GET {path}", ok=False, latency_ms=ms, error=str(exc))


def stream_chat(message: str, timeout: float = 180.0) -> Sample:
    t0 = time.perf_counter()
    body = json.dumps({"message": message}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/chat/stream",
        data=body,
        headers=_headers(),
        method="POST",
    )
    events: list[str] = []
    final = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode().strip()
                if not line:
                    continue
                event = json.loads(line)
                et = str(event.get("type") or "?")
                events.append(et)
                if et == "final_answer":
                    final = event.get("content") or ""
            ms = (time.perf_counter() - t0) * 1000
            ok = bool(final) and "error" not in events
            return Sample(
                name="POST /api/chat/stream",
                ok=ok,
                latency_ms=ms,
                status=resp.status,
                events=events,
                final_len=len(final),
            )
    except urllib.error.HTTPError as exc:
        ms = (time.perf_counter() - t0) * 1000
        return Sample(name="POST /api/chat/stream", ok=False, latency_ms=ms, status=exc.code, error=str(exc.reason))
    except Exception as exc:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        return Sample(name="POST /api/chat/stream", ok=False, latency_ms=ms, error=str(exc))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def summarize(label: str, samples: list[Sample]) -> dict[str, Any]:
    latencies = [s.latency_ms for s in samples]
    ok = [s for s in samples if s.ok]
    fail = [s for s in samples if not s.ok]
    rate_limited = sum(1 for s in samples if s.status == 429)
    cache_hits = sum(1 for s in samples if "cache" in s.events)
    kb_hits = sum(1 for s in samples if "kb_search" in s.events)
    tool_hits = sum(1 for s in samples if "resource_called" in s.events or "sop_matched" in s.events)
    elapsed = max(latencies) if not samples else None
    # wall approx from sum of max concurrent isn't known here; caller adds rps
    return {
        "label": label,
        "n": len(samples),
        "ok": len(ok),
        "fail": len(fail),
        "success_rate": (len(ok) / len(samples) * 100.0) if samples else 0.0,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "avg_ms": statistics.fmean(latencies) if latencies else 0.0,
        "max_ms": max(latencies) if latencies else 0.0,
        "rate_limited": rate_limited,
        "cache_hits": cache_hits,
        "kb_hits": kb_hits,
        "tool_or_sop": tool_hits,
        "errors": [s.error or f"HTTP {s.status}" for s in fail[:5]],
    }


def run_pool(jobs: list[Any], concurrency: int) -> tuple[list[Sample], float]:
    t0 = time.perf_counter()
    out: list[Sample] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futs = [pool.submit(fn, *args) for fn, args in jobs]
        for fut in as_completed(futs):
            out.append(fut.result())
    wall = time.perf_counter() - t0
    return out, wall


def build_api_jobs(n: int) -> list[tuple[Any, tuple]]:
    paths = [
        "/healthz",
        "/readyz",
        "/api/kb/references",
        "/api/sops/documents",
        "/api/resources",
        "/api/usage/stats?days=7",
    ]
    jobs = []
    for i in range(n):
        path = paths[i % len(paths)]
        jobs.append((api_get, (path,)))
    return jobs


def build_chat_jobs(n: int, *, warm_cache: bool) -> list[tuple[Any, tuple]]:
    """Repeat FAQ prompts so semantic cache can engage after first wave."""
    jobs = []
    for i in range(n):
        if warm_cache and i >= max(4, n // 3):
            msg = FAQ_PROMPTS[i % len(FAQ_PROMPTS)]
        elif i % 7 == 0:
            msg = TRAP_PROMPTS[0]
        elif i % 5 == 0:
            msg = OPS_PROMPTS[i % len(OPS_PROMPTS)]
        else:
            msg = FAQ_PROMPTS[i % len(FAQ_PROMPTS)]
        jobs.append((stream_chat, (msg,)))
    return jobs


def print_summary(row: dict[str, Any], wall_s: float) -> None:
    rps = row["n"] / wall_s if wall_s > 0 else 0
    print(
        f"[{row['label']}] n={row['n']} ok={row['ok']}/{row['n']} "
        f"success={row['success_rate']:.1f}% "
        f"p50={row['p50_ms']:.0f}ms p95={row['p95_ms']:.0f}ms p99={row['p99_ms']:.0f}ms "
        f"avg={row['avg_ms']:.0f}ms max={row['max_ms']:.0f}ms "
        f"rps={rps:.1f} 429={row['rate_limited']} "
        f"cache={row['cache_hits']} kb={row['kb_hits']} tools={row['tool_or_sop']}"
    )
    if row["errors"]:
        print(f"  errors: {row['errors']}")


def main() -> int:
    pause_s = float(os.environ.get("WAVE_PAUSE_S", "2"))
    skip_api = API_ROUNDS <= 0
    print(f"API_BASE={API_BASE}")
    print(
        f"API_ROUNDS={API_ROUNDS} CHAT_ROUNDS={CHAT_ROUNDS} "
        f"levels={CONCURRENCY_LEVELS} WAVE_PAUSE_S={pause_s}"
    )

    # Probe
    probe = api_get("/healthz")
    if not probe.ok:
        print(f"API unreachable: {probe.error or probe.status}")
        return 2
    print(f"healthz ok ({probe.latency_ms:.0f}ms)")

    report: dict[str, Any] = {"api": [], "chat": []}

    if not skip_api:
        print("\n=== Phase A: API read traffic ===")
        for c in CONCURRENCY_LEVELS:
            samples, wall = run_pool(build_api_jobs(API_ROUNDS), c)
            row = summarize(f"api c={c}", samples)
            row["concurrency"] = c
            row["wall_s"] = wall
            row["rps"] = row["n"] / wall if wall else 0
            report["api"].append(row)
            print_summary(row, wall)
            if row["rate_limited"] and pause_s > 0:
                print(f"  rate-limited — pausing {pause_s:.0f}s")
                time.sleep(pause_s)

    print("\n=== Phase B: Chat usability under load ===")
    # Cold-ish first wave at c=1, then hotter concurrency with repeated FAQs.
    for idx, c in enumerate(CONCURRENCY_LEVELS):
        n = max(4, CHAT_ROUNDS // max(1, len(CONCURRENCY_LEVELS) - idx))
        # Fewer chats at high concurrency to control LLM spend.
        if c >= 10:
            n = min(n, 12)
        if c >= 20:
            n = min(n, 8)
        if pause_s > 0 and idx:
            time.sleep(pause_s)
        samples, wall = run_pool(build_chat_jobs(n, warm_cache=True), c)
        row = summarize(f"chat c={c}", samples)
        row["concurrency"] = c
        row["wall_s"] = wall
        row["rps"] = row["n"] / wall if wall else 0
        report["chat"].append(row)
        print_summary(row, wall)
        if row["rate_limited"]:
            print("  rate-limited — sleeping 65s for window reset")
            time.sleep(65)

    out_path = os.environ.get("LOAD_REPORT", "scripts/load_usability_report.json")
    existing: dict[str, Any] = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as fh:
                existing = json.load(fh)
        except Exception:  # noqa: BLE001
            existing = {}
    existing.update(report)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
