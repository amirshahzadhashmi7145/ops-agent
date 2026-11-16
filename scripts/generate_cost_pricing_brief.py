#!/usr/bin/env python3
"""Generate a clean printable Ops Agent cost & pricing brief (PDF)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#1c2434")
MUTED = colors.HexColor("#5b6578")
LINE = colors.HexColor("#d8dee8")
SOFT = colors.HexColor("#f4f6fa")
ACCENT = colors.HexColor("#2f5bff")
OK = colors.HexColor("#0f7b4a")


def money(value: float, digits: int | None = None) -> str:
    if value is None:
        return "—"
    v = float(value)
    if digits is None:
        if v == 0:
            return "$0"
        if abs(v) < 0.01:
            return f"${v:.4f}"
        if abs(v) < 1:
            return f"${v:.3f}"
        return f"${v:,.2f}"
    return f"${v:,.{digits}f}"


def pct(value: float) -> str:
    return f"{float(value):.0f}%"


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "TitleClean",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=INK,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleClean",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "h": ParagraphStyle(
            "HeadingClean",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=INK,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "BodyClean",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "SmallClean",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=INK,
            alignment=TA_CENTER,
        ),
        "kpi_hint": ParagraphStyle(
            "KpiHint",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
    }
    return styles


def kpi_row(styles, items: list[tuple[str, str, str]]):
    cells = []
    for label, value, hint in items:
        inner = Table(
            [
                [Paragraph(label, styles["kpi_label"])],
                [Paragraph(value, styles["kpi_value"])],
                [Paragraph(hint, styles["kpi_hint"])],
            ],
            colWidths=[1.7 * inch],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        cells.append(inner)
    table = Table([cells], colWidths=[1.85 * inch] * len(items))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def simple_table(headers: list[str], rows: list[list[str]], col_widths: list[float]):
    data = [headers] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.35, LINE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, LINE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    table.setStyle(TableStyle(style))
    return table


def callout(styles, title: str, body: str):
    content = Paragraph(f"<b>{title}</b><br/>{body}", styles["callout"])
    table = Table([[content]], colWidths=[7.1 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef3ff")),
                ("BOX", (0, 0), (-1, -1), 0.8, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def generate(stats: dict, out_path: Path) -> None:
    styles = build_styles()
    tickets = stats["tickets"]
    pricing = stats["pricing"]
    hosting = stats["hosting"]
    decision = stats["decision"]
    cache = stats.get("cache") or {}

    days = int(stats["days"])
    spend = float(stats["spend_usd"])
    ticket_count = int(tickets["conversations"])
    avg_cost = float(tickets["avg_cost_usd"])
    p50 = float(tickets["p50_cost_usd"])
    p90 = float(tickets["p90_cost_usd"])
    p99 = float(tickets["p99_cost_usd"])
    max_cost = float(tickets["max_cost_usd"])
    avg_turns = float(tickets["avg_user_turns"])
    p90_turns = float(tickets["p90_user_turns"])
    max_turns = float(tickets["max_user_turns"])
    cost_per_turn = float(tickets["cost_per_user_turn_usd"]) or (avg_cost / max(avg_turns, 1))
    markup = float(pricing.get("markup") or 4)
    host_mo = float(hosting["monthly_usd"])
    generated = datetime.now(timezone.utc).strftime("%d %b %Y")

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Ops Agent — Cost & Pricing Brief",
        author="Ops Agent",
    )

    story = []
    story.append(Paragraph("Ops Agent — Cost & Pricing Brief", styles["title"]))
    story.append(
        Paragraph(
            f"Printable handoff for pricing strategy · {days}-day live snapshot · Generated {generated} UTC",
            styles["subtitle"],
        )
    )

    story.append(
        callout(
            styles,
            f"Recommendation: {decision.get('label') or 'Usage-based'}",
            "Charge for the whole ticket (conversation), not per message. "
            "Short tickets stay cheap; long tool-heavy tickets cost more — usage-based pricing "
            "follows that naturally. Keep a small platform fee to cover hosting.",
        )
    )

    story.append(Paragraph("1. Live snapshot", styles["h"]))
    story.append(
        kpi_row(
            styles,
            [
                ("Tickets", f"{ticket_count}", f"Last {days} days"),
                ("LLM spend", money(spend, 3), "Vendor cost"),
                ("Avg / ticket", money(avg_cost), f"{avg_turns:.1f} user turns"),
                ("Hosting", money(host_mo, 0) + "/mo", hosting.get("profile", "")),
            ],
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "A <b>ticket</b> is one conversation. It may have 5, 10, 20, or 30+ messages. "
            "We sum all LLM cost for that conversation, then look at the distribution across tickets. "
            "We do <b>not</b> multiply “98 tickets × one fixed message price.”",
            styles["body"],
        )
    )

    story.append(Paragraph("2. Cost by ticket length", styles["h"]))
    story.append(
        Paragraph(
            "Each <b>user turn</b> is one customer message that the assistant answers "
            "(tools + model). Total messages in the thread are usually about 2× user turns "
            "(customer + assistant). Estimates use live cost per user turn "
            f"({money(cost_per_turn)}).",
            styles["body"],
        )
    )

    length_rows = []
    for turns in (5, 10, 20, 30):
        vendor = cost_per_turn * turns
        bill = vendor * markup
        length_rows.append(
            [
                f"{turns} user turns",
                f"~{turns * 2} messages",
                money(vendor),
                money(bill),
                "Long / complex" if turns >= 20 else "Short–medium",
            ]
        )
    # Observed mix row
    length_rows.append(
        [
            f"Observed avg ({avg_turns:.1f})",
            f"~{max(1, round(avg_turns * 2))} messages",
            money(avg_cost),
            money(avg_cost * markup),
            "Current mix",
        ]
    )
    length_rows.append(
        [
            f"Observed p90 ({p90_turns:.0f})",
            f"~{max(1, round(p90_turns * 2))} messages",
            money(p90),
            money(p90 * markup),
            "Heavier tickets",
        ]
    )

    story.append(
        simple_table(
            ["Ticket length", "Approx. messages", "Vendor LLM cost", f"Bill @ {markup:.0f}×", "Notes"],
            length_rows,
            [1.45 * inch, 1.35 * inch, 1.35 * inch, 1.2 * inch, 1.75 * inch],
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Observed spread: p50 {money(p50)} · p90 {money(p90)} · p99 {money(p99)} · max {money(max_cost)}. "
            f"Longest ticket in sample: {max_turns:.0f} user turns. "
            f"Cache hit rate: {pct(cache.get('hit_rate_pct') or 0)}.",
            styles["small"],
        )
    )

    story.append(Paragraph("3. Pricing options (same volumes)", styles["h"]))
    story.append(
        Paragraph(
            "Compare customer bill at common monthly volumes. Vendor cost always includes "
            f"{money(host_mo, 0)}/mo hosting plus LLM.",
            styles["body"],
        )
    )

    model_by_key = {m["key"]: m for m in pricing.get("models") or []}
    volumes = [200, 500, 2000, 8000]
    price_headers = ["Model"] + [f"{v:,} tix" for v in volumes]
    price_rows = []
    for key, label in (
        ("usage", "Usage-based"),
        ("hybrid", "Hybrid seat+overage"),
        ("subscription", "Flat subscription"),
        ("per_ticket", "Per ticket only"),
    ):
        model = model_by_key.get(key)
        if not model:
            continue
        by_vol = {int(s["tickets_per_month"]): s for s in model.get("scenarios") or []}
        row = [label]
        for v in volumes:
            s = by_vol.get(v)
            row.append(money(float(s["customer_bill_usd"]), 0) if s else "—")
        price_rows.append(row)

    story.append(
        simple_table(
            price_headers,
            price_rows,
            [1.7 * inch] + [1.35 * inch] * 4,
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Suggested list: ~{money(float(pricing.get('usage_this_mix_per_ticket_usd') or 0))} per typical ticket "
            f"(LLM×{markup:.0f}), ~{money(float(pricing.get('usage_long_ticket_usd') or 0))} for a long ticket, "
            f"plus platform fee so hosting stays covered. Seat sketch: "
            f"{money(float(pricing.get('seat_usd') or 0), 0)}/mo with "
            f"{int(pricing.get('included_tickets') or 0):,} tickets included.",
            styles["small"],
        )
    )

    story.append(Paragraph("4. How to decide", styles["h"]))
    bullets = [
        "<b>Prefer usage-based</b> if ticket length varies a lot (your sample already does: fat tail).",
        "<b>Add a platform / seat fee</b> so $71 hosting is not lost at low volume.",
        "<b>Quote long tickets separately</b> (p90 / 20–30 turn examples) so tool-heavy work does not sink a flat plan.",
        "<b>Revisit after more production traffic</b> — this sample includes demos/evals; avg turns may rise.",
    ]
    for item in bullets:
        story.append(Paragraph(f"- {item}", styles["body"]))

    why = decision.get("why") or []
    if why:
        story.append(Paragraph("Signals from this snapshot", styles["h"]))
        for line in why[:4]:
            story.append(Paragraph(f"- {line}", styles["small"]))

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Internal handoff only · Figures are vendor LLM + configured hosting, not final customer SKUs.",
            styles["footer"],
        )
    )

    doc.build(story)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stats",
        type=Path,
        default=None,
        help="Path to usage stats JSON (default: fetch or /tmp/usage_stats_30d.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "Ops-Agent-Cost-Pricing-Brief.pdf",
    )
    parser.add_argument("--api", default="http://localhost:8001/api/usage/stats?days=30")
    args = parser.parse_args()

    stats = None
    if args.stats and args.stats.exists():
        stats = json.loads(args.stats.read_text(encoding="utf-8"))
    else:
        tmp = Path("/tmp/usage_stats_30d.json")
        if tmp.exists():
            stats = json.loads(tmp.read_text(encoding="utf-8"))
        else:
            try:
                import urllib.request

                with urllib.request.urlopen(args.api, timeout=15) as resp:
                    stats = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"Could not load usage stats: {exc}", file=sys.stderr)
                return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    generate(stats, args.out)
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
