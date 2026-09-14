"use client";

import { MarkdownMessage } from "@/components/chat/markdown-message";
import { StatusPill } from "@/components/kb/status-pill";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import type { KbReference } from "@/types/kb";

interface ReferenceReviewProps {
  reference: KbReference | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit: () => void;
  onToggleEnabled: (enabled: boolean) => void;
  onReprocess?: () => void;
  togglingEnabled?: boolean;
  reprocessing?: boolean;
}

export function ReferenceReview({
  reference,
  open,
  onOpenChange,
  onEdit,
  onToggleEnabled,
  onReprocess,
  togglingEnabled,
  reprocessing,
}: ReferenceReviewProps) {
  if (!reference) return null;

  const isReady = reference.processing_status === "ready";
  const isFailed = reference.processing_status === "failed";
  const isProcessing = ["queued", "formatting", "indexing"].includes(reference.processing_status);

  const processingLabel =
    reference.processing_status === "queued"
      ? "Queued for processing..."
      : reference.processing_status === "formatting"
        ? "Formatting content with AI..."
        : "Indexing chunks for search...";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle>{reference.title}</DialogTitle>
            <StatusPill status={reference.processing_status} />
            {!reference.enabled && <Badge variant="secondary">Disabled</Badge>}
          </div>
          <DialogDescription>
            {isReady
              ? "Compare your original input with the processed reference."
              : isFailed
                ? reference.processing_error || "Processing failed."
                : processingLabel}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {isProcessing && (
            <div className="flex items-center gap-3 rounded-xl border border-dashed border-primary/30 bg-primary/5 px-4 py-4">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
              </span>
              <p className="text-sm text-foreground">{processingLabel}</p>
            </div>
          )}

          <section>
            <h3 className="mb-2 text-sm font-semibold text-foreground">What you entered</h3>
            <p className="mb-2 text-xs text-muted-foreground">
              Your original content and formatting. This is what was sent to processing.
            </p>
            <div className="max-h-72 overflow-y-auto rounded-xl border bg-muted/30 p-4">
              <MarkdownMessage content={reference.raw_text || ""} variant="document" />
            </div>
          </section>

          {isReady && (
            <section>
              <h3 className="mb-2 text-sm font-semibold text-foreground">Processed reference</h3>
              <p className="mb-2 text-xs text-muted-foreground">
                Structured output from the formatter (used for search). Not a copy of your editor formatting.
              </p>
              {reference.summary && (
                <div className="mb-4 rounded-xl border border-primary/20 bg-primary/5 p-4">
                  <p className="text-sm leading-relaxed text-foreground">{reference.summary}</p>
                </div>
              )}
              <div className="max-h-80 overflow-y-auto rounded-xl border p-4">
                <MarkdownMessage content={reference.markdown || ""} variant="document" />
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
                {reference.source_url && (
                  <span>
                    Source:{" "}
                    <a
                      href={reference.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary underline"
                    >
                      {reference.source_url}
                    </a>
                  </span>
                )}
                <span>Processed {new Date(reference.updated_at).toLocaleString()}</span>
                <span>{reference.chunk_count} chunks indexed</span>
              </div>
            </section>
          )}

          {isFailed && reference.processing_error && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
              {reference.processing_error}
            </div>
          )}
        </div>

        <Separator />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={onEdit}>
              Edit
            </Button>
            {isFailed && onReprocess && (
              <Button variant="outline" onClick={onReprocess} disabled={reprocessing}>
                {reprocessing ? "Retrying..." : "Retry processing"}
              </Button>
            )}
          </div>
          <Button
            variant={reference.enabled ? "outline" : "default"}
            onClick={() => onToggleEnabled(!reference.enabled)}
            disabled={togglingEnabled || isProcessing}
          >
            {reference.enabled ? "Disable" : "Enable"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
