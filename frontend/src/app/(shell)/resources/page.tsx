"use client";

import { motion } from "framer-motion";
import { MoreHorizontal, Pencil, Play, Plus, Power, PowerOff, Trash2, Wrench } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { TestResultPanel } from "@/components/resources/test-result-panel";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useDeleteResource,
  useResources,
  useSetResourceActive,
  useTestResource,
} from "@/hooks/use-resources";
import { fetchResource } from "@/lib/api";
import { buttonMotion, listItemVariants } from "@/lib/motion";
import { buildTestPayload } from "@/lib/test-query";
import type { Resource, ResourceFormValues, ResourceListItem, ResourceTestResult } from "@/types/resource";

const RestQueryDialog = dynamic(
  () => import("@/components/resources/rest-query-dialog").then((m) => m.RestQueryDialog),
  { loading: () => null },
);

function StatusDot({ success }: { success: boolean | null }) {
  if (success === null) return <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/30" />;
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${
        success ? "bg-emerald-500" : "bg-red-400"
      }`}
    />
  );
}

export default function ResourcesPage() {
  const queryClient = useQueryClient();
  const { data: resources = [], isLoading } = useResources();
  const deleteMutation = useDeleteResource();
  const setActiveMutation = useSetResourceActive();
  const testMutation = useTestResource();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Resource | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ResourceListItem | null>(null);
  const [quickTestTarget, setQuickTestTarget] = useState<ResourceListItem | null>(null);
  const [quickTestResult, setQuickTestResult] = useState<ResourceTestResult | null>(null);

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = async (item: ResourceListItem) => {
    try {
      const resource = await queryClient.fetchQuery({
        queryKey: ["resources", item.id],
        queryFn: () => fetchResource(item.id),
      });
      setEditing(resource);
      setDialogOpen(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load resource");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  const handleQuickTest = async (item: ResourceListItem) => {
    setQuickTestTarget(item);
    setQuickTestResult(null);

    try {
      const resource = await queryClient.fetchQuery({
        queryKey: ["resources", item.id],
        queryFn: () => fetchResource(item.id),
      });
      const result = await testMutation.mutateAsync({
        resource_id: item.id,
        name: resource.name,
        description: resource.description,
        tool_scope: resource.tool_scope ?? "external",
        connection_mode: resource.connection_mode,
        connection_id: resource.connection_id,
        http_method: resource.http_method as ResourceFormValues["http_method"],
        url: resource.url,
        parameters: resource.parameters,
        fixed_headers: resource.fixed_headers,
        test_payload: buildTestPayload(resource.parameters, []),
      });
      setQuickTestResult(result);
      if (result.success) {
        toast.success(`Test passed for ${item.name}`);
      } else {
        toast.error(result.error || `Test failed for ${item.name}`);
      }
    } catch {
      setQuickTestTarget(null);
      setQuickTestResult(null);
    }
  };

  return (
    <>
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="page-header">Tools & Resources</h2>
            <p className="page-description">
              Register REST queries the agent can call during SOP execution.
            </p>
          </div>
          <motion.div {...buttonMotion}>
            <Button onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add REST Query
            </Button>
          </motion.div>
        </div>

        {isLoading ? (
          <div className="surface-card p-10 text-center text-sm text-muted-foreground">
            Loading resources...
          </div>
        ) : resources.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center"
          >
            <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
              <Wrench className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">No REST queries yet</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Add your first tool so the agent can call internal or external APIs.
            </p>
            <Button className="mt-6" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add REST Query
            </Button>
          </motion.div>
        ) : (
          <div className="surface-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-border/60 hover:bg-transparent">
                  <TableHead className="pl-6">Name</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Agent Access</TableHead>
                  <TableHead>Last test</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {resources.map((resource, index) => (
                  <TableRow
                    key={resource.id}
                    className="transition-colors hover:bg-muted/50"
                  >
                    <TableCell className="pl-6 font-medium text-foreground">
                      <motion.span
                        custom={index}
                        variants={listItemVariants}
                        initial="hidden"
                        animate="visible"
                        className="flex items-center gap-2"
                      >
                        <span>{resource.name}</span>
                        <Badge
                          variant={resource.tool_scope === "internal" ? "default" : "secondary"}
                          className="text-[10px]"
                        >
                          {resource.tool_scope === "internal" ? "Internal" : "External"}
                        </Badge>
                      </motion.span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-mono text-xs">
                        {resource.http_method}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">{resource.url}</TableCell>
                    <TableCell>
                      <motion.div {...buttonMotion} className="w-fit">
                        <Button
                          variant={resource.active ? "secondary" : "outline"}
                          size="sm"
                          disabled={setActiveMutation.isPending}
                          onClick={() =>
                            setActiveMutation.mutate({
                              id: resource.id,
                              active: !resource.active,
                            })
                          }
                        >
                          {resource.active ? (
                            <>
                              <Power className="mr-1.5 h-3.5 w-3.5" />
                              On
                            </>
                          ) : (
                            <>
                              <PowerOff className="mr-1.5 h-3.5 w-3.5" />
                              Off
                            </>
                          )}
                        </Button>
                      </motion.div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StatusDot success={resource.last_test_success} />
                        <span className="text-xs text-muted-foreground">
                          {resource.last_tested_at
                            ? new Date(resource.last_tested_at).toLocaleString()
                            : "Never"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          className="inline-flex h-9 w-9 items-center justify-center rounded-lg hover:bg-muted"
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(resource)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => {
                              void handleQuickTest(resource);
                            }}
                            disabled={testMutation.isPending && quickTestTarget?.id === resource.id}
                          >
                            <Play className="mr-2 h-4 w-4" />
                            {testMutation.isPending && quickTestTarget?.id === resource.id
                              ? "Testing..."
                              : "Test"}
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={() => setDeleteTarget(resource)}
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

      <RestQueryDialog open={dialogOpen} onOpenChange={setDialogOpen} resource={editing} />

      <Dialog
        open={Boolean(quickTestTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setQuickTestTarget(null);
            setQuickTestResult(null);
          }
        }}
      >
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Test result — {quickTestTarget?.name}</DialogTitle>
            <DialogDescription>
              Quick test using saved parameter defaults and fixed headers.
            </DialogDescription>
          </DialogHeader>
          <TestResultPanel
            result={quickTestResult}
            loading={testMutation.isPending}
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setQuickTestTarget(null);
                setQuickTestResult(null);
              }}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete REST query?</DialogTitle>
            <DialogDescription>
              This will remove <strong>{deleteTarget?.name}</strong> from the agent toolset.
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
