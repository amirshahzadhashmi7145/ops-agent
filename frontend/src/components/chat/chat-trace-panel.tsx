"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";
import type { AgentMode, PipelineTraceEvent } from "@/types/chat";

interface ChatTracePanelProps {
  trace: PipelineTraceEvent[];
}

const MODE_LABELS: Record<AgentMode, string> = {
  general_chat: "Chat",
  tool_call: "Tools",
  forced_tool_call: "Tools",
  sop: "SOP",
};

const DETAIL_TYPES = new Set([
  "resource_called",
  "resource_result",
  "kb_search",
  "sop_matched",
  "sop_search",
  "sop_step",
]);

export function ChatTracePanel({ trace }: ChatTracePanelProps) {
  const [open, setOpen] = useState(false);
  const detailEvents = trace.filter((event) => DETAIL_TYPES.has(event.type));
  const modeEvent = trace.find((event) => event.type === "mode");
  const mode = modeEvent?.type === "mode" ? modeEvent.mode : undefined;
  const isSop = mode === "sop";

  if (detailEvents.length === 0 && !modeEvent) {
    return null;
  }

  return (
    <div className="mt-3 rounded-lg border border-border/50 bg-muted/30 px-3 py-2">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        Agent trace
        {mode && (
          <span
            className={cn(
              "ml-1 rounded px-1.5 py-0.5",
              isSop ? "bg-primary/15 font-semibold text-primary" : "bg-muted",
            )}
          >
            {MODE_LABELS[mode] ?? mode}
          </span>
        )}
      </button>
      {open && (
        <div className="mt-2 space-y-1 text-xs text-muted-foreground">
          {detailEvents.map((event, index) => {
            if (event.type === "sop_matched") {
              return (
                <p key={`sop-matched-${index}`} className="text-primary">
                  Matched SOP: <span className="font-medium">{event.title}</span>
                  {typeof event.score === "number" ? ` · ${Math.round(event.score * 100)}% match` : ""}
                </p>
              );
            }
            if (event.type === "sop_search") {
              return (
                <p key={`sop-search-${index}`}>
                  SOP search: <span className="font-mono text-foreground">{event.query}</span>
                  {event.match_count ? ` · ${event.match_count} match(es)` : " · no match"}
                </p>
              );
            }
            if (event.type === "sop_step") {
              return (
                <p key={`sop-step-${index}`}>
                  SOP step → <span className="font-mono text-foreground">{event.tool}</span>
                </p>
              );
            }
            if (event.type === "kb_search") {
              return (
                <p key={`kb-${index}`}>
                  KB search: <span className="font-mono text-foreground">{event.query}</span>
                  {event.match_count ? ` · ${event.match_count} match(es)` : ""}
                </p>
              );
            }
            if (event.type === "resource_called") {
              return (
                <p key={`${event.name}-${index}`}>
                  Called <span className="font-mono text-foreground">{event.name}</span>
                  {event.status_code ? ` · HTTP ${event.status_code}` : ""}
                  {event.latency_ms ? ` · ${event.latency_ms}ms` : ""}
                </p>
              );
            }
            if (event.type === "resource_result") {
              return (
                <p key={`${event.name}-result-${index}`}>
                  Result from <span className="font-mono text-foreground">{event.name}</span>:{" "}
                  {event.success ? "success" : "failed"}
                </p>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}
