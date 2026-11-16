"use client";

import { Badge } from "@/components/ui/badge";
import type { ConversationStatus } from "@/types/chat";

export function ConversationStatusPill({ status }: { status: ConversationStatus }) {
  if (status === "live") {
    return (
      <Badge className="gap-1.5 bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-300">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
        Live
      </Badge>
    );
  }
  if (status === "escalated") {
    return (
      <Badge className="gap-1.5 bg-amber-500/15 text-amber-800 hover:bg-amber-500/15 dark:text-amber-300">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
        Handed over
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1.5 text-muted-foreground">
      <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50" />
      Ended
    </Badge>
  );
}

export function conversationStatusDotClass(status: ConversationStatus) {
  if (status === "live") return "bg-emerald-500";
  if (status === "escalated") return "bg-amber-500";
  return "bg-muted-foreground/40";
}
