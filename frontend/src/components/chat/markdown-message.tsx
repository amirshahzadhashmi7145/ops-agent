"use client";

import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

interface MarkdownMessageProps {
  content: string;
  className?: string;
  /** Chat bubbles use compact headings; document review uses larger hierarchy. */
  variant?: "chat" | "document";
}

function buildComponents(variant: "chat" | "document"): Components {
  const isDocument = variant === "document";

  return {
    p: ({ children }) => (
      <p className="my-2 first:mt-0 last:mb-0 leading-relaxed text-sm">{children}</p>
    ),
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    em: ({ children }) => <em className="italic">{children}</em>,
    ul: ({ children }) => (
      <ul className="my-2 list-disc space-y-1 pl-5 first:mt-0 last:mb-0 text-sm">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="my-2 list-decimal space-y-1 pl-5 first:mt-0 last:mb-0 text-sm">{children}</ol>
    ),
    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
    h1: ({ children }) => (
      <h1
        className={cn(
          "mb-2 mt-4 font-bold tracking-tight first:mt-0",
          isDocument ? "text-2xl" : "text-base font-semibold",
        )}
      >
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2
        className={cn(
          "mb-2 mt-4 font-bold tracking-tight first:mt-0",
          isDocument ? "text-xl" : "text-base font-semibold",
        )}
      >
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3
        className={cn(
          "mb-1.5 mt-3 font-semibold first:mt-0",
          isDocument ? "text-lg" : "text-sm",
        )}
      >
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="mb-1.5 mt-3 text-base font-semibold first:mt-0">{children}</h4>
    ),
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-primary underline underline-offset-2 hover:opacity-80"
      >
        {children}
      </a>
    ),
    code: ({ className, children }) => {
      const isBlock = (className ?? "").includes("language-");
      if (isBlock) {
        return (
          <code className="block whitespace-pre-wrap rounded-md bg-black/10 px-1 py-0.5 font-mono text-xs dark:bg-white/10">
            {children}
          </code>
        );
      }
      return (
        <code className="rounded bg-black/10 px-1 py-0.5 font-mono text-[0.85em] dark:bg-white/10">
          {children}
        </code>
      );
    },
    pre: ({ children }) => (
      <pre className="my-2 overflow-x-auto rounded-md bg-black/10 p-3 text-xs first:mt-0 last:mb-0 dark:bg-white/10">
        {children}
      </pre>
    ),
    blockquote: ({ children }) => (
      <blockquote className="my-2 border-l-2 border-current/30 pl-3 italic opacity-90">
        {children}
      </blockquote>
    ),
    table: ({ children }) => (
      <div className="my-2 overflow-x-auto">
        <table className="w-full border-collapse text-xs">{children}</table>
      </div>
    ),
    th: ({ children }) => (
      <th className="border border-current/20 px-2 py-1 text-left font-semibold">{children}</th>
    ),
    td: ({ children }) => <td className="border border-current/20 px-2 py-1">{children}</td>,
    hr: () => <hr className="my-3 border-current/20" />,
  };
}

/** Turns literal `\\n` sequences into real newlines when LLM JSON parsing left them escaped. */
function normalizeMarkdown(content: string): string {
  if (!content.includes("\\n")) return content;
  // Only rewrite when content looks like escaped JSON strings, not real Windows paths.
  if (content.includes("\n") && !content.includes("\\n\\n") && (content.match(/\\n/g) || []).length < 2) {
    return content;
  }
  return content.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
}

export function MarkdownMessage({
  content,
  className,
  variant = "chat",
}: MarkdownMessageProps) {
  const normalized = normalizeMarkdown(content);

  return (
    <div className={cn("break-words text-foreground", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={buildComponents(variant)}>
        {normalized}
      </ReactMarkdown>
    </div>
  );
}
