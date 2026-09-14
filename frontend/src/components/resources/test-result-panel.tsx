"use client";

import { motion } from "framer-motion";
import { CheckCircle2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { fadeSlideUp } from "@/lib/motion";
import type { ResourceTestResult } from "@/types/resource";

interface TestResultPanelProps {
  result: ResourceTestResult | null;
  loading?: boolean;
}

export function TestResultPanel({ result, loading }: TestResultPanelProps) {
  if (loading) {
    return (
      <motion.div
        variants={fadeSlideUp}
        initial="hidden"
        animate="visible"
        className="rounded-xl border border-border bg-muted/40 p-4 text-sm text-muted-foreground"
      >
        Running test query...
      </motion.div>
    );
  }

  if (!result) return null;

  const success = result.success;

  return (
    <motion.div
      variants={fadeSlideUp}
      initial="hidden"
      animate="visible"
      className="min-w-0 space-y-3 overflow-hidden rounded-xl border border-border bg-muted/40 p-4"
    >
      <div className="flex flex-wrap items-center gap-2">
        {success ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500 dark:text-red-400" />
        )}
        <Badge variant={success ? "secondary" : "destructive"} className="font-mono">
          {result.status_code ?? "ERR"}
        </Badge>
        <span className="text-sm text-muted-foreground">{result.latency_ms}ms</span>
        {result.resolved_url && (
          <span className="truncate text-xs text-muted-foreground/70">{result.resolved_url}</span>
        )}
      </div>

      {result.error && (
        <p className="text-sm text-red-600">{result.error}</p>
      )}

      {result.body !== null && result.body !== undefined && (
        <div className="scrollbar-none max-h-48 overflow-x-hidden overflow-y-auto rounded-lg border border-border bg-card p-3">
          <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed text-foreground/80 [overflow-wrap:anywhere]">
            {typeof result.body === "string"
              ? result.body
              : JSON.stringify(result.body, null, 2)}
          </pre>
        </div>
      )}
    </motion.div>
  );
}
