"use client";

import { motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";
import { useFieldArray, type Control } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { buttonMotion } from "@/lib/motion";
import type { ResourceFormValues } from "@/types/resource";

interface HeaderFieldsProps {
  control: Control<ResourceFormValues>;
}

export function HeaderFields({ control }: HeaderFieldsProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: "fixed_headers",
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Fixed Headers</Label>
        <motion.div {...buttonMotion}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => append({ key: "", value: "", is_secret: false })}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add Header
          </Button>
        </motion.div>
      </div>

      <div className="space-y-2">
        {fields.map((field, index) => (
          <motion.div
            key={field.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid gap-2 rounded-xl border border-border bg-card p-3 md:grid-cols-[1fr_1fr_auto]"
          >
            <Input placeholder="Header name" {...control.register(`fixed_headers.${index}.key`)} />
            <Input placeholder="Header value" {...control.register(`fixed_headers.${index}.value`)} />
            <Button type="button" variant="ghost" size="icon" onClick={() => remove(index)}>
              <Trash2 className="h-4 w-4 text-muted-foreground" />
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
