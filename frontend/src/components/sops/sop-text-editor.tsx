"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import type { ResourceListItem } from "@/types/resource";
import { cn } from "@/lib/utils";

interface SopTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  tools: ResourceListItem[];
  placeholder?: string;
}

function measureCaretOffset(textarea: HTMLTextAreaElement, position: number) {
  const mirror = document.createElement("div");
  const style = window.getComputedStyle(textarea);
  const properties = [
    "boxSizing",
    "width",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "borderTopWidth",
    "borderRightWidth",
    "borderBottomWidth",
    "borderLeftWidth",
    "fontFamily",
    "fontSize",
    "fontWeight",
    "fontStyle",
    "letterSpacing",
    "textTransform",
    "textAlign",
    "lineHeight",
    "whiteSpace",
    "wordBreak",
    "overflowWrap",
  ] as const;

  mirror.style.position = "absolute";
  mirror.style.visibility = "hidden";
  mirror.style.pointerEvents = "none";
  mirror.style.top = "0";
  mirror.style.left = "-9999px";
  for (const property of properties) {
    mirror.style[property] = style[property];
  }
  mirror.style.whiteSpace = "pre-wrap";
  mirror.style.wordWrap = "break-word";
  mirror.style.height = "auto";
  mirror.style.overflow = "hidden";

  const text = textarea.value.slice(0, position);
  mirror.textContent = text;
  const marker = document.createElement("span");
  marker.textContent = "\u200b";
  mirror.appendChild(marker);
  document.body.appendChild(mirror);

  const top = marker.offsetTop - textarea.scrollTop;
  const left = marker.offsetLeft - textarea.scrollLeft;
  document.body.removeChild(mirror);

  return {
    top: Math.max(0, top + 22),
    left: Math.min(Math.max(0, left), textarea.clientWidth - 280),
  };
}

export function SopTextEditor({ value, onChange, tools, placeholder }: SopTextEditorProps) {
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStart, setMentionStart] = useState<number | null>(null);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const [menuOffset, setMenuOffset] = useState({ top: 0, left: 0 });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const suggestions = useMemo(() => {
    if (mentionQuery === null) return [];
    const q = mentionQuery.toLowerCase();
    return tools
      .filter((tool) => tool.name.toLowerCase().includes(q))
      .slice(0, 8);
  }, [mentionQuery, tools]);

  useEffect(() => {
    setHighlightIndex(0);
  }, [mentionQuery, suggestions.length]);

  const updateMentionState = (next: string, cursor: number) => {
    onChange(next);
    const before = next.slice(0, cursor);
    const match = before.match(/@([a-zA-Z0-9_-]*)$/);
    if (match) {
      setMentionQuery(match[1]);
      setMentionStart(cursor - match[0].length);
      requestAnimationFrame(() => {
        if (!textareaRef.current) return;
        setMenuOffset(measureCaretOffset(textareaRef.current, cursor - match[0].length));
      });
    } else {
      setMentionQuery(null);
      setMentionStart(null);
    }
  };

  const insertMention = (name: string) => {
    if (mentionStart === null || !textareaRef.current) return;
    const cursor = textareaRef.current.selectionStart;
    const before = value.slice(0, mentionStart);
    const after = value.slice(cursor);
    const next = `${before}@${name} ${after}`;
    onChange(next);
    setMentionQuery(null);
    setMentionStart(null);
    requestAnimationFrame(() => {
      const pos = before.length + name.length + 2;
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(pos, pos);
    });
  };

  const scopeLabel = (scope: string) =>
    scope === "internal" ? "Internal" : scope === "external" ? "External" : scope;

  return (
    <div className="relative">
      <Textarea
        ref={textareaRef}
        value={value}
        placeholder={placeholder}
        className="min-h-56 font-mono text-sm"
        onChange={(event) =>
          updateMentionState(event.target.value, event.target.selectionStart)
        }
        onClick={(event) =>
          updateMentionState(event.currentTarget.value, event.currentTarget.selectionStart)
        }
        onKeyUp={(event) => {
          if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
            updateMentionState(event.currentTarget.value, event.currentTarget.selectionStart);
          }
        }}
        onKeyDown={(event) => {
          if (mentionQuery === null || suggestions.length === 0) return;
          if (event.key === "Escape") {
            event.preventDefault();
            setMentionQuery(null);
            setMentionStart(null);
            return;
          }
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setHighlightIndex((index) => (index + 1) % suggestions.length);
            return;
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setHighlightIndex((index) => (index - 1 + suggestions.length) % suggestions.length);
            return;
          }
          if (event.key === "Enter" || event.key === "Tab") {
            event.preventDefault();
            insertMention(suggestions[highlightIndex]?.name ?? suggestions[0].name);
          }
        }}
        onScroll={() => {
          if (mentionStart === null || !textareaRef.current) return;
          setMenuOffset(measureCaretOffset(textareaRef.current, mentionStart));
        }}
      />
      {mentionQuery !== null && suggestions.length > 0 && (
        <div
          className="absolute z-20 max-h-56 w-[min(100%,20rem)] overflow-auto rounded-xl border border-border bg-card shadow-lg"
          style={{ top: menuOffset.top, left: menuOffset.left }}
        >
          {suggestions.map((tool, index) => (
            <button
              key={tool.id}
              type="button"
              className={cn(
                "flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm",
                index === highlightIndex ? "bg-muted" : "hover:bg-muted",
              )}
              onMouseDown={(event) => {
                event.preventDefault();
                insertMention(tool.name);
              }}
            >
              <span className="font-medium text-foreground">@{tool.name}</span>
              <Badge
                variant={tool.tool_scope === "internal" ? "default" : "secondary"}
                className="text-[10px]"
              >
                {scopeLabel(tool.tool_scope)}
              </Badge>
            </button>
          ))}
        </div>
      )}
      <p className={cn("mt-1.5 text-xs text-muted-foreground")}>
        Type <span className="font-mono">@</span> to insert a tool by name (internal or external).
        Use arrows and Enter to pick from the list.
      </p>
    </div>
  );
}
