"use client";

import { RefreshCw } from "lucide-react";

import { StatusPill } from "@/components/kb/status-pill";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import type { ProcessingStatus } from "@/types/kb";
import type { SopDocument } from "@/types/sop";

interface SopReviewProps {
  document: SopDocument | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit: () => void;
  onToggleEnabled: (enabled: boolean) => void;
  onReprocess: () => void;
  togglingEnabled?: boolean;
  reprocessing?: boolean;
}

function stepTypeLabel(type?: string) {
  if (!type) return "Inform";
  return type
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

export function SopReview({
  document,
  open,
  onOpenChange,
  onEdit,
  onToggleEnabled,
  onReprocess,
  togglingEnabled,
  reprocessing,
}: SopReviewProps) {
  if (!document) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="pr-8">{document.title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{document.category_name || "Uncategorized"}</Badge>
            <Badge variant={document.enabled ? "default" : "outline"}>
              {document.enabled ? "Enabled" : "Disabled"}
            </Badge>
            <StatusPill status={document.processing_status as ProcessingStatus} />
          </div>
          {document.summary && (
            <p className="leading-relaxed text-muted-foreground">{document.summary}</p>
          )}
          {document.tool_warnings && document.tool_warnings.length > 0 && (
            <div className="rounded-xl border border-amber-300/50 bg-amber-50 px-3 py-2 text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
              <p className="mb-1 font-medium">Tool warnings</p>
              <ul className="list-disc space-y-1 pl-4">
                {document.tool_warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          <Separator />
          <div className="space-y-4">
            <h3 className="font-semibold text-foreground">
              Processes ({document.processes?.length || 0})
            </h3>
            {(document.processes || []).map((process) => (
              <div key={process.id} className="rounded-xl border border-border bg-muted/30 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="font-medium text-foreground">{process.title}</h4>
                  <span className="font-mono text-xs text-muted-foreground">{process.process_key}</span>
                </div>
                <p className="mt-1 text-muted-foreground">{process.description}</p>
                {process.trigger_phrases?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {process.trigger_phrases.map((phrase) => (
                      <Badge key={phrase} variant="outline" className="font-normal">
                        {phrase}
                      </Badge>
                    ))}
                  </div>
                )}
                {process.tools?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {process.tools.map((tool) => (
                      <Badge key={tool} className="font-mono text-[11px]">
                        @{tool}
                      </Badge>
                    ))}
                  </div>
                )}
                <ol className="mt-3 list-decimal space-y-1 pl-5 text-foreground/90">
                  {(process.steps || []).map((step, index) => (
                    <li key={`${process.id}-${index}`}>
                      <span className="text-xs text-muted-foreground">
                        [{stepTypeLabel(step.type)}]
                      </span>{" "}
                      {step.instruction}
                      {step.tool ? (
                        <span className="font-mono text-xs text-primary"> @{step.tool}</span>
                      ) : null}
                    </li>
                  ))}
                </ol>
              </div>
            ))}
            {(document.processes || []).length === 0 && (
              <p className="text-muted-foreground">
                No processes extracted yet. Wait for processing or reprocess.
              </p>
            )}
          </div>
        </div>
        <DialogFooter className="flex-wrap gap-2">
          <Button variant="outline" onClick={onEdit}>
            Edit
          </Button>
          <Button
            variant="outline"
            onClick={() => onToggleEnabled(!document.enabled)}
            disabled={togglingEnabled}
          >
            {document.enabled ? "Disable" : "Enable"}
          </Button>
          <Button variant="secondary" onClick={onReprocess} disabled={reprocessing}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Reprocess
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
