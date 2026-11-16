"use client";

import type { UsageStats } from "@/types/usage";

function formatUsd(value: number) {
  if (!Number.isFinite(value)) return "—";
  if (value > 0 && value < 0.01) return "<$0.01";
  return `$${value.toFixed(value >= 10 ? 2 : 3)}`;
}

export function UsageOverviewCharts({ stats }: { stats: UsageStats }) {
  const days = stats.by_day ?? [];
  const maxSpend = Math.max(0.001, ...days.map((day) => day.spend_usd));
  const cacheHit = stats.cache?.hit_rate_pct ?? 0;
  const llmCalls = stats.calls?.llm ?? 0;
  const semanticHits = stats.calls?.semantic_hits ?? 0;
  const totalCalls = Math.max(1, llmCalls + semanticHits);

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.5fr)_minmax(220px,0.85fr)]">
      <section className="surface-card p-4">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-foreground">Spend</p>
            <p className="text-xs text-muted-foreground">Last {stats.days} days</p>
          </div>
          <div className="text-right">
            <p className="text-lg font-medium tabular-nums text-foreground">
              {formatUsd(stats.spend_usd)}
            </p>
            {stats.savings_usd > 0 ? (
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                Saved {formatUsd(stats.savings_usd)} ({stats.savings_pct.toFixed(0)}%)
              </p>
            ) : (
              <p className="text-[11px] text-muted-foreground">LLM + cache window</p>
            )}
          </div>
        </div>
        {days.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border/70 bg-muted/20 px-3 py-10 text-center text-xs text-muted-foreground">
            No usage yet — spend appears after chat traffic.
          </p>
        ) : (
          <div className="space-y-2">
            <div className="flex h-32 items-end gap-1">
              {days.map((day) => {
                const heightPct = day.spend_usd
                  ? Math.max(8, (day.spend_usd / maxSpend) * 100)
                  : 4;
                const label = new Date(`${day.day}T12:00:00`).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                });
                return (
                  <div
                    key={day.day}
                    className="flex h-full min-w-0 flex-1 items-end"
                    title={`${label}: ${formatUsd(day.spend_usd)} · ${day.calls} calls`}
                  >
                    <div
                      className="w-full rounded-t-md bg-primary/70"
                      style={{ height: `${heightPct}%` }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="flex gap-1">
              {days.map((day, index) => {
                const show =
                  index === 0 || index === days.length - 1 || index === Math.floor(days.length / 2);
                if (!show) {
                  return <span key={day.day} className="min-w-0 flex-1" />;
                }
                const label = new Date(`${day.day}T12:00:00`).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                });
                return (
                  <span
                    key={day.day}
                    className="min-w-0 flex-1 truncate text-center text-[10px] text-muted-foreground"
                  >
                    {label}
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </section>

      <section className="surface-card flex flex-col justify-between p-4">
        <div>
          <p className="text-sm font-medium text-foreground">Efficiency</p>
          <p className="text-xs text-muted-foreground">Cache vs live LLM</p>
        </div>
        <div className="mt-4 space-y-3">
          <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
            <div
              className="bg-emerald-500"
              style={{ width: `${(semanticHits / totalCalls) * 100}%` }}
            />
            <div
              className="bg-primary/60"
              style={{ width: `${(llmCalls / totalCalls) * 100}%` }}
            />
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Cache hit</dt>
              <dd className="font-medium tabular-nums">{cacheHit.toFixed(0)}%</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">LLM calls</dt>
              <dd className="font-medium tabular-nums">{llmCalls}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Conversations</dt>
              <dd className="font-medium tabular-nums">{stats.tickets.conversations}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Avg / ticket</dt>
              <dd className="font-medium tabular-nums">
                {stats.tickets.observed ? formatUsd(stats.tickets.avg_cost_usd) : "—"}
              </dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  );
}
