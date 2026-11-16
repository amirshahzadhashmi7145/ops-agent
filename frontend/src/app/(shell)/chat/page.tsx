"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { ChatHistoryBar } from "@/components/chat/chat-history-bar";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { ConversationStatusPill } from "@/components/chat/conversation-status-pill";
import { Button } from "@/components/ui/button";
import {
  useConversation,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useEndConversation,
  useHandoverConversation,
  useReopenConversation,
  sendMessageWithStream,
} from "@/hooks/use-chat";
import type { ChatMessage, ChatStreamEvent, ConversationStatus } from "@/types/chat";

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-5 text-sm text-muted-foreground">Loading chat…</div>}>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeConversationId = searchParams.get("c");
  const { data: conversations = [] } = useConversations();
  const createConversation = useCreateConversation();
  const deleteConversation = useDeleteConversation();
  const endConversation = useEndConversation();
  const handoverConversation = useHandoverConversation();
  const reopenConversation = useReopenConversation();
  const { data: conversation, refetch: refetchConversation } = useConversation(activeConversationId);
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [turnStatus, setTurnStatus] = useState<ConversationStatus | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (conversation) {
      queueMicrotask(() => {
        setLocalMessages(conversation.messages);
        setTurnStatus(null);
      });
    } else if (!activeConversationId) {
      queueMicrotask(() => {
        setLocalMessages([]);
        setTurnStatus(null);
      });
    }
  }, [conversation, activeConversationId]);

  const syncUrl = useCallback(
    (id: string | null) => {
      if (id) {
        router.replace(`/chat?c=${id}`);
      } else {
        router.replace("/chat");
      }
    },
    [router],
  );

  const handleSelect = (id: string) => {
    syncUrl(id);
  };

  const handleNewChat = async () => {
    const created = await createConversation.mutateAsync();
    setLocalMessages([]);
    syncUrl(created.id);
  };

  const handleDelete = async (id: string) => {
    await deleteConversation.mutateAsync(id);
    if (activeConversationId === id) {
      setLocalMessages([]);
      syncUrl(null);
    }
  };

  const handleSend = useCallback(
    async (message: string) => {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        pipeline_trace: [],
        created_at: new Date().toISOString(),
      };
      setLocalMessages((current) => [...current, userMessage]);
      setIsSending(true);
      setStreamingStatus(null);
      setPendingAssistant(null);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const result = await sendMessageWithStream(
          {
            conversationId: activeConversationId,
            message,
            onEvent: (event: ChatStreamEvent) => {
              if (event.type === "status_update") {
                setStreamingStatus(event.message);
              }
              if (event.type === "sop_matched") {
                setStreamingStatus(`Following workflow: ${event.title}`);
              }
              if (event.type === "final_answer") {
                setPendingAssistant(event.content);
              }
              if (event.type === "conversation_status") {
                setTurnStatus(event.status);
                if (event.status === "ended") {
                  setStreamingStatus("Conversation closed by assistant");
                } else if (event.status === "escalated") {
                  setStreamingStatus("Handed over to a human agent");
                }
              }
              if (event.type === "done" && event.status) {
                setTurnStatus(event.status);
              }
            },
          },
          controller.signal,
        );

        if (!activeConversationId) {
          syncUrl(result.conversationId);
        }

        setLocalMessages((current) => [...current, result.assistantMessage]);
        await refetchConversation();
      } catch (error) {
        if ((error as Error)?.name !== "AbortError") {
          toast.error((error as Error)?.message || "Something went wrong. Please try again.");
        }
      } finally {
        abortRef.current = null;
        setIsSending(false);
        setStreamingStatus(null);
        setPendingAssistant(null);
      }
    },
    [activeConversationId, refetchConversation, syncUrl],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const status = turnStatus ?? conversation?.status ?? "live";
  const locked = status === "ended" || status === "escalated";

  return (
      <div className="flex h-[calc(100vh)] min-h-0 flex-col overflow-hidden">
        <div className="flex min-h-0 flex-1 flex-col bg-[radial-gradient(ellipse_at_top,oklch(0.97_0.02_275),transparent_55%)] dark:bg-[radial-gradient(ellipse_at_top,oklch(0.26_0.05_275),transparent_55%)]">
          <div className="shrink-0 border-b border-border/80 bg-background/80 px-5 py-2.5 backdrop-blur-sm">
            <div className="flex w-full items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="truncate text-sm font-medium tracking-tight text-foreground">
                  {conversation?.title || "New conversation"}
                </h2>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {conversation?.status_reason && locked
                    ? conversation.status_reason
                    : "Follows Workflows, searches Articles, and calls Tools only when needed."}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <ConversationStatusPill status={status} />
                {activeConversationId ? (
                  status === "live" ? (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={handoverConversation.isPending || isSending}
                        onClick={() =>
                          handoverConversation.mutate({
                            id: activeConversationId,
                            reason: "Manual handover from Chat",
                          })
                        }
                      >
                        Hand over
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={endConversation.isPending || isSending}
                        onClick={() => endConversation.mutate(activeConversationId)}
                      >
                        End
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={reopenConversation.isPending || isSending}
                      onClick={() => reopenConversation.mutate(activeConversationId)}
                    >
                      Reopen
                    </Button>
                  )
                ) : null}
              </div>
            </div>
          </div>

          <ChatMessageList
            messages={localMessages}
            streamingStatus={streamingStatus}
            pendingAssistant={pendingAssistant}
            isSending={isSending}
            onSuggestionClick={handleSend}
          />

          <ChatInput
            disabled={isSending || locked}
            isSending={isSending}
            onSend={handleSend}
            onStop={handleStop}
          />
        </div>

        <ChatHistoryBar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelect}
          onNewChat={handleNewChat}
          onDelete={handleDelete}
        />
      </div>
  );
}
