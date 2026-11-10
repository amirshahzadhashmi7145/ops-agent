"use client";

import { Loader2, Send, Square } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  disabled?: boolean;
  isSending?: boolean;
  onSend: (message: string) => void;
  onStop?: () => void;
}

export function ChatInput({ disabled, isSending, onSend, onStop }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <div className="shrink-0 border-t border-border/80 bg-background/90 px-4 py-3 backdrop-blur-sm md:px-5">
      <div className="w-full">
        <div className="flex items-end gap-2 rounded-xl border border-border bg-card p-1.5 shadow-sm">
          <Textarea
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="Ask about an account, device, order, or policy…"
            className="max-h-32 min-h-9 resize-none border-0 bg-transparent px-2.5 py-2 text-sm shadow-none focus-visible:ring-0"
            disabled={disabled}
            rows={1}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit();
              }
            }}
          />
          {isSending ? (
            <Button
              type="button"
              onClick={onStop}
              size="icon"
              variant="destructive"
              title="Stop generating"
              aria-label="Stop generating"
              className="h-8 w-8 shrink-0 rounded-lg"
            >
              {/* Pulsing stop square signals both "working" and "click to stop". */}
              <Square className="h-3 w-3 animate-pulse" fill="currentColor" />
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={disabled || !value.trim()}
              size="icon"
              title="Send message"
              aria-label="Send message"
              className="h-8 w-8 shrink-0 rounded-lg"
            >
              {disabled ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
            </Button>
          )}
        </div>
        <p className="mt-1.5 px-1 text-[10px] text-muted-foreground">
          Enter to send · Shift+Enter for a new line
        </p>
      </div>
    </div>
  );
}
