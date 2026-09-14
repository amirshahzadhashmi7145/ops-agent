"use client";

import { motion } from "framer-motion";
import { Bot, Eye, MoreHorizontal, Pencil, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { StatusPill } from "@/components/kb/status-pill";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useCreateSopCategory,
  useCreateSopDocument,
  useDeleteSopDocument,
  useReprocessSopDocument,
  useSetSopEnabled,
  useSopCategories,
  useSopDocument,
  useSopDocuments,
  useUpdateSopDocument,
} from "@/hooks/use-sops";
import { fetchSopDocument } from "@/lib/api";
import { buttonMotion } from "@/lib/motion";
import type { ProcessingStatus } from "@/types/kb";
import type { SopDocument, SopDocumentListItem } from "@/types/sop";

const SopDialog = dynamic(
  () => import("@/components/sops/sop-dialog").then((m) => m.SopDialog),
  { loading: () => null },
);
const SopReview = dynamic(
  () => import("@/components/sops/sop-review").then((m) => m.SopReview),
  { loading: () => null },
);

const STATUS_LABELS: Record<string, string> = {
  all: "All statuses",
  ready: "Ready",
  queued: "Queued",
  formatting: "Processing",
  indexing: "Indexing",
  failed: "Failed",
};

export default function SopsPage() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [reviewOpen, setReviewOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState<SopDocument | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SopDocumentListItem | null>(null);
  const [reprocessingId, setReprocessingId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const { data: categories = [] } = useSopCategories();
  const filters = useMemo(() => {
    const next: { search?: string; category?: string; status?: string } = {};
    if (search.trim()) next.search = search.trim();
    if (categoryFilter !== "all") next.category = categoryFilter;
    if (statusFilter !== "all") next.status = statusFilter;
    return next;
  }, [search, categoryFilter, statusFilter]);

  const { data: documents = [], isLoading } = useSopDocuments(filters);
  const { data: selectedDocument } = useSopDocument(selectedId, { poll: reviewOpen });
  const createMutation = useCreateSopDocument();
  const createCategoryMutation = useCreateSopCategory();
  const updateMutation = useUpdateSopDocument(editing?.id ?? "");
  const deleteMutation = useDeleteSopDocument();
  const enableMutation = useSetSopEnabled();
  const reprocessMutation = useReprocessSopDocument();

  const selectedCategoryLabel = useMemo(() => {
    if (categoryFilter === "all") return "All categories";
    return categories.find((category) => category.slug === categoryFilter)?.name ?? "Category";
  }, [categories, categoryFilter]);

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = async (item: SopDocumentListItem) => {
    try {
      const document = await fetchSopDocument(item.id);
      setEditing(document);
      setDialogOpen(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load SOP");
    }
  };

  return (
    <>
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="page-header">SOPs</h2>
            <p className="page-description">
              Executable procedures the agent auto-matches and follows step by step.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <motion.div {...buttonMotion}>
              <Button variant="outline" onClick={() => setCategoryDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New category
              </Button>
            </motion.div>
            <motion.div {...buttonMotion}>
              <Button onClick={openCreate}>
                <Plus className="mr-2 h-4 w-4" />
                Add SOP
              </Button>
            </motion.div>
          </div>
        </div>

        <div className="mb-6 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search SOPs..."
              className="pl-9"
            />
          </div>
          <Select value={categoryFilter} onValueChange={(value) => value && setCategoryFilter(value)}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Category">{selectedCategoryLabel}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {categories.map((category) => (
                <SelectItem key={category.id} value={category.slug}>
                  {category.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={(value) => value && setStatusFilter(value)}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue placeholder="Status">
                {STATUS_LABELS[statusFilter] ?? "Status"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="ready">Ready</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="formatting">Processing</SelectItem>
              <SelectItem value="indexing">Indexing</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {isLoading ? (
          <div className="surface-card space-y-3 p-6">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-12 animate-pulse rounded-lg bg-muted/60" />
            ))}
          </div>
        ) : documents.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center"
          >
            <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
              <Bot className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">No SOPs yet</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Add your first SOP document. Use @tool mentions so each process binds to real tools.
            </p>
            <Button className="mt-6" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add SOP
            </Button>
          </motion.div>
        ) : (
          <div className="surface-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-6">Title</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Processes</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((document) => (
                  <TableRow key={document.id}>
                    <TableCell className="pl-6 font-medium">{document.title}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{document.category_name || "—"}</Badge>
                    </TableCell>
                    <TableCell>
                      <StatusPill status={document.processing_status as ProcessingStatus} />
                    </TableCell>
                    <TableCell>{document.process_count}</TableCell>
                    <TableCell>{document.enabled ? "Yes" : "No"}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted">
                          <MoreHorizontal className="h-4 w-4" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={() => {
                              setSelectedId(document.id);
                              setReviewOpen(true);
                            }}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            View
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => void openEdit(document)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={async () => {
                              setReprocessingId(document.id);
                              try {
                                await reprocessMutation.mutateAsync(document.id);
                              } finally {
                                setReprocessingId(null);
                              }
                            }}
                          >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            {reprocessingId === document.id ? "Reprocessing…" : "Reprocess"}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={() => setDeleteTarget(document)}
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
        )}
      </div>

      <SopDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        categories={categories}
        document={editing}
        loading={createMutation.isPending || updateMutation.isPending}
        onCreateCategory={async (name) => createCategoryMutation.mutateAsync({ name })}
        onSubmit={async (values) => {
          if (editing) {
            await updateMutation.mutateAsync(values);
          } else {
            await createMutation.mutateAsync(values);
          }
        }}
      />

      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New category</DialogTitle>
            <DialogDescription>Create a category for grouping SOP documents.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Input
              value={newCategoryName}
              onChange={(event) => setNewCategoryName(event.target.value)}
              placeholder="Billing"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void (async () => {
                    const name = newCategoryName.trim();
                    if (!name) {
                      toast.error("Category name is required");
                      return;
                    }
                    await createCategoryMutation.mutateAsync({ name });
                    setNewCategoryName("");
                    setCategoryDialogOpen(false);
                  })();
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={createCategoryMutation.isPending}
              onClick={async () => {
                const name = newCategoryName.trim();
                if (!name) {
                  toast.error("Category name is required");
                  return;
                }
                await createCategoryMutation.mutateAsync({ name });
                setNewCategoryName("");
                setCategoryDialogOpen(false);
              }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <SopReview
        document={selectedDocument ?? null}
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        onEdit={() => {
          if (selectedDocument) {
            setEditing(selectedDocument);
            setReviewOpen(false);
            setDialogOpen(true);
          }
        }}
        onToggleEnabled={async (enabled) => {
          if (!selectedDocument) return;
          setTogglingId(selectedDocument.id);
          try {
            await enableMutation.mutateAsync({ id: selectedDocument.id, enabled });
          } finally {
            setTogglingId(null);
          }
        }}
        onReprocess={async () => {
          if (!selectedDocument) return;
          setReprocessingId(selectedDocument.id);
          try {
            await reprocessMutation.mutateAsync(selectedDocument.id);
          } finally {
            setReprocessingId(null);
          }
        }}
        togglingEnabled={togglingId === selectedId}
        reprocessing={reprocessingId === selectedId}
      />

      <Dialog open={Boolean(deleteTarget)} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete SOP?</DialogTitle>
            <DialogDescription>
              This will remove <strong>{deleteTarget?.title}</strong> from searchable procedures.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (!deleteTarget) return;
                await deleteMutation.mutateAsync(deleteTarget.id);
                if (selectedId === deleteTarget.id) {
                  setReviewOpen(false);
                  setSelectedId(null);
                }
                setDeleteTarget(null);
              }}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
