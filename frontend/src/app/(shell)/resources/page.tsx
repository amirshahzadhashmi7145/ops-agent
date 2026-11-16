"use client";

import { motion } from "framer-motion";
import { Activity, MoreHorizontal, Pencil, Play, Plus, Power, PowerOff, Trash2, Wrench } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { LocalTime } from "@/components/local-time";
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
import { useToolLogSummary } from "@/hooks/use-tool-logs";
import { fetchResource } from "@/lib/api";
import { buttonMotion, listItemVariants } from "@/lib/motion";
import { buildTestPayload } from "@/lib/test-query";
import { isAliasTool } from "@/lib/tool-aliases";
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
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: resources = [], isLoading } = useResources();
  const { data: usageSummary = [] } = useToolLogSummary();
  const usageByName = Object.fromEntries(usageSummary.map((item) => [item.tool_name, item.call_count]));
  const deleteMutation = useDeleteResource();
  const setActiveMutation = useSetResourceActive();
  const testMutation = useTestResource();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Resource | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ResourceListItem | null>(null);
  const [quickTestTarget, setQuickTestTarget] = useState<ResourceListItem | null>(null);
  const [quickTestResult, setQuickTestResult] = useState<ResourceTestResult | null>(null);
  const [hideAliases, setHideAliases] = useState(true);

  const sortedResources = useMemo(() => {
    return [...resources].sort((a, b) => a.name.localeCompare(b.name));
  }, [resources]);

  const visibleResources = useMemo(() => {
    if (!hideAliases) return sortedResources;
    return sortedResources.filter((resource) => !isAliasTool(resource.name, resource.is_alias));
  }, [hideAliases, sortedResources]);

  const aliasCount = sortedResources.filter((resource) =>
    isAliasTool(resource.name, resource.is_alias),
  ).length;

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
      toast.error(error instanceof Error ? error.message : "Failed to load tool");
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
      <div className="w-full px-5 py-5">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="page-header">Tools</h2>
            <p className="page-description">
              APIs the assistant can call while running a workflow (lookup, refund, reset, and more).
            </p>
            {!isLoading && resources.length > 0 ? (
              <p className="mt-1.5 text-xs text-muted-foreground">
                Showing {visibleResources.length} of {resources.length}
                {aliasCount > 0 ? ` · ${aliasCount} alias${aliasCount === 1 ? "" : "es"}` : ""}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {aliasCount > 0 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setHideAliases((value) => !value)}
              >
                {hideAliases ? "Show aliases" : "Hide aliases"}
              </Button>
            ) : null}
            <motion.div {...buttonMotion}>
              <Button onClick={openCreate}>
                <Plus className="mr-2 h-4 w-4" />
                Add tool
              </Button>
            </motion.div>
          </div>
        </div>

        {isLoading ? (
          <div className="surface-card p-10 text-center text-sm text-muted-foreground">
            Loading tools...
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
            <h3 className="text-sm font-medium text-foreground">No tools yet</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Add your first tool so the assistant can call internal or external APIs.
            </p>
            <Button className="mt-6" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add tool
            </Button>
          </motion.div>
        ) : (
          <div className="surface-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-border/60 hover:bg-transparent">
                  <TableHead className="w-14 pl-5 text-muted-foreground">#</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="w-20 text-right">Calls</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Last test</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleResources.map((resource, index) => {
                  const alias = isAliasTool(resource.name, resource.is_alias);
                  const calls = usageByName[resource.name] ?? 0;
                  return (
                    <TableRow
                      key={resource.id}
                      className="transition-colors hover:bg-muted/50"
                    >
                      <TableCell className="pl-5 tabular-nums text-muted-foreground">
                        {index + 1}
                      </TableCell>
                      <TableCell className="font-medium text-foreground">
                        <motion.span
                          custom={index}
                          variants={listItemVariants}
                          initial="hidden"
                          animate="visible"
                          className="flex flex-wrap items-center gap-2"
                        >
                          <Link
                            href={`/resources/${resource.id}/logs`}
                            className="hover:text-primary"
                          >
                            {resource.name}
                          </Link>
                          <Badge
                            variant={resource.tool_scope === "internal" ? "default" : "secondary"}
                            className="text-[10px]"
                          >
                            {resource.tool_scope === "internal" ? "Internal" : "External"}
                          </Badge>
                          {alias ? (
                            <Badge variant="outline" className="text-[10px]">
                              Alias
                            </Badge>
                          ) : null}
                        </motion.span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {calls}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="font-mono text-xs">
                          {resource.http_method}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-muted-foreground">
                        {resource.url}
                      </TableCell>
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
                          <LocalTime
                            value={resource.last_tested_at}
                            className="text-xs text-muted-foreground"
                          />
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
                            <DropdownMenuItem onClick={() => router.push(`/resources/${resource.id}/logs`)}>
                              <Activity className="mr-2 h-4 w-4" />
                              Usage logs
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
                  );
                })}
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
            <DialogTitle>Delete tool?</DialogTitle>
            <DialogDescription>
              This will remove <strong>{deleteTarget?.name}</strong> from Tools.
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
