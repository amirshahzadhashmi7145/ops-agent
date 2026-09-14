"use client";

import { ArrowLeft, Activity } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { LocalTime } from "@/components/local-time";
import { JsonPane } from "@/components/resources/json-pane";
import { ToolUsageCharts } from "@/components/resources/tool-usage-charts";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { useResource } from "@/hooks/use-resources";
import { useToolLog, useToolLogs } from "@/hooks/use-tool-logs";
import { cn } from "@/lib/utils";

export default function ResourceLogsPage() {
  const params = useParams<{ id: string }>();
  const resourceId = params.id;
  const { data: resource, isLoading: resourceLoading, isError } = useResource(resourceId);
  const { data: calls = [], isLoading: callsLoading } = useToolLogs({
    resourceId,
    toolName: resource?.name,
    enabled: Boolean(resourceId && resource?.name),
  });
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const { data: selectedLog, isLoading: detailLoading } = useToolLog(selectedLogId);

  useEffect(() => {
    if (callsLoading) return;
    setSelectedLogId((current) => {
      if (!calls.length) return null;
      if (current && calls.some((call) => call.id === current)) return current;
      return calls[0].id;
    });
  }, [calls, callsLoading]);

  const successCount = calls.filter((call) => call.success).length;

  if (resourceLoading) {
    return (
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="mt-6 h-40 animate-pulse rounded-2xl bg-muted/60" />
      </div>
    );
  }

  if (isError || !resource) {
    return (
      <div className="mx-auto max-w-6xl px-8 py-10">
        <Link href="/resources" className={cn(buttonVariants({ variant: "ghost" }), "-ml-2")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Tools & Resources
        </Link>
        <p className="mt-6 text-sm text-muted-foreground">This tool could not be found.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <Link href="/resources" className={cn(buttonVariants({ variant: "ghost" }), "-ml-2 mb-4")}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        Tools & Resources
      </Link>

      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="page-header">{resource.name}</h2>
          <p className="page-description">
            Usage logs for this tool — graphs, request/response, and success vs failure per call.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="font-mono">
            {resource.http_method}
          </Badge>
          <Badge variant={resource.tool_scope === "internal" ? "default" : "secondary"}>
            {resource.tool_scope === "internal" ? "Internal" : "External"}
          </Badge>
          <span className="max-w-sm truncate text-xs text-muted-foreground">{resource.url}</span>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Total calls" value={String(calls.length)} />
        <StatCard label="Succeeded" value={String(successCount)} />
        <StatCard label="Failed" value={String(calls.length - successCount)} />
        <StatCard
          label="Last called"
          value={calls[0]?.created_at ? undefined : "Never"}
          timestamp={calls[0]?.created_at ?? null}
        />
      </div>

      <ToolUsageCharts calls={calls} />

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(280px,0.95fr)_minmax(0,1.15fr)]">
        <section className="surface-card overflow-hidden">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-semibold">Every call</p>
            <p className="text-xs text-muted-foreground">Newest first · click a row for payloads</p>
          </div>
          {callsLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-14 animate-pulse rounded-lg bg-muted/60" />
              ))}
            </div>
          ) : calls.length === 0 ? (
            <div className="flex flex-col items-center px-6 py-16 text-center">
              <div className="mb-3 rounded-2xl bg-primary/10 p-3 text-primary">
                <Activity className="h-5 w-5" />
              </div>
              <p className="max-w-xs text-sm text-muted-foreground">
                No calls yet. Run this tool from Chat or use Test on Tools & Resources.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {calls.map((call) => {
                const active = call.id === selectedLogId;
                return (
                  <button
                    key={call.id}
                    type="button"
                    onClick={() => setSelectedLogId(call.id)}
                    className={cn(
                      "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50",
                      active && "bg-primary/5",
                    )}
                  >
                    <span
                      className={cn(
                        "mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full",
                        call.success ? "bg-emerald-500" : "bg-red-400",
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={call.success ? "secondary" : "destructive"}>
                          {call.success ? "Success" : "Failed"}
                        </Badge>
                        <Badge variant="outline" className="font-mono">
                          {call.response_status ?? (call.success ? "OK" : "ERR")}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] uppercase">
                          {call.source}
                        </Badge>
                        {call.latency_ms != null && (
                          <span className="text-[11px] text-muted-foreground">{call.latency_ms}ms</span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        <LocalTime value={call.created_at} /> · {call.created_by}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        <section className="surface-card overflow-hidden">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-semibold">Request & response</p>
            {selectedLog ? (
              <p className="text-xs text-muted-foreground">
                <LocalTime value={selectedLog.created_at} /> ·{" "}
                {selectedLog.success ? "Success" : "Failed"}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">Select a call to inspect payloads</p>
            )}
          </div>
          <div className="space-y-4 p-4">
            {!selectedLogId ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                Select a call to see request and response bodies.
              </p>
            ) : detailLoading || !selectedLog ? (
              <div className="space-y-3">
                <div className="h-32 animate-pulse rounded-xl bg-muted/60" />
                <div className="h-32 animate-pulse rounded-xl bg-muted/60" />
              </div>
            ) : (
              <>
                <JsonPane title="Request body" value={selectedLog.request} />
                <JsonPane title="Response body" value={selectedLog.response} />
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  timestamp,
}: {
  label: string;
  value?: string;
  timestamp?: string | null;
}) {
  return (
    <div className="surface-card px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      {timestamp ? (
        <p className="mt-1 text-sm font-semibold">
          <LocalTime value={timestamp} />
        </p>
      ) : (
        <p className="mt-1 text-lg font-semibold">{value}</p>
      )}
    </div>
  );
}
