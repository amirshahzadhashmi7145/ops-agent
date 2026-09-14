"use client";

import { motion } from "framer-motion";
import { Eye, MoreHorizontal, Pencil, RefreshCw, Trash2 } from "lucide-react";

import { StatusPill } from "@/components/kb/status-pill";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listItemVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { KbReferenceListItem } from "@/types/kb";

interface ReferenceListProps {
  references: KbReferenceListItem[];
  onView: (item: KbReferenceListItem) => void;
  onEdit: (item: KbReferenceListItem) => void;
  onDelete: (item: KbReferenceListItem) => void;
  onReprocess: (item: KbReferenceListItem) => void;
  onToggleEnabled: (item: KbReferenceListItem, enabled: boolean) => void;
  togglingId?: string | null;
  reprocessingId?: string | null;
}

function EnableToggle({
  enabled,
  disabled,
  onChange,
}: {
  enabled: boolean;
  disabled?: boolean;
  onChange: (enabled: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={() => onChange(!enabled)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors",
        enabled ? "bg-primary" : "bg-muted",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span
        className={cn(
          "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-background shadow ring-0 transition",
          enabled ? "translate-x-5" : "translate-x-0",
        )}
      />
    </button>
  );
}

export function ReferenceList({
  references,
  onView,
  onEdit,
  onDelete,
  onReprocess,
  onToggleEnabled,
  togglingId,
  reprocessingId,
}: ReferenceListProps) {
  return (
    <div className="surface-card overflow-hidden">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow className="border-border/60 hover:bg-transparent">
            <TableHead className="w-[29%] pl-6">Title</TableHead>
            <TableHead className="w-[26%]">Summary</TableHead>
            <TableHead className="w-[15%]">Status</TableHead>
            <TableHead className="w-[12%]">Enabled</TableHead>
            <TableHead className="w-[14%]">Updated</TableHead>
            <TableHead className="w-14" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {references.map((reference, index) => (
            <TableRow
              key={reference.id}
              className={cn(
                "transition-colors hover:bg-muted/50",
                !reference.enabled && "opacity-60",
              )}
            >
              <TableCell className="pl-6 pr-3 font-medium text-foreground">
                <motion.div
                  custom={index}
                  variants={listItemVariants}
                  initial="hidden"
                  animate="visible"
                  className="flex items-center gap-2"
                >
                  <span className="truncate leading-tight">{reference.title}</span>
                  {!reference.enabled && (
                    <Badge variant="outline" className="text-xs">
                      Disabled
                    </Badge>
                  )}
                </motion.div>
              </TableCell>
              <TableCell className="truncate pr-3 text-sm text-muted-foreground">
                {reference.summary || "—"}
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1 pr-2">
                  <StatusPill status={reference.processing_status} />
                  {reference.processing_status === "failed" && reference.processing_error && (
                    <span className="truncate text-xs text-destructive">
                      {reference.processing_error}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <EnableToggle
                  enabled={reference.enabled}
                  disabled={
                    togglingId === reference.id ||
                    ["queued", "formatting", "indexing"].includes(reference.processing_status)
                  }
                  onChange={(enabled) => onToggleEnabled(reference, enabled)}
                />
              </TableCell>
              <TableCell className="truncate text-xs text-muted-foreground">
                {new Date(reference.updated_at).toLocaleDateString()} {new Date(reference.updated_at).toLocaleTimeString()}
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted">
                    <MoreHorizontal className="h-4 w-4" />
                    <span className="sr-only">Open menu</span>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onView(reference)}>
                      <Eye className="mr-2 h-4 w-4" />
                      View
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onEdit(reference)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    {reference.processing_status === "failed" && (
                      <DropdownMenuItem
                        onClick={() => onReprocess(reference)}
                        disabled={reprocessingId === reference.id}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        {reprocessingId === reference.id ? "Retrying..." : "Retry processing"}
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem
                      className="text-red-600"
                      onClick={() => onDelete(reference)}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
