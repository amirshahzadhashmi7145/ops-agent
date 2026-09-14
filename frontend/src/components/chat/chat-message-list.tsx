"use client";

import { motion } from "framer-motion";
import { Bot, ScrollText, User } from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatTracePanel } from "@/components/chat/chat-trace-panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ChatMessage, PipelineTraceEvent } from "@/types/chat";

const MarkdownMessage = dynamic(
  () => import("@/components/chat/markdown-message").then((m) => m.MarkdownMessage),
  {
    loading: () => (
      <p className="animate-pulse text-sm text-muted-foreground">Loading message…</p>
    ),
  },
);

/** Title of the SOP followed in this message, if any (for the "Followed SOP" chip). */
function matchedSopTitle(trace: PipelineTraceEvent[]): string | null {
  const matched = trace.find((event) => event.type === "sop_matched");
  return matched?.type === "sop_matched" ? matched.title : null;
}

interface ChatMessageListProps {
  messages: ChatMessage[];
  streamingStatus?: string | null;
  pendingAssistant?: string | null;
  isSending?: boolean;
  onSuggestionClick?: (text: string) => void;
}

const SUGGESTIONS = [
  "Hi there",
  "What can you help me with?",
  "Get device health for my dash cam",
];

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1">
      {[0, 1, 2].map((index) => (
        <motion.span
          key={index}
          className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60"
          animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
          transition={{ duration: 1, repeat: Infinity, delay: index * 0.15 }}
        />
      ))}
    </div>
  );
}

export function ChatMessageList({
  messages,
  streamingStatus,
  pendingAssistant,
  isSending,
  onSuggestionClick,
}: ChatMessageListProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  const isNearBottom = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return true;
    const distance = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distance < 120;
  }, []);

  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "end" });
  }, []);

  useEffect(() => {
    if (isNearBottom()) {
      scrollToBottom();
    }
  }, [messages, streamingStatus, pendingAssistant, isSending, isNearBottom, scrollToBottom]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      setShowScrollButton(!isNearBottom());
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, [isNearBottom]);

  const showEmptyState =
    messages.length === 0 && !streamingStatus && !pendingAssistant && !isSending;

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollContainerRef}
        className="h-full overflow-y-auto scroll-smooth px-4 py-6 md:px-8"
      >
        <div className="mx-auto flex min-h-full max-w-6xl flex-col">
          {showEmptyState ? (
            <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Bot className="h-7 w-7" />
              </div>
              <h3 className="text-xl font-semibold tracking-tight text-foreground">
                Ops Agent
              </h3>
              <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
                Ask about device health, operations, or start with a greeting. I&apos;ll call
                registered APIs only when your request needs them.
              </p>
              {onSuggestionClick && (
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => onSuggestionClick(suggestion)}
                      className="rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground/90 shadow-sm transition-colors hover:bg-muted"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6 pb-4">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={cn(
                    "flex gap-3",
                    message.role === "user" ? "flex-row-reverse" : "flex-row",
                  )}
                >
                  <div
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "border border-border bg-card text-primary",
                    )}
                  >
                    {message.role === "user" ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "min-w-0 max-w-[85%]",
                      message.role === "user" ? "items-end" : "items-start",
                    )}
                  >
                    <div
                      className={cn(
                        "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "border border-border/80 bg-card text-foreground",
                      )}
                    >
                      {message.role === "assistant" &&
                        (() => {
                          const sopTitle = matchedSopTitle(message.pipeline_trace);
                          return sopTitle ? (
                            <div className="mb-2 inline-flex items-center gap-1.5 rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary">
                              <ScrollText className="h-3 w-3" />
                              Followed SOP: {sopTitle}
                            </div>
                          ) : null;
                        })()}
                      {message.role === "assistant" ? (
                        <MarkdownMessage content={message.content} />
                      ) : (
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                      )}
                      {message.role === "assistant" && message.pipeline_trace.length > 0 && (
                        <ChatTracePanel trace={message.pipeline_trace} />
                      )}
                    </div>
                    <p
                      className={cn(
                        "mt-1.5 px-1 text-[11px] text-muted-foreground",
                        message.role === "user" ? "text-right" : "text-left",
                      )}
                    >
                      {formatTime(message.created_at)}
                    </p>
                  </div>
                </motion.div>
              ))}

              {(isSending || streamingStatus || pendingAssistant) && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-card text-primary">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="max-w-[85%] rounded-2xl border border-border/80 bg-card px-4 py-3 text-sm shadow-sm">
                    {streamingStatus && !pendingAssistant && (
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">
                          {streamingStatus}
                        </p>
                        <TypingIndicator />
                      </div>
                    )}
                    {pendingAssistant && (
                      <MarkdownMessage content={pendingAssistant} className="text-foreground" />
                    )}
                    {isSending && !streamingStatus && !pendingAssistant && <TypingIndicator />}
                  </div>
                </motion.div>
              )}
            </div>
          )}
          <div ref={bottomRef} className="h-px shrink-0" />
        </div>
      </div>

      {showScrollButton && (
        <div className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="pointer-events-auto rounded-full shadow-md"
            onClick={() => scrollToBottom()}
          >
            Scroll to latest
          </Button>
        </div>
      )}
    </div>
  );
}
