"use client";

import { motion } from "framer-motion";
import { BookOpen, Plus, Search } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { ReferenceList } from "@/components/kb/reference-list";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateReference,
  useDeleteReference,
  useReference,
  useReferences,
  useReprocessReference,
  useSetReferenceEnabled,
  useUpdateReference,
} from "@/hooks/use-kb";
import { fetchReference } from "@/lib/api";
import { buttonMotion } from "@/lib/motion";
import type { KbReference, KbReferenceListItem, StatusFilter } from "@/types/kb";

const ReferenceDialog = dynamic(
  () => import("@/components/kb/reference-dialog").then((m) => m.ReferenceDialog),
  { loading: () => null },
);
const ReferenceReview = dynamic(
  () => import("@/components/kb/reference-review").then((m) => m.ReferenceReview),
  { loading: () => null },
);

const STATUS_FILTER_LABELS: Record<StatusFilter, string> = {
  all: "All",
  ready: "Ready",
  queued: "Queued",
  formatting: "Processing",
  indexing: "Indexing",
  failed: "Failed",
  disabled: "Disabled",
};

export default function KbPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<KbReferenceListItem | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingReference, setEditingReference] = useState<KbReference | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);

  const apiFilters = useMemo(() => {
    const filters: { search?: string; status?: string; enabled?: boolean } = {};
    if (search.trim()) filters.search = search.trim();
    if (statusFilter === "disabled") {
      filters.enabled = false;
    } else if (statusFilter !== "all") {
      filters.status = statusFilter;
    }
    return filters;
  }, [search, statusFilter]);

  const { data: references = [], isLoading } = useReferences(apiFilters);
  const { data: selectedReference } = useReference(selectedId, { poll: reviewOpen });
  const createMutation = useCreateReference();
  const deleteMutation = useDeleteReference();
  const enableMutation = useSetReferenceEnabled();
  const reprocessMutation = useReprocessReference();
  const updateMutation = useUpdateReference(editingReference?.id ?? "");

  const openCreate = () => {
    setEditingReference(null);
    setDialogOpen(true);
  };

  const openEdit = async (item: KbReferenceListItem) => {
    try {
      const reference = await fetchReference(item.id);
      setEditingReference(reference);
      setDialogOpen(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load reference");
    }
  };

  const openView = (item: KbReferenceListItem) => {
    setSelectedId(item.id);
    setReviewOpen(true);
  };

  const handleCreateOrUpdate = async (values: {
    title: string;
    raw_text: string;
    source_url?: string;
  }) => {
    if (editingReference) {
      const updated = await updateMutation.mutateAsync(values);
      if (updated.processing_status !== "ready") {
        toast.info("Reference updated and queued for processing");
      }
      return;
    }

    const created = await createMutation.mutateAsync(values);
    setSelectedId(created.id);
  };

  const handleToggleEnabled = async (item: KbReferenceListItem, enabled: boolean) => {
    setTogglingId(item.id);
    try {
      await enableMutation.mutateAsync({ id: item.id, enabled });
    } finally {
      setTogglingId(null);
    }
  };

  const handleReprocess = async (item: KbReferenceListItem) => {
    setReprocessingId(item.id);
    try {
      await reprocessMutation.mutateAsync(item.id);
    } finally {
      setReprocessingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    if (selectedId === deleteTarget.id) {
      setReviewOpen(false);
      setSelectedId(null);
    }
    setDeleteTarget(null);
  };

  return (
    <>
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="page-header">Knowledge Base</h2>
            <p className="page-description">
              Manage references the agent can search for policies, FAQs, and product docs.
            </p>
          </div>
          <motion.div {...buttonMotion}>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add reference
            </Button>
          </motion.div>
        </div>

        <div className="mb-6 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search references..."
              className="pl-9"
            />
          </div>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as StatusFilter)}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Filter status">{STATUS_FILTER_LABELS[statusFilter]}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="ready">Ready</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="formatting">Processing</SelectItem>
              <SelectItem value="indexing">Indexing</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="disabled">Disabled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="surface-card space-y-3 p-6">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-12 animate-pulse rounded-lg bg-muted/60" />
            ))}
          </div>
        ) : references.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center"
          >
            <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
              <BookOpen className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">No references yet</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Add your first reference so the agent can answer policy and product questions.
            </p>
            <Button className="mt-6" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add reference
            </Button>
          </motion.div>
        ) : (
          <ReferenceList
            references={references}
            onView={openView}
            onEdit={(item) => {
              void openEdit(item);
            }}
            onDelete={setDeleteTarget}
            onReprocess={(item) => {
              void handleReprocess(item);
            }}
            onToggleEnabled={(item, enabled) => {
              void handleToggleEnabled(item, enabled);
            }}
            togglingId={togglingId}
            reprocessingId={reprocessingId}
          />
        )}
      </div>

      <ReferenceDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        reference={editingReference}
        onSubmit={handleCreateOrUpdate}
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <ReferenceReview
        reference={selectedReference ?? null}
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        onEdit={() => {
          if (selectedReference) {
            setEditingReference(selectedReference);
            setReviewOpen(false);
            setDialogOpen(true);
          }
        }}
        onToggleEnabled={(enabled) => {
          if (selectedReference) {
            void handleToggleEnabled(selectedReference, enabled);
          }
        }}
        onReprocess={() => {
          if (selectedReference) {
            void handleReprocess(selectedReference);
          }
        }}
        togglingEnabled={togglingId === selectedId}
        reprocessing={reprocessingId === selectedId}
      />

      <Dialog open={Boolean(deleteTarget)} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete reference?</DialogTitle>
            <DialogDescription>
              This will remove <strong>{deleteTarget?.title}</strong> from the knowledge base.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
