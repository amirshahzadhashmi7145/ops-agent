"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

interface RuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "add" | "edit";
  categoryLabel: string;
  initialContent?: string;
  loading?: boolean;
  onSubmit: (content: string) => Promise<void> | void;
}

export function RuleDialog({
  open,
  onOpenChange,
  mode,
  categoryLabel,
  initialContent = "",
  loading,
  onSubmit,
}: RuleDialogProps) {
  const [value, setValue] = useState(initialContent);
  const [wasOpen, setWasOpen] = useState(open);

  // Reset the field when the dialog transitions to open for a new rule/category.
  // Adjusting state during render (not in an effect) avoids a cascading re-render.
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) setValue(initialContent);
  }

  const trimmed = value.trim();

  const handleSubmit = async () => {
    if (!trimmed || loading) return;
    await onSubmit(trimmed);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "add" ? "Add rule" : "Edit rule"}</DialogTitle>
          <DialogDescription>
            {categoryLabel} — this rule is added to the agent&apos;s system prompt on every message.
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Write one clear instruction, e.g. 'Always confirm the device serial before checking status.'"
          className="min-h-32 resize-none"
          autoFocus
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              void handleSubmit();
            }
          }}
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={() => void handleSubmit()} disabled={!trimmed || loading}>
            {mode === "add" ? "Add rule" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
