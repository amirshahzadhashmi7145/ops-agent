"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { ChatHistoryBar } from "@/components/chat/chat-history-bar";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  useConversation,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useEndConversation,
  useReopenConversation,
  sendMessageWithStream,
} from "@/hooks/use-chat";
import type { ChatMessage, ChatStreamEvent } from "@/types/chat";

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
  const reopenConversation = useReopenConversation();
  const { data: conversation, refetch: refetchConversation } = useConversation(activeConversationId);
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
  const [pendingAssistant, setPendingAssistant] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (conversation) {
      queueMicrotask(() => {
        setLocalMessages(conversation.messages);
      });
    } else if (!activeConversationId) {
      queueMicrotask(() => {
        setLocalMessages([]);
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

  const status = conversation?.status ?? "live";

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
                  Follows Workflows, searches Articles, and calls Tools only when needed.
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {status === "live" ? (
                  <Badge className="gap-1.5 bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-300">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                    Live
                  </Badge>
                ) : (
                  <Badge variant="outline" className="gap-1.5 text-muted-foreground">
                    <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50" />
                    Ended
                  </Badge>
                )}
                {activeConversationId ? (
                  status === "live" ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={endConversation.isPending || isSending}
                      onClick={() => endConversation.mutate(activeConversationId)}
                    >
                      End
                    </Button>
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
            disabled={isSending || status === "ended"}
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
