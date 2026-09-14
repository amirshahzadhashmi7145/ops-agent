"use client";

import { motion } from "framer-motion";
import { Inbox, Mail, Trash2 } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useClearMessages, useMessage, useMessages } from "@/hooks/use-messages";
import { buttonMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";

export default function MessagesPage() {
  const { data: messages = [], isLoading } = useMessages();
  const clearMutation = useClearMessages();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: selected } = useMessage(selectedId);

  const pillLabel = (message: (typeof messages)[number]) => {
    const kind = message.message_kind || null;
    if (kind === "jira_ticket") return "Jira Ticket";
    if (kind === "support_ticket") return "Support Ticket";
    if (kind === "ticket_note") return "Internal Note";
    if (kind === "email") return "Email";
    if (message.related_entity_type === "jira") return "Jira Ticket";
    if (message.related_entity_type === "ticket") return "Support Ticket";
    if (message.related_entity_type === "email") return "Email";
    return message.related_entity_type || null;
  };

  return (
    <>
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="page-header">Messages</h2>
            <p className="page-description">
              Simulated outbound email outbox from SOP actions — nothing is sent externally.
            </p>
          </div>
          <motion.div {...buttonMotion}>
            <Button
              variant="outline"
              disabled={!messages.length || clearMutation.isPending}
              onClick={() => clearMutation.mutate()}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Clear outbox
            </Button>
          </motion.div>
        </div>

        {isLoading ? (
          <div className="surface-card space-y-3 p-6">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-14 animate-pulse rounded-lg bg-muted/60" />
            ))}
          </div>
        ) : messages.length === 0 ? (
          <div className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center">
            <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
              <Inbox className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold">No messages yet</h3>
            <p className="mt-2 max-w-sm text-sm text-muted-foreground">
              Run subscription cancel or device return flows in Chat to generate confirmation messages here.
            </p>
          </div>
        ) : (
          <div className="surface-card divide-y divide-border overflow-hidden">
            {messages.map((message) => (
              <button
                key={message.id}
                type="button"
                onClick={() => setSelectedId(message.id)}
                className={cn(
                  "flex w-full items-start gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/50",
                  !message.read && "bg-primary/5",
                )}
              >
                <div className="mt-0.5 rounded-lg bg-muted p-2 text-muted-foreground">
                  <Mail className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate font-medium text-foreground">{message.subject}</p>
                    {!message.read && <Badge className="text-[10px]">New</Badge>}
                    {pillLabel(message) && (
                      <Badge variant="outline" className="text-[10px] uppercase">
                        {pillLabel(message)}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 truncate text-sm text-muted-foreground">
                    To {message.to_address} · From {message.from_address}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {new Date(message.created_at).toLocaleString()}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <Dialog open={Boolean(selectedId)} onOpenChange={() => setSelectedId(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{selected?.subject || "Message"}</DialogTitle>
          </DialogHeader>
          {selected ? (
            <div className="space-y-4 text-sm">
              <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
                <p>
                  <span className="text-muted-foreground">From:</span> {selected.from_address}
                </p>
                <p>
                  <span className="text-muted-foreground">To:</span> {selected.to_address}
                </p>
                <p>
                  <span className="text-muted-foreground">Sent:</span>{" "}
                  {new Date(selected.created_at).toLocaleString()}
                </p>
              </div>
              <pre className="whitespace-pre-wrap rounded-xl border border-border bg-card p-4 font-sans leading-relaxed text-foreground">
                {selected.body}
              </pre>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Loading…</p>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
