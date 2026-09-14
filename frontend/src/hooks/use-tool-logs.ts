"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchToolLog, fetchToolLogSummary, fetchToolLogs } from "@/lib/api";

export function useToolLogSummary() {
  return useQuery({
    queryKey: ["tool-logs", "summary"],
    queryFn: fetchToolLogSummary,
    refetchInterval: 5000,
  });
}

export function useToolLogs(options: {
  toolName?: string | null;
  resourceId?: string | null;
  enabled?: boolean;
}) {
  const toolName = options.toolName ?? null;
  const resourceId = options.resourceId ?? null;
  const enabled = options.enabled ?? Boolean(toolName || resourceId);

  return useQuery({
    queryKey: ["tool-logs", "list", toolName, resourceId],
    queryFn: () => fetchToolLogs({ toolName, resourceId, limit: 200 }),
    enabled,
    refetchInterval: 5000,
  });
}

export function useToolLog(id: string | null) {
  return useQuery({
    queryKey: ["tool-logs", "detail", id],
    queryFn: () => fetchToolLog(id!),
    enabled: Boolean(id),
  });
}
