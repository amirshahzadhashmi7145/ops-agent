"use client";

import { motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { buttonMotion } from "@/lib/motion";
import type { TestParamValue } from "@/lib/test-query";
import type { HeaderField, ParameterField } from "@/types/resource";

interface TestQueryFieldsProps {
  parameters: ParameterField[];
  fixedHeaders: HeaderField[];
  paramValues: TestParamValue[];
  onParamValuesChange: (values: TestParamValue[]) => void;
  testHeaders: HeaderField[];
  onTestHeadersChange: (headers: HeaderField[]) => void;
}

export function TestQueryFields({
  parameters,
  fixedHeaders,
  paramValues,
  onParamValuesChange,
  testHeaders,
  onTestHeadersChange,
}: TestQueryFieldsProps) {
  const savedParameters = parameters.filter((p) => p.name.trim());
  const savedHeaders = fixedHeaders.filter((h) => h.key.trim());

  return (
    <div className="space-y-4 rounded-xl border border-border/60 bg-muted/30 p-4">
      <p className="text-xs text-muted-foreground">
        Test uses the parameters and fixed headers saved above. Add items below only to override
        values for this test run.
      </p>

      <div className="space-y-3">
        <Label>Test parameters</Label>
        {paramValues.length === 0 && (
          <p className="text-xs text-muted-foreground">
            {savedParameters.length === 0
              ? "No saved parameters. Add a test parameter override below if needed."
              : "No overrides. Saved parameter values above will be used."}
          </p>
        )}
        {paramValues.length > 0 && (
          <div className="space-y-2">
            {paramValues.map((param, index) => (
              <div
                key={`test-param-${index}`}
                className="grid gap-2 rounded-lg border border-dashed border-border bg-card p-3 md:grid-cols-[1fr_1fr_auto]"
              >
                <Input
                  placeholder="name"
                  value={param.name}
                  onChange={(e) => {
                    const next = [...paramValues];
                    next[index] = { ...next[index], name: e.target.value };
                    onParamValuesChange(next);
                  }}
                />
                <Input
                  placeholder="override value"
                  value={param.value}
                  onChange={(e) => {
                    const next = [...paramValues];
                    next[index] = { ...next[index], value: e.target.value };
                    onParamValuesChange(next);
                  }}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => onParamValuesChange(paramValues.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </div>
            ))}
          </div>
        )}
        <motion.div {...buttonMotion}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onParamValuesChange([...paramValues, { name: "", value: "" }])}
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add test parameter
          </Button>
        </motion.div>
      </div>

      <div className="space-y-3">
        <Label>Test headers</Label>
        {testHeaders.length === 0 && (
          <p className="text-xs text-muted-foreground">
            {savedHeaders.length === 0
              ? "No saved headers. Add a test header override below if needed."
              : "No overrides. Saved fixed headers above will be used."}
          </p>
        )}
        {testHeaders.length > 0 && (
          <div className="space-y-2">
            {testHeaders.map((header, index) => (
              <motion.div
                key={`test-header-${index}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid gap-2 rounded-lg border border-border bg-card p-3 md:grid-cols-[1fr_1fr_auto]"
              >
                <Input
                  placeholder="Header name"
                  value={header.key}
                  onChange={(e) => {
                    const next = [...testHeaders];
                    next[index] = { ...next[index], key: e.target.value };
                    onTestHeadersChange(next);
                  }}
                />
                <Input
                  placeholder="override value"
                  value={header.value}
                  onChange={(e) => {
                    const next = [...testHeaders];
                    next[index] = { ...next[index], value: e.target.value };
                    onTestHeadersChange(next);
                  }}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => onTestHeadersChange(testHeaders.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </motion.div>
            ))}
          </div>
        )}
        <motion.div {...buttonMotion}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() =>
              onTestHeadersChange([...testHeaders, { key: "", value: "", is_secret: false }])
            }
          >
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Add test header
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
