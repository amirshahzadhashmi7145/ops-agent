"use client";

import { motion } from "framer-motion";
import {
  History as HistoryIcon,
  Inbox,
  Mail,
  MessageSquare,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { LocalTime } from "@/components/local-time";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ConversationStatusPill } from "@/components/chat/conversation-status-pill";
import {
  useConversations,
  useDeleteConversation,
  useEndConversation,
  useHandoverConversation,
  useReopenConversation,
} from "@/hooks/use-chat";
import { useClearMessages, useMessage, useMessages } from "@/hooks/use-messages";
import { buttonMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { ConversationListItem, ConversationStatus } from "@/types/chat";

type Tab = "conversations" | "drafts";
type StatusFilter = "all" | ConversationStatus;

export default function HistoryPage() {
  const [tab, setTab] = useState<Tab>("conversations");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const { data: conversations = [], isLoading } = useConversations();
  const deleteConversation = useDeleteConversation();
  const endConversation = useEndConversation();
  const handoverConversation = useHandoverConversation();
  const reopenConversation = useReopenConversation();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: drafts = [], isLoading: draftsLoading } = useMessages();
  const clearDrafts = useClearMessages();
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
  const { data: selectedDraft } = useMessage(selectedDraftId);

  const filtered = useMemo(() => {
    if (statusFilter === "all") return conversations;
    return conversations.filter((item) => item.status === statusFilter);
  }, [conversations, statusFilter]);

  const liveCount = conversations.filter((item) => item.status === "live").length;
  const endedCount = conversations.filter((item) => item.status === "ended").length;
  const escalatedCount = conversations.filter((item) => item.status === "escalated").length;
  const selected = conversations.find((item) => item.id === selectedId) ?? null;

  const pillLabel = (message: (typeof drafts)[number]) => {
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
      <div className="w-full px-5 py-5">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="page-header">History</h2>
            <p className="page-description">
              Past and live conversations — open one in Chat, or end it when the ticket is done.
            </p>
          </div>
          <div className="flex rounded-lg border border-border bg-muted/30 p-1">
            <TabButton active={tab === "conversations"} onClick={() => setTab("conversations")}>
              Conversations
            </TabButton>
            <TabButton active={tab === "drafts"} onClick={() => setTab("drafts")}>
              Drafts
              {drafts.length > 0 ? (
                <span className="ml-1.5 tabular-nums text-muted-foreground">{drafts.length}</span>
              ) : null}
            </TabButton>
          </div>
        </div>

        {tab === "conversations" ? (
          <>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {(
                [
                  ["all", `All (${conversations.length})`],
                  ["live", `Live (${liveCount})`],
                  ["escalated", `Handed over (${escalatedCount})`],
                  ["ended", `Ended (${endedCount})`],
                ] as const
              ).map(([key, label]) => (
                <Button
                  key={key}
                  size="sm"
                  variant={statusFilter === key ? "secondary" : "outline"}
                  onClick={() => setStatusFilter(key)}
                >
                  {label}
                </Button>
              ))}
            </div>

            {isLoading ? (
              <div className="surface-card space-y-3 p-6">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="h-16 animate-pulse rounded-lg bg-muted/60" />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center">
                <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
                  <HistoryIcon className="h-6 w-6" />
                </div>
                <h3 className="text-sm font-medium">No conversations yet</h3>
                <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                  Start a ticket in Chat — it will show here as Live, then Ended when you close it
                  or it goes idle.
                </p>
                <Link href="/chat" className="mt-6">
                  <Button>Open Chat</Button>
                </Link>
              </div>
            ) : (
              <div className="surface-card divide-y divide-border overflow-hidden">
                {filtered.map((conversation, index) => (
                  <ConversationRow
                    key={conversation.id}
                    conversation={conversation}
                    index={index}
                    onOpen={() => setSelectedId(conversation.id)}
                    onEnd={() => endConversation.mutate(conversation.id)}
                    onHandover={() =>
                      handoverConversation.mutate({
                        id: conversation.id,
                        reason: "Manual handover from History",
                      })
                    }
                    onReopen={() => reopenConversation.mutate(conversation.id)}
                    onDelete={() => deleteConversation.mutate(conversation.id)}
                    ending={endConversation.isPending}
                    handingOver={handoverConversation.isPending}
                    reopening={reopenConversation.isPending}
                    deleting={deleteConversation.isPending}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            <div className="mb-4 flex justify-end">
              <motion.div {...buttonMotion}>
                <Button
                  variant="outline"
                  disabled={!drafts.length || clearDrafts.isPending}
                  onClick={() => clearDrafts.mutate()}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear drafts
                </Button>
              </motion.div>
            </div>
            {draftsLoading ? (
              <div className="surface-card space-y-3 p-6">
                {Array.from({ length: 4 }).map((_, index) => (
                  <div key={index} className="h-14 animate-pulse rounded-lg bg-muted/60" />
                ))}
              </div>
            ) : drafts.length === 0 ? (
              <div className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center">
                <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
                  <Inbox className="h-6 w-6" />
                </div>
                <h3 className="text-sm font-medium">No drafts</h3>
                <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                  Workflow tools may leave demo emails and tickets here — nothing is sent outside this app.
                </p>
              </div>
            ) : (
              <div className="surface-card divide-y divide-border overflow-hidden">
                {drafts.map((message) => (
                  <button
                    key={message.id}
                    type="button"
                    onClick={() => setSelectedDraftId(message.id)}
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
                    <LocalTime
                      value={message.created_at}
                      className="shrink-0 text-xs text-muted-foreground"
                    />
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <Dialog open={Boolean(selectedId)} onOpenChange={() => setSelectedId(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="pr-8">{selected?.title || "Conversation"}</DialogTitle>
            <DialogDescription>
              {selected ? (
                <span className="inline-flex flex-wrap items-center gap-2 pt-1">
                  <ConversationStatusPill status={selected.status} />
                  <span>
                    {selected.message_count} message{selected.message_count === 1 ? "" : "s"}
                  </span>
                </span>
              ) : null}
            </DialogDescription>
          </DialogHeader>
          {selected ? (
            <div className="space-y-4 text-sm">
              {selected.status_reason ? (
                <p className="rounded-xl border border-border bg-muted/40 px-4 py-3 text-sm text-foreground">
                  <span className="text-muted-foreground">Reason: </span>
                  {selected.status_reason}
                </p>
              ) : null}
              {selected.preview ? (
                <p className="rounded-xl border border-border bg-muted/40 px-4 py-3 text-muted-foreground">
                  {selected.preview}
                </p>
              ) : (
                <p className="text-muted-foreground">No messages in this conversation yet.</p>
              )}
              <div className="flex flex-wrap gap-2">
                <Link href={`/chat?c=${selected.id}`}>
                  <Button>
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Open in Chat
                  </Button>
                </Link>
                {selected.status === "live" ? (
                  <>
                    <Button
                      variant="outline"
                      disabled={handoverConversation.isPending}
                      onClick={() =>
                        handoverConversation.mutate({
                          id: selected.id,
                          reason: "Manual handover from History",
                        })
                      }
                    >
                      Hand over
                    </Button>
                    <Button
                      variant="outline"
                      disabled={endConversation.isPending}
                      onClick={() => endConversation.mutate(selected.id)}
                    >
                      End conversation
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="outline"
                    disabled={reopenConversation.isPending}
                    onClick={() => reopenConversation.mutate(selected.id)}
                  >
                    Reopen
                  </Button>
                )}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(selectedDraftId)} onOpenChange={() => setSelectedDraftId(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{selectedDraft?.subject || "Draft"}</DialogTitle>
          </DialogHeader>
          {selectedDraft ? (
            <div className="space-y-4 text-sm">
              <div className="rounded-xl border border-border bg-muted/40 px-4 py-3">
                <p>
                  <span className="text-muted-foreground">From:</span> {selectedDraft.from_address}
                </p>
                <p>
                  <span className="text-muted-foreground">To:</span> {selectedDraft.to_address}
                </p>
                <p>
                  <span className="text-muted-foreground">Created:</span>{" "}
                  <LocalTime value={selectedDraft.created_at} />
                </p>
              </div>
              <pre className="whitespace-pre-wrap rounded-xl border border-border bg-card p-4 font-sans leading-relaxed text-foreground">
                {selectedDraft.body}
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

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm transition-colors",
        active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function ConversationRow({
  conversation,
  index,
  onOpen,
  onEnd,
  onHandover,
  onReopen,
  onDelete,
  ending,
  handingOver,
  reopening,
  deleting,
}: {
  conversation: ConversationListItem;
  index: number;
  onOpen: () => void;
  onEnd: () => void;
  onHandover: () => void;
  onReopen: () => void;
  onDelete: () => void;
  ending: boolean;
  handingOver: boolean;
  reopening: boolean;
  deleting: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.02, 0.2) }}
      className="flex w-full items-start gap-3 px-5 py-4 transition-colors hover:bg-muted/40"
    >
      <button type="button" onClick={onOpen} className="min-w-0 flex-1 text-left">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate font-medium text-foreground">{conversation.title}</p>
          <ConversationStatusPill status={conversation.status} />
          <span className="text-xs text-muted-foreground tabular-nums">
            {conversation.message_count} msg
          </span>
        </div>
        <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
          {conversation.status_reason || conversation.preview || "No messages yet"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Updated <LocalTime value={conversation.updated_at} />
          {conversation.status === "ended" && conversation.ended_at ? (
            <>
              {" · "}Ended <LocalTime value={conversation.ended_at} />
            </>
          ) : null}
        </p>
      </button>
      <div className="flex shrink-0 flex-col gap-1 sm:flex-row">
        <Link href={`/chat?c=${conversation.id}`}>
          <Button size="sm" variant="outline">
            Open
          </Button>
        </Link>
        {conversation.status === "live" ? (
          <>
            <Button size="sm" variant="ghost" disabled={handingOver} onClick={onHandover}>
              Hand over
            </Button>
            <Button size="sm" variant="ghost" disabled={ending} onClick={onEnd}>
              End
            </Button>
          </>
        ) : (
          <Button size="sm" variant="ghost" disabled={reopening} onClick={onReopen}>
            Reopen
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="text-red-600"
          disabled={deleting}
          onClick={onDelete}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </motion.div>
  );
}
