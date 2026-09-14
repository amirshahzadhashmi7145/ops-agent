"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  Building2,
  Info,
  MessageSquare,
  Pencil,
  Plus,
  Trash2,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";

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
  useAgentRules,
  useCreateAgentRule,
  useDeleteAgentRule,
  useUpdateAgentRule,
} from "@/hooks/use-agent-rules";
import { buttonMotion } from "@/lib/motion";
import type { AgentRule, AgentRuleCategory } from "@/types/agent-rules";

const RuleDialog = dynamic(
  () => import("@/components/agent-rules/rule-dialog").then((m) => m.RuleDialog),
  { loading: () => null },
);

interface CategoryMeta {
  key: AgentRuleCategory;
  label: string;
  description: string;
  icon: LucideIcon;
}

const CATEGORIES: CategoryMeta[] = [
  {
    key: "business_context",
    label: "Business Context",
    description: "Facts about the business the agent should always know.",
    icon: Building2,
  },
  {
    key: "escalations",
    label: "Escalations",
    description: "When and how the agent should escalate to a human.",
    icon: AlertTriangle,
  },
  {
    key: "response_tone_style",
    label: "Response Tone & Style",
    description: "How the agent should sound and format its replies.",
    icon: MessageSquare,
  },
  {
    key: "agent_capabilities",
    label: "Agent Capabilities",
    description: "What the agent can and cannot do.",
    icon: Zap,
  },
];

type DialogState =
  | { mode: "add"; category: CategoryMeta }
  | { mode: "edit"; category: CategoryMeta; rule: AgentRule }
  | null;

export default function AgentRulesPage() {
  const { data: rules = [], isLoading } = useAgentRules();
  const createMutation = useCreateAgentRule();
  const updateMutation = useUpdateAgentRule();
  const deleteMutation = useDeleteAgentRule();

  const [dialog, setDialog] = useState<DialogState>(null);
  const [deleteTarget, setDeleteTarget] = useState<AgentRule | null>(null);

  const rulesByCategory = useMemo(() => {
    const grouped: Record<AgentRuleCategory, AgentRule[]> = {
      business_context: [],
      escalations: [],
      response_tone_style: [],
      agent_capabilities: [],
    };
    for (const rule of rules) {
      if (grouped[rule.category]) grouped[rule.category].push(rule);
    }
    return grouped;
  }, [rules]);

  const totalRules = rules.length;

  const handleSubmit = async (content: string) => {
    if (!dialog) return;
    if (dialog.mode === "add") {
      await createMutation.mutateAsync({ category: dialog.category.key, content });
    } else {
      await updateMutation.mutateAsync({ id: dialog.rule.id, payload: { content } });
    }
    setDialog(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  return (
    <>
      <div className="mx-auto max-w-6xl px-8 py-10">
        <div className="mb-6">
          <h2 className="page-header">Agent Rules</h2>
          <p className="page-description">
            Define rules the agent always follows. Every rule below is added to the agent&apos;s
            system prompt on each message.
          </p>
        </div>

        <div className="mb-8 flex items-start gap-3 rounded-xl border border-border/70 bg-muted/40 px-4 py-3">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <p className="text-sm text-muted-foreground">
            {totalRules === 0
              ? "No rules yet. Rules you add here are grouped by category and sent to the agent with every request."
              : `${totalRules} rule${totalRules === 1 ? "" : "s"} are sent to the agent with every request, grouped by category.`}
          </p>
        </div>

        <div className="space-y-6">
          {CATEGORIES.map((category) => {
            const Icon = category.icon;
            const categoryRules = rulesByCategory[category.key];
            return (
              <motion.section
                key={category.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="surface-card p-6"
              >
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-foreground">
                        {category.label}
                        <span className="ml-2 text-xs font-normal text-muted-foreground">
                          {categoryRules.length}
                        </span>
                      </h3>
                      <p className="mt-0.5 text-sm text-muted-foreground">{category.description}</p>
                    </div>
                  </div>
                  <motion.div {...buttonMotion}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setDialog({ mode: "add", category })}
                    >
                      <Plus className="mr-1.5 h-4 w-4" />
                      Add
                    </Button>
                  </motion.div>
                </div>

                {isLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 2 }).map((_, index) => (
                      <div key={index} className="h-10 animate-pulse rounded-lg bg-muted/60" />
                    ))}
                  </div>
                ) : categoryRules.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-border/70 px-4 py-5 text-center text-sm text-muted-foreground">
                    No rules in this category yet.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {categoryRules.map((rule) => (
                      <li
                        key={rule.id}
                        className="group flex items-start gap-3 rounded-lg border border-border/70 bg-background/60 px-4 py-3"
                      >
                        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/50" />
                        <p className="min-w-0 flex-1 whitespace-pre-wrap break-words text-sm text-foreground">
                          {rule.content}
                        </p>
                        <div className="flex shrink-0 gap-1 opacity-60 transition-opacity group-hover:opacity-100">
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8"
                            title="Edit rule"
                            aria-label="Edit rule"
                            onClick={() => setDialog({ mode: "edit", category, rule })}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            title="Delete rule"
                            aria-label="Delete rule"
                            onClick={() => setDeleteTarget(rule)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </motion.section>
            );
          })}
        </div>
      </div>

      <RuleDialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!open) setDialog(null);
        }}
        mode={dialog?.mode ?? "add"}
        categoryLabel={dialog?.category.label ?? ""}
        initialContent={dialog?.mode === "edit" ? dialog.rule.content : ""}
        loading={createMutation.isPending || updateMutation.isPending}
        onSubmit={handleSubmit}
      />

      <Dialog open={Boolean(deleteTarget)} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete rule?</DialogTitle>
            <DialogDescription>
              This rule will no longer be sent to the agent. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteTarget && (
            <p className="rounded-lg border border-border/70 bg-muted/40 px-4 py-3 text-sm text-foreground">
              {deleteTarget.content}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleDelete()}
              disabled={deleteMutation.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
