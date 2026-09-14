"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { KbReference, ReferenceFormValues } from "@/types/kb";

const schema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  raw_text: z.string().min(1, "Content is required"),
  source_url: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface ReferenceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reference?: KbReference | null;
  onSubmit: (values: ReferenceFormValues) => Promise<void>;
  loading?: boolean;
}

export function ReferenceDialog({
  open,
  onOpenChange,
  reference,
  onSubmit,
  loading,
}: ReferenceDialogProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      raw_text: "",
      source_url: "",
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        title: reference?.title ?? "",
        raw_text: reference?.raw_text ?? "",
        source_url: reference?.source_url ?? "",
      });
    }
  }, [open, reference, form]);

  const handleSubmit = form.handleSubmit(async (values) => {
    await onSubmit({
      title: values.title.trim(),
      raw_text: values.raw_text,
      source_url: values.source_url?.trim() || undefined,
    });
    onOpenChange(false);
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{reference ? "Edit reference" : "Add reference"}</DialogTitle>
          <DialogDescription>
            Paste policy or FAQ text — we&apos;ll structure it without changing facts.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input id="title" {...form.register("title")} placeholder="Return policy" />
            {form.formState.errors.title && (
              <p className="text-sm text-destructive">{form.formState.errors.title.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="raw_text">Content</Label>
            <Textarea
              id="raw_text"
              {...form.register("raw_text")}
              rows={14}
              placeholder="Paste the full reference text here..."
              className="max-h-80 min-h-48 resize-y overflow-y-auto text-sm"
            />
            {form.formState.errors.raw_text && (
              <p className="text-sm text-destructive">{form.formState.errors.raw_text.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="source_url">Source URL (optional)</Label>
            <Input
              id="source_url"
              {...form.register("source_url")}
              placeholder="https://..."
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving..." : reference ? "Save changes" : "Add reference"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
