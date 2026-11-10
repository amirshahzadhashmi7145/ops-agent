"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUsageStats } from "@/hooks/use-usage";
import { cn } from "@/lib/utils";
import type { HostingStats, PricingModel, UsageStats } from "@/types/usage";

function usd(value: number, digits = 2) {
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

function bill(value: number) {
  return usd(value, value < 100 ? 2 : 0);
}

function compact(value: number) {
  return value.toLocaleString();
}

export default function UsagePage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useUsageStats(days);

  return (
    <div className="w-full px-5 py-5">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="page-header">Pricing model</h2>
          <p className="page-description">
            Metered LLM + configured VM hosting — pick subscription, usage, per-ticket, or hybrid.
          </p>
        </div>
        <div className="flex gap-1">
          {[7, 30, 90].map((value) => (
            <Button
              key={value}
              size="sm"
              variant={days === value ? "default" : "outline"}
              onClick={() => setDays(value)}
            >
              {value}d
            </Button>
          ))}
        </div>
      </div>

      {isLoading || !data ? (
        <div className="grid gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="surface-card h-24 animate-pulse bg-muted/30" />
          ))}
        </div>
      ) : (
        <>
          <HostingPanel hosting={data.hosting} />
          {data.tickets.observed ? <DecisionBoard data={data} /> : <EmptyUsage />}
        </>
      )}
    </div>
  );
}

function EmptyUsage() {
  return (
    <div className="surface-card p-6">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">Live sample</p>
      <h3 className="mt-1 text-xl font-semibold tracking-tight">Need live tickets</h3>
      <p className="mt-2 max-w-xl text-sm text-muted-foreground">
        Hosting above is your configured VM plan. LLM percentiles and the model pick only appear after Chat
        records real spend.
      </p>
    </div>
  );
}

