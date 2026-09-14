"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ChatHistoryBar } from "@/components/chat/chat-history-bar";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import {
  useConversation,
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  sendMessageWithStream,
} from "@/hooks/use-chat";
import type { ChatMessage, ChatStreamEvent } from "@/types/chat";

export default function ChatPage() {
  const { data: conversations = [] } = useConversations();
  const createConversation = useCreateConversation();
  const deleteConversation = useDeleteConversation();
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
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

  const handleNewChat = async () => {
    const created = await createConversation.mutateAsync();
    setActiveConversationId(created.id);
    setLocalMessages([]);
  };

  const handleDelete = async (id: string) => {
    await deleteConversation.mutateAsync(id);
    if (activeConversationId === id) {
      setActiveConversationId(null);
      setLocalMessages([]);
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
                setStreamingStatus(`Following SOP: ${event.title}`);
              }
              if (event.type === "final_answer") {
                setPendingAssistant(event.content);
              }
            },
          },
          controller.signal,
        );

        if (!activeConversationId) {
          setActiveConversationId(result.conversationId);
        }

        setLocalMessages((current) => [...current, result.assistantMessage]);
        await refetchConversation();
      } catch (error) {
        // A user-initiated stop is expected; anything else is a real failure.
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
    [activeConversationId, refetchConversation],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return (
      <div className="flex h-[calc(100vh)] min-h-0 flex-col overflow-hidden">
        <div className="flex min-h-0 flex-1 flex-col bg-[radial-gradient(ellipse_at_top,oklch(0.97_0.02_275),transparent_55%)] dark:bg-[radial-gradient(ellipse_at_top,oklch(0.26_0.05_275),transparent_55%)]">
          <div className="shrink-0 border-b border-border/80 bg-background/70 px-6 py-4 backdrop-blur-sm md:px-8">
            <div className="mx-auto max-w-6xl">
              <h2 className="truncate text-lg font-semibold tracking-tight text-foreground">
                {conversation?.title || "New conversation"}
              </h2>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Ask naturally — I only call tools when your request needs registered APIs.
              </p>
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
            disabled={isSending}
            isSending={isSending}
            onSend={handleSend}
            onStop={handleStop}
          />
        </div>

        <ChatHistoryBar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={setActiveConversationId}
          onNewChat={handleNewChat}
          onDelete={handleDelete}
        />
      </div>
  );
}
