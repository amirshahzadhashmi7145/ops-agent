"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { HeaderFields } from "@/components/resources/header-fields";
import { ParameterFields } from "@/components/resources/parameter-fields";
import { TestQueryFields } from "@/components/resources/test-query-fields";
import { TestResultPanel } from "@/components/resources/test-result-panel";
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
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateResource,
  useTestResource,
  useUpdateResource,
} from "@/hooks/use-resources";
import { buttonMotion, modalVariants } from "@/lib/motion";
import {
  buildTestPayload,
  type TestParamValue,
} from "@/lib/test-query";
import type { HeaderField, Resource, ResourceFormValues, ResourceTestResult } from "@/types/resource";

const formSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required")
    .transform((v) => v.trim().replace(/\s+/g, "_"))
    .refine((v) => /^[a-zA-Z0-9_-]+$/.test(v), {
      message: "Only letters, numbers, underscores, and hyphens",
    }),
  description: z.string(),
  tool_scope: z.enum(["internal", "external"]),
  connection_mode: z.enum(["direct", "existing"]),
  connection_id: z.string().nullable(),
  http_method: z.enum(["GET", "POST", "PUT", "PATCH", "DELETE"]),
  url: z.string().min(1, "URL is required"),
  parameters: z.array(
    z.object({
      name: z.string(),
      type: z.enum(["string", "number", "boolean"]),
      required: z.boolean(),
      description: z.string(),
      default_value: z.string(),
    }),
  ),
  fixed_headers: z.array(
    z.object({
      key: z.string(),
      value: z.string(),
      is_secret: z.boolean().optional(),
    }),
  ),
});

const defaultValues: ResourceFormValues = {
  name: "",
  description: "",
  tool_scope: "external",
  connection_mode: "direct",
  connection_id: null,
  http_method: "GET",
  url: "",
  parameters: [],
  fixed_headers: [],
};

function normalizeParameters(
  parameters: ResourceFormValues["parameters"],
): ResourceFormValues["parameters"] {
  return parameters.map((param) => ({
    ...param,
    default_value: param.default_value ?? "",
  }));
}

interface RestQueryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  resource?: Resource | null;
}