function HostingPanel({ hosting }: { hosting: HostingStats }) {
  return (
    <div className="mb-5 surface-card overflow-hidden p-0">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">
            Hosting / VM
          </p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight">
            {usd(hosting.monthly_usd, 0)}
            <span className="ml-1 text-sm font-medium text-muted-foreground">/ month</span>
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {hosting.provider_hint} · profile <span className="font-medium text-foreground">{hosting.profile}</span> ·
            configured plan (edit HOSTING_* env), not a scraped cloud invoice.
          </p>
        </div>
        <div className="text-right text-xs text-muted-foreground">
          <p>
            This window ({hosting.window_days}d):{" "}
            <span className="font-medium tabular-nums text-foreground">{usd(hosting.window_usd)}</span>
          </p>
          <p className="mt-0.5">
            At {compact(hosting.assumed_capacity_tickets)} tickets:{" "}
            <span className="font-medium tabular-nums text-foreground">
              {usd(hosting.at_capacity_per_ticket_usd)}/ticket
            </span>
          </p>
        </div>
      </div>
      <div className="grid gap-0 sm:grid-cols-2 xl:grid-cols-4">
        {hosting.line_items.map((item) => (
          <div key={item.key} className="border-t border-border px-5 py-4 sm:border-t-0 sm:border-l first:border-l-0">
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {item.label}
            </p>
            <p className="mt-1.5 text-xl font-semibold tabular-nums">{usd(item.monthly_usd, 0)}</p>
            <p className="mt-0.5 text-[11px] font-medium text-foreground">{item.specs}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{item.note}</p>
          </div>
        ))}
      </div>
      <div className="border-t border-border px-5 py-3">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Hosting share by ticket volume
        </p>
        <div className="flex flex-wrap gap-4 text-xs">
          {hosting.per_ticket_by_volume.map((row) => (
            <div key={row.tickets_per_month} className="tabular-nums">
              <span className="text-muted-foreground">{compact(row.tickets_per_month)}/mo → </span>
              <span className="font-medium">{usd(row.hosting_per_ticket_usd)}/ticket</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DecisionBoard({ data }: { data: UsageStats }) {
  const pick = data.decision;
  const volume = 2000;
  const tail = data.decision.signals.p90_vs_p50;
  const rowAtVolume =
    data.pricing.models[0]?.scenarios.find((item) => item.tickets_per_month === volume) ??
    data.pricing.models[0]?.scenarios[0];

  return (
    <>
      <div className="mb-5 surface-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">
              Recommended model
            </p>
            <h3 className="mt-1 text-xl font-semibold tracking-tight">{pick.label}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {pick.sample === "observed"
                ? `From ${compact(pick.signals.ticket_count)} metered tickets in this window.`
                : `From ${compact(pick.signals.ticket_count)} metered tickets — still a thin sample.`}
            </p>
          </div>
          <div className="flex gap-1.5">
            <Badge variant={pick.confidence === "high" ? "default" : "secondary"}>
              {pick.confidence} confidence
            </Badge>
            <Badge variant="outline">{pick.sample}</Badge>
          </div>
        </div>
        <ul className="mt-4 space-y-1.5 text-sm text-foreground">
          {pick.why.map((line) => (
            <li key={line} className="flex gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Median thread LLM"
          value={usd(data.tickets.p50_cost_usd, 4)}
          hint={`${data.tickets.avg_user_turns.toFixed(1)} user turns · ${data.tickets.avg_llm_calls.toFixed(1)} LLM calls`}
        />
        <StatCard
          label="Long ticket LLM (p90)"
          value={usd(data.tickets.p90_cost_usd, 4)}
          hint={`${data.tickets.p90_user_turns.toFixed(0)} user turns · ${tail.toFixed(1)}× median`}
        />
        <StatCard
          label="Hosting / month"
          value={usd(data.hosting.monthly_usd, 0)}
          hint={`Fixed VM bill · ${usd((rowAtVolume?.vendor_hosting_usd ?? data.hosting.monthly_usd) / volume, 4)}/ticket at ${compact(volume)}`}
        />
        <StatCard
          label="Cache hit rate"
          value={`${data.cache.hit_rate_pct.toFixed(0)}%`}
          hint="Prompt + semantic hits. Higher = better seat margin"
          tone={data.cache.hit_rate_pct >= 25 ? "good" : undefined}
        />
      </div>

      {data.pricing.models.length > 0 ? (
        <div className="mb-5 surface-card overflow-x-auto p-4">
          <div className="mb-3 flex items-end justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">Compare models at {compact(volume)} tickets / month</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                COGS = metered LLM ({usd(data.pricing.cost_per_ticket_usd, 4)}/ticket) + fixed hosting (
                {usd(data.hosting.monthly_usd, 0)}/mo). Seat {usd(data.pricing.seat_usd, 0)} recovers hosting
                and {compact(data.pricing.included_tickets)} tickets at {data.pricing.markup.toFixed(1)}×.
              </p>
            </div>
          </div>
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Model</th>
                <th className="py-2 pr-3 font-medium">Customer pays</th>
                <th className="py-2 pr-3 font-medium">LLM</th>
                <th className="py-2 pr-3 font-medium">Hosting</th>
                <th className="py-2 pr-3 font-medium">Margin</th>
                <th className="py-2 font-medium">If tickets run long</th>
              </tr>
            </thead>
            <tbody>
              {data.pricing.models.map((model) => {
                const row = model.scenarios.find((item) => item.tickets_per_month === volume) ?? model.scenarios[0];
                const selected = model.key === pick.key;
                return (
                  <tr key={model.key} className={cn("border-b border-border/60", selected && "bg-primary/5")}>
                    <td className="py-2.5 pr-3">
                      <p className="font-semibold text-foreground">
                        {model.label}
                        {selected ? <span className="ml-2 text-[10px] font-medium text-primary">Pick</span> : null}
                      </p>
                      <p className="mt-0.5 max-w-xs text-[11px] text-muted-foreground">{model.summary}</p>
                    </td>
                    <td className="py-2.5 pr-3 font-medium tabular-nums">{bill(row.customer_bill_usd)}</td>
                    <td className="py-2.5 pr-3 tabular-nums text-muted-foreground">{bill(row.vendor_llm_usd)}</td>
                    <td className="py-2.5 pr-3 tabular-nums text-muted-foreground">{bill(row.vendor_hosting_usd)}</td>
                    <td className="py-2.5 pr-3 tabular-nums">{row.vendor_margin_pct.toFixed(0)}%</td>
                    <td className="py-2.5 tabular-nums text-muted-foreground">{bill(row.heavy_customer_bill_usd)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <VolumeStrip models={data.pricing.models} selected={pick.key} />
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="surface-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Unit economics
          </p>
          <ul className="mt-3 space-y-2 text-xs">
            <Row label="Tickets in window" value={compact(data.tickets.conversations)} />
            <Row
              label="User turns / ticket"
              value={`${data.tickets.avg_user_turns.toFixed(1)} avg · ${data.tickets.p90_user_turns.toFixed(0)} p90 · ${data.tickets.max_user_turns.toFixed(0)} max`}
            />
            <Row
              label="Tokens / ticket"
              value={`${compact(data.tickets.avg_tokens)} avg · ${compact(data.tickets.p90_tokens)} p90`}
            />
            <Row
              label="Mean / p99 / max LLM"
              value={`${usd(data.tickets.avg_cost_usd, 4)} · ${usd(data.tickets.p99_cost_usd, 4)} · ${usd(data.tickets.max_cost_usd, 4)}`}
            />
            <Row label="LLM spend this window" value={`${usd(data.spend_usd)} (saved ${usd(data.savings_usd)})`} />
            <Row label="Hosting this window" value={usd(data.hosting.window_usd)} />
          </ul>
        </div>
        <div className="surface-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            What the mix is telling you
          </p>
          <ul className="mt-3 space-y-2 text-xs">
            <Row label="Semantic cache hits" value={compact(data.calls.semantic_hits)} />
            <Row label="Prompt cache hits" value={compact(data.calls.prompt_cache_hits)} />
            <Row label="Cheap tickets (≤ half mean)" value={`${data.tickets.cheap_share_pct.toFixed(0)}%`} />
            <Row label="Heavy tail" value={`${data.tickets.heavy_share_pct.toFixed(0)}%`} />
            <Row
              label="Model rates"
              value={`${data.pricing.model_rates.model} · in ${usd(data.pricing.model_rates.input_per_million_usd)}/1M`}
            />
            <Row label="Stack services" value={data.hosting.services.join(" · ")} />
          </ul>
        </div>
      </div>
    </>
  );
}

function VolumeStrip({
  models,
  selected,
}: {
  models: PricingModel[];
  selected: PricingModel["key"] | null;
}) {
  const volumes = models[0]?.scenarios.map((item) => item.tickets_per_month) ?? [];
  return (
    <div className="mt-4 overflow-x-auto">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        Customer bill by volume (usage includes hosting platform fee)
      </p>
      <table className="w-full text-left text-[11px]">
        <thead>
          <tr className="text-muted-foreground">
            <th className="py-1 pr-2 font-medium">Tickets / mo</th>
            {volumes.map((volume) => (
              <th key={volume} className="py-1 pr-2 font-medium tabular-nums">
                {compact(volume)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.key} className={cn(model.key === selected && "text-foreground")}>
              <td className="py-1 pr-2 font-medium">{model.label}</td>
              {model.scenarios.map((row) => (
                <td key={row.tickets_per_month} className="py-1 pr-2 tabular-nums">
                  {bill(row.customer_bill_usd)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium tabular-nums">{value}</span>
    </li>
  );
}

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone?: "good";
}) {
  return (
    <div className="surface-card p-4">
      <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-1.5 text-2xl font-semibold tracking-tight tabular-nums",
          tone === "good" ? "text-emerald-600 dark:text-emerald-400" : "text-foreground",
        )}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}
