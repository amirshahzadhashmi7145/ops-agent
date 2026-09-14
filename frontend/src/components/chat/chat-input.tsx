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
    <div className="shrink-0 border-t border-border/80 bg-background/90 px-4 py-4 backdrop-blur-sm md:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm">
          <Textarea
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="Message Ops Agent..."
            className="max-h-36 min-h-11 resize-none border-0 bg-transparent px-3 py-2.5 shadow-none focus-visible:ring-0"
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
              className="h-10 w-10 shrink-0 rounded-xl"
            >
              {/* Pulsing stop square signals both "working" and "click to stop". */}
              <Square className="h-3.5 w-3.5 animate-pulse" fill="currentColor" />
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={disabled || !value.trim()}
              size="icon"
              title="Send message"
              aria-label="Send message"
              className="h-10 w-10 shrink-0 rounded-xl"
            >
              {disabled ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
