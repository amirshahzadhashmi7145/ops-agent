"use client";

import { motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";
import { Controller, useFieldArray, type Control } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { buttonMotion } from "@/lib/motion";
import type { ResourceFormValues } from "@/types/resource";

interface ParameterFieldsProps {
  control: Control<ResourceFormValues>;
}

export function ParameterFields({ control }: ParameterFieldsProps) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: "parameters",
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Parameters</Label>
        <motion.div {...buttonMotion}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              append({
                name: "",
                type: "string",
                required: false,
                description: "",
                default_value: "",
              })
            }
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add Parameter
          </Button>
        </motion.div>
      </div>

      <div className="space-y-2">
        {fields.map((field, index) => (
          <motion.div
            key={field.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid gap-2 rounded-xl border border-border bg-card p-3 md:grid-cols-[1fr_100px_1fr_1fr_auto]"
          >
            <Input
              placeholder="name"
              {...control.register(`parameters.${index}.name`)}
            />
            <Controller
              control={control}
              name={`parameters.${index}.type`}
              render={({ field: typeField }) => (
                <Select value={typeField.value} onValueChange={typeField.onChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="string">string</SelectItem>
                    <SelectItem value="number">number</SelectItem>
                    <SelectItem value="boolean">boolean</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Input
              placeholder="default value"
              {...control.register(`parameters.${index}.default_value`)}
            />
            <Input
              placeholder="description"
              {...control.register(`parameters.${index}.description`)}
            />
            <Button type="button" variant="ghost" size="icon" onClick={() => remove(index)}>
              <Trash2 className="h-4 w-4 text-muted-foreground" />
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
