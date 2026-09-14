import { cn } from "@/lib/utils";
import { Check, CircleDot, Clock3, Loader2, X } from "lucide-react";
import type { ProcessingStatus } from "@/types/kb";

const STATUS_CONFIG: Record<
  ProcessingStatus,
  { label: string; className: string; icon: typeof Clock3; spin?: boolean }
> = {
  queued: {
    label: "Queued",
    className: "bg-muted text-muted-foreground",
    icon: Clock3,
  },
  formatting: {
    label: "Processing",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
    icon: CircleDot,
  },
  indexing: {
    label: "Indexing",
    className: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200",
    icon: Loader2,
    spin: true,
  },
  ready: {
    label: "Ready",
    className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
    icon: Check,
  },
  failed: {
    label: "Failed",
    className: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
    icon: X,
  },
};

export function StatusPill({ status }: { status: ProcessingStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  return (
    <span
      className={cn(
        "inline-flex h-6 min-w-28 items-center justify-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.className,
      )}
    >
      <Icon className={cn("h-3.5 w-3.5", config.spin && "animate-spin")} />
      {config.label}
    </span>
  );
}
