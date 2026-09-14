"use client";

import { motion } from "framer-motion";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ConversationListItem } from "@/types/chat";

interface ChatHistoryBarProps {
  conversations: ConversationListItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
}

function formatRelativeTime(value: string) {
  const date = new Date(value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ChatHistoryBar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
}: ChatHistoryBarProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeItemRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeId || !activeItemRef.current || !scrollRef.current) return;
    activeItemRef.current.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "center",
    });
  }, [activeId, conversations.length]);

  return (
    <section className="shrink-0 border-t border-border/80 bg-card/80 backdrop-blur-sm">
      <div className="flex items-center gap-3 px-4 py-3 md:px-6">

        <Button
          size="sm"
          className="h-9 shrink-0 rounded-full px-4 shadow-sm"
          onClick={onNewChat}
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          New chat
        </Button>

        <div className="relative min-w-0 flex-1">
          <div
            ref={scrollRef}
            className="flex gap-2 overflow-x-auto px-1 pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {conversations.length === 0 ? (
              <div className="flex h-9 items-center gap-2 rounded-full border border-dashed border-border px-4 text-xs text-muted-foreground">
                <MessageSquare className="h-3.5 w-3.5" />
                No past conversations yet
              </div>
            ) : (
              conversations.map((conversation) => {
                const isActive = activeId === conversation.id;
                return (
                  <motion.div
                    key={conversation.id}
                    ref={isActive ? activeItemRef : undefined}
                    initial={{ opacity: 0, scale: 0.96 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className={cn(
                      "group flex shrink-0 items-center gap-0.5 rounded-full border transition-colors",
                      isActive
                        ? "border-primary/30 bg-primary/10 shadow-sm"
                        : "border-border/80 bg-background hover:bg-muted/70",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelect(conversation.id)}
                      className="flex max-w-[220px] items-center gap-2 rounded-full px-3 py-1.5 text-left sm:max-w-[260px]"
                    >
                      <MessageSquare
                        className={cn(
                          "h-3.5 w-3.5 shrink-0",
                          isActive ? "text-primary" : "text-muted-foreground",
                        )}
                      />
                      <span
                        className={cn(
                          "truncate text-sm font-medium",
                          isActive ? "text-foreground" : "text-foreground/80",
                        )}
                      >
                        {conversation.title}
                      </span>
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {formatRelativeTime(conversation.updated_at)}
                      </span>
                    </button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-0 w-0 shrink-0 overflow-hidden rounded-full p-0 opacity-0 transition-all group-hover:h-7 group-hover:w-7 group-hover:p-0 group-hover:opacity-100"
                      onClick={() => onDelete(conversation.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </motion.div>
                );
              })
            )}
          </div>
          <div className="pointer-events-none absolute inset-y-0 left-0 w-3 bg-gradient-to-r from-card/90 to-transparent" />
          <div className="pointer-events-none absolute inset-y-0 right-0 w-3 bg-gradient-to-l from-card/90 to-transparent" />
        </div>
      </div>
    </section>
  );
}
