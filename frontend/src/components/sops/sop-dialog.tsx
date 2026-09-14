"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { SopTextEditor } from "@/components/sops/sop-text-editor";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchResources } from "@/lib/api";
import type { ResourceListItem } from "@/types/resource";
import type { SopCategory, SopDocument, SopDocumentFormValues } from "@/types/sop";

interface SopDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  categories: SopCategory[];
  document?: SopDocument | null;
  onSubmit: (values: SopDocumentFormValues) => Promise<void>;
  onCreateCategory?: (name: string) => Promise<SopCategory>;
  loading?: boolean;
}

export function SopDialog({
  open,
  onOpenChange,
  categories,
  document,
  onSubmit,
  onCreateCategory,
  loading,
}: SopDialogProps) {
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [rawText, setRawText] = useState("");
  const [tools, setTools] = useState<ResourceListItem[]>([]);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [creatingCategory, setCreatingCategory] = useState(false);

  useEffect(() => {
    if (!open) return;
    setTitle(document?.title ?? "");
    setCategoryId(document?.category_id ?? categories[0]?.id ?? "");
    setRawText(document?.raw_text ?? "");
    void fetchResources()
      .then(setTools)
      .catch(() => toast.error("Failed to load tools for @mentions"));
  }, [open, document, categories]);

  const selectedCategoryName = useMemo(
    () => categories.find((category) => category.id === categoryId)?.name,
    [categories, categoryId],
  );

  const handleSubmit = async () => {
    if (!title.trim() || !categoryId || !rawText.trim()) {
      toast.error("Title, category, and SOP text are required");
      return;
    }
    await onSubmit({
      title: title.trim(),
      category_id: categoryId,
      raw_text: rawText,
    });
    onOpenChange(false);
  };

  const handleCreateCategory = async () => {
    if (!onCreateCategory) return;
    const name = newCategoryName.trim();
    if (!name) {
      toast.error("Category name is required");
      return;
    }
    setCreatingCategory(true);
    try {
      const category = await onCreateCategory(name);
      setCategoryId(category.id);
      setNewCategoryName("");
      setCategoryDialogOpen(false);
    } finally {
      setCreatingCategory(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{document ? "Edit SOP" : "Add SOP"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="sop-title">Title</Label>
              <Input
                id="sop-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Subscription Operations"
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <Label>Category</Label>
                {onCreateCategory ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => setCategoryDialogOpen(true)}
                  >
                    New category
                  </Button>
                ) : null}
              </div>
              <Select value={categoryId} onValueChange={(value) => value && setCategoryId(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select category">
                    {selectedCategoryName}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {categories.map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>SOP document</Label>
              <SopTextEditor
                value={rawText}
                onChange={setRawText}
                tools={tools}
                placeholder={
                  "Describe each process as clear steps. Mention tools with @tool_name, e.g.\n\n## Cancel subscription\n1. Ask for the customer email\n2. Call @lookup_customer_by_email\n3. List subscriptions with @list_subscriptions\n4. Confirm and call @cancel_subscription"
                }
              />
            </div>
            <div className="rounded-xl border border-border/70 bg-muted/30 px-3 py-3 text-xs leading-relaxed text-muted-foreground">
              <p className="mb-1.5 font-medium text-foreground">Writing tips</p>
              <ul className="list-disc space-y-1 pl-4">
                <li>
                  Separate processes with a heading (e.g. <span className="font-mono">## Cancel subscription</span>).
                </li>
                <li>Number the steps for each process in order.</li>
                <li>
                  Mention tools with <span className="font-mono">@tool_name</span> — pick from the @ menu when possible.
                </li>
                <li>
                  A perfect template helps, but free-form text is fine: the importer still tries to recover processes,
                  steps, and tool names.
                </li>
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => void handleSubmit()} disabled={loading}>
              {document ? "Save" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New category</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="new-sop-category">Name</Label>
            <Input
              id="new-sop-category"
              value={newCategoryName}
              onChange={(event) => setNewCategoryName(event.target.value)}
              placeholder="Billing"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void handleCreateCategory();
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void handleCreateCategory()} disabled={creatingCategory}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