export function RestQueryDialog({ open, onOpenChange, resource }: RestQueryDialogProps) {
  const isEdit = Boolean(resource);
  const createMutation = useCreateResource();
  const updateMutation = useUpdateResource(resource?.id ?? "");
  const testMutation = useTestResource(resource?.id);
  const [testResult, setTestResult] = useState<ResourceTestResult | null>(null);
  const [testPassed, setTestPassed] = useState(false);
  const [testParamValues, setTestParamValues] = useState<TestParamValue[]>([]);
  const [testHeaders, setTestHeaders] = useState<HeaderField[]>([]);

  const [internalBase, setInternalBase] = useState("http://backend:8000");

  const form = useForm<ResourceFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues,
  });

  useEffect(() => {
    if (!open) return;
    void fetch("/api/config")
      .then((res) => (res.ok ? res.json() : null))
      .then((data: { internal_api_base_url?: string } | null) => {
        if (data?.internal_api_base_url) setInternalBase(data.internal_api_base_url);
      })
      .catch(() => undefined);
    queueMicrotask(() => {
      setTestResult(null);
      setTestPassed(false);
      setTestParamValues([]);
      setTestHeaders([]);
    });
    if (resource) {
      form.reset({
        name: resource.name,
        description: resource.description,
        tool_scope: resource.tool_scope ?? "external",
        connection_mode: "direct",
        connection_id: null,
        http_method: resource.http_method as ResourceFormValues["http_method"],
        url: resource.url,
        parameters: normalizeParameters(resource.parameters),
        fixed_headers: resource.fixed_headers,
      });
    } else {
      form.reset(defaultValues);
    }
  }, [open, resource, form]);

  const parameters = useWatch({
    control: form.control,
    name: "parameters",
    defaultValue: [],
  });
  const fixedHeaders = useWatch({
    control: form.control,
    name: "fixed_headers",
    defaultValue: [],
  });
  const httpMethod = useWatch({
    control: form.control,
    name: "http_method",
    defaultValue: "GET",
  });
  const toolScope = useWatch({
    control: form.control,
    name: "tool_scope",
    defaultValue: "external",
  });
  const urlValue = useWatch({
    control: form.control,
    name: "url",
    defaultValue: "",
  });

  const handleTest = form.handleSubmit(async (values) => {
    const testHeaderOverrides = testHeaders.filter((h) => h.key.trim());
    const result = await testMutation.mutateAsync({
      ...values,
      connection_mode: "direct",
      connection_id: null,
      test_payload: buildTestPayload(values.parameters, testParamValues),
      test_headers: testHeaderOverrides.length > 0 ? testHeaderOverrides : undefined,
    });
    setTestResult(result);
    setTestPassed(result.success);
    if (result.success) {
      toast.success("Test passed");
    } else {
      toast.error(result.error || "Test failed");
    }
  });

  const handleSave = form.handleSubmit(async (values, event) => {
    const forceSave =
      (event?.nativeEvent as SubmitEvent | undefined)?.submitter?.getAttribute("data-force") ===
      "true";

    if (!testPassed && !forceSave) {
      toast.error("Run a successful test before creating");
      return;
    }

    const payload = {
      ...values,
      connection_mode: "direct" as const,
      connection_id: null,
      force_save: forceSave,
      last_test_success: testPassed,
    };

    if (isEdit) {
      await updateMutation.mutateAsync(payload);
    } else {
      await createMutation.mutateAsync(payload);
    }
    onOpenChange(false);
  });

  const saving = createMutation.isPending || updateMutation.isPending;
  const path = urlValue.startsWith("/") ? urlValue : `/${urlValue || ""}`;
  const resolvedPreview = toolScope === "internal" ? `${internalBase.replace(/\/$/, "")}${path}` : urlValue;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-x-hidden overflow-y-auto sm:max-w-2xl">
        <motion.div
          variants={modalVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className="min-w-0"
        >
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold">
              {isEdit ? "Edit REST Query" : "Create REST Query"}
            </DialogTitle>
          </DialogHeader>

          <form className="mt-6 min-w-0 space-y-5" onSubmit={(e) => e.preventDefault()}>
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" placeholder="get_order" {...form.register("name")} />
              <p className="text-xs text-muted-foreground">
                Only letters, numbers, underscores, and hyphens. Spaces will be converted to
                underscores.
              </p>
              {form.formState.errors.name && (
                <p className="text-xs text-red-500">{form.formState.errors.name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="When the agent should use this query..."
                className="max-h-40 min-h-20 resize-none overflow-y-auto"
                {...form.register("description")}
              />
            </div>

            <div className="space-y-2">
              <Label>Tool scope</Label>
              <Select
                value={toolScope}
                onValueChange={(value) => {
                  if (value === "internal" || value === "external") {
                    form.setValue("tool_scope", value);
                    if (value === "internal" && !form.getValues("url").startsWith("/")) {
                      form.setValue("url", "/api/sim/");
                    }
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue>
                    {toolScope === "internal" ? "Internal" : "External"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="external">External</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Internal tools store a path; the host comes from INTERNAL_API_BASE_URL.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-[180px_1fr]">
              <div className="space-y-2">
                <Label>HTTP Method</Label>
                <Select
                  value={httpMethod}
                  onValueChange={(value) => {
                    if (value) form.setValue("http_method", value);
                  }}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["GET", "POST", "PUT", "PATCH", "DELETE"].map((method) => (
                      <SelectItem key={method} value={method}>
                        {method}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="url">{toolScope === "internal" ? "Path" : "Complete URL"}</Label>
                <Input
                  id="url"
                  placeholder={
                    toolScope === "internal"
                      ? "/api/sim/subscriptions/{email}"
                      : "https://api.example.com/path/to/resource"
                  }
                  {...form.register("url")}
                />
                {toolScope === "internal" && (
                  <p className="truncate text-xs text-muted-foreground">
                    Resolves to <span className="font-mono">{resolvedPreview}</span>
                  </p>
                )}
              </div>
            </div>

            <ParameterFields control={form.control} />
            <HeaderFields control={form.control} />

            <Separator />

            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">Test Query</h3>
              <motion.div {...buttonMotion}>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTest}
                  disabled={testMutation.isPending}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Test
                </Button>
              </motion.div>
            </div>

            <TestQueryFields
              parameters={parameters}
              fixedHeaders={fixedHeaders}
              paramValues={testParamValues}
              onParamValuesChange={setTestParamValues}
              testHeaders={testHeaders}
              onTestHeadersChange={setTestHeaders}
            />

            <TestResultPanel result={testResult} loading={testMutation.isPending} />

            <DialogFooter className="gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              {!testPassed && (
                <Button
                  type="button"
                  variant="secondary"
                  data-force="true"
                  disabled={saving}
                  onClick={handleSave}
                >
                  Create anyway
                </Button>
              )}
              <motion.div {...buttonMotion}>
                <Button
                  type="button"
                  disabled={saving || !testPassed}
                  onClick={handleSave}
                >
                  {isEdit ? "Save" : "Create"}
                </Button>
              </motion.div>
            </DialogFooter>
          </form>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
}
