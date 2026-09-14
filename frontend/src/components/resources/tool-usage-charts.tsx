"use client";

import type { ToolCallLogListItem } from "@/types/tool-log";

const DAY_COUNT = 14;

function dayKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function lastDays(count: number) {
  const days: { key: string; label: string }[] = [];
  const cursor = new Date();
  cursor.setHours(0, 0, 0, 0);
  for (let offset = count - 1; offset >= 0; offset -= 1) {
    const date = new Date(cursor);
    date.setDate(cursor.getDate() - offset);
    days.push({
      key: dayKey(date),
      label: date.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    });
  }
  return days;
}

export function ToolUsageCharts({ calls }: { calls: ToolCallLogListItem[] }) {
  const days = lastDays(DAY_COUNT);
  const totals = days.map((day) => {
    const matching = calls.filter((call) => dayKey(new Date(call.created_at)) === day.key);
    return {
      ...day,
      success: matching.filter((call) => call.success).length,
      failed: matching.filter((call) => !call.success).length,
    };
  });
  const maxVolume = Math.max(1, ...totals.map((day) => day.success + day.failed));
  const successCount = calls.filter((call) => call.success).length;
  const failedCount = calls.length - successCount;
  const avgLatency = calls.length
    ? Math.round(
        calls.reduce((sum, call) => sum + (call.latency_ms ?? 0), 0) / calls.length,
      )
    : 0;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(220px,0.8fr)]">
      <section className="surface-card p-5">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold">Calls over time</p>
            <p className="text-xs text-muted-foreground">Last {DAY_COUNT} days</p>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Success
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-red-400" /> Failed
            </span>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex h-36 items-end gap-1.5">
            {totals.map((day) => {
              const volume = day.success + day.failed;
              const heightPct = volume ? Math.max(14, (volume / maxVolume) * 100) : 6;
              return (
                <div
                  key={day.key}
                  className="flex h-full min-w-0 flex-1 items-end"
                  title={`${day.label}: ${day.success} succeeded, ${day.failed} failed`}
                >
                  <div
                    className="flex w-full flex-col justify-end overflow-hidden rounded-t-md bg-muted/40"
                    style={{ height: `${heightPct}%` }}
                  >
                    {day.failed > 0 && (
                      <div className="w-full min-h-0.5 bg-red-400" style={{ flexGrow: day.failed }} />
                    )}
                    {day.success > 0 && (
                      <div className="w-full min-h-0.5 bg-emerald-500" style={{ flexGrow: day.success }} />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex gap-1.5">
            {totals.map((day) => (
              <span key={day.key} className="min-w-0 flex-1 truncate text-center text-[10px] text-muted-foreground">
                {day.label}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="surface-card flex flex-col justify-between p-5">
        <div>
          <p className="text-sm font-semibold">Outcomes</p>
          <p className="text-xs text-muted-foreground">Across loaded calls</p>
        </div>
        <div className="mt-4 space-y-3">
          <div className="flex h-3 overflow-hidden rounded-full bg-muted">
            <div
              className="bg-emerald-500"
              style={{ width: calls.length ? `${(successCount / calls.length) * 100}%` : "0%" }}
            />
            <div
              className="bg-red-400"
              style={{ width: calls.length ? `${(failedCount / calls.length) * 100}%` : "0%" }}
            />
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">Succeeded</dt>
              <dd className="font-semibold text-emerald-600 dark:text-emerald-400">{successCount}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Failed</dt>
              <dd className="font-semibold text-red-500">{failedCount}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Success rate</dt>
              <dd className="font-semibold">
                {calls.length ? `${Math.round((successCount / calls.length) * 100)}%` : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Avg latency</dt>
              <dd className="font-semibold">{calls.length ? `${avgLatency}ms` : "—"}</dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  );
}
