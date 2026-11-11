"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  CircleOff,
  Hammer,
  MessageSquare,
  Power,
  PowerOff,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAgentRules } from "@/hooks/use-agent-rules";
import { useResources, useSetResourceActive } from "@/hooks/use-resources";
import { useSopDocuments } from "@/hooks/use-sops";
import { buttonMotion, fadeSlideUp, listItemVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { AgentRuleCategory } from "@/types/agent-rules";

interface CategoryMeta {
  key: AgentRuleCategory;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  accentClass: string;
}

const CATEGORIES: CategoryMeta[] = [
  {
    key: "business_context",
    label: "Business Context",
    description: "Core company facts and policies the agent should always keep in context.",
    icon: Building2,
    accentClass: "bg-sky-500/10 text-sky-700 dark:text-sky-300",
  },
  {
    key: "escalations",
    label: "Escalations",
    description: "Conditions and handoff rules for routing sensitive cases to humans quickly.",
    icon: AlertTriangle,
    accentClass: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  },
  {
    key: "response_tone_style",
    label: "Response Tone & Style",
    description: "Voice, clarity, and answer formatting standards used in every response.",
    icon: MessageSquare,
    accentClass: "bg-violet-500/10 text-violet-700 dark:text-violet-300",
  },
  {
    key: "agent_capabilities",
    label: "Agent Capabilities",
    description: "Boundaries for what the agent can do, cannot do, and must avoid.",
    icon: Zap,
    accentClass: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  },
];

export default function AgentOverviewPage() {
  const { data: rules = [], isLoading } = useAgentRules();
  const { data: sopDocuments = [] } = useSopDocuments();
  const { data: resources = [] } = useResources();
  const setActiveMutation = useSetResourceActive();

  const groupedRules = useMemo(() => {
    const grouped: Record<AgentRuleCategory, string[]> = {
      business_context: [],
      escalations: [],
      response_tone_style: [],
      agent_capabilities: [],
    };

    for (const rule of rules) {
      grouped[rule.category].push(rule.content);
    }

    return grouped;
  }, [rules]);

  const categoriesWithCount = CATEGORIES.map((category) => ({
    ...category,
    count: groupedRules[category.key].length,
  }));

  const populatedCount = categoriesWithCount.filter((category) => category.count > 0).length;
  const totalProcesses = sopDocuments.reduce((sum, document) => sum + document.process_count, 0);
  const activeTools = resources.filter((resource) => resource.active).length;

  return (
      <div className="w-full px-5 py-5">
        <div className="mb-5 overflow-hidden surface-card">
          <div className="flex flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
            <div className="max-w-2xl">
              <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-primary">
                Support copilot
              </p>
              <h2 className="mt-1 text-xl font-medium tracking-tight text-foreground">
                Ready to take the next ticket.
              </h2>
              <p className="page-description max-w-xl">
                Looks up accounts, follows SOPs, calls registered tools, and leaves an audit trail.
                Load your playbooks — same runtime for any support desk.
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <motion.div {...buttonMotion}>
                <Link href="/chat">
                  <Button>
                    Open Chat
                    <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Button>
                </Link>
              </motion.div>
              <motion.div {...buttonMotion}>
                <Link href="/agent-rules">
                  <Button variant="outline">
                    Manage rules
                  </Button>
                </Link>
              </motion.div>
            </div>
          </div>
        </div>

        <div className="mb-5 grid gap-3 md:grid-cols-3">
          <div className="surface-card p-4">
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Rule Groups Configured
            </p>
            <p className="mt-1.5 text-2xl font-medium tracking-tight text-foreground tabular-nums">
              {populatedCount}
              <span className="ml-1 text-sm font-medium text-muted-foreground">/ {CATEGORIES.length}</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Groups that currently have at least one rule.</p>
          </div>
          <div className="surface-card p-4">
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              SOPs / Processes
            </p>
            <p className="mt-1.5 text-2xl font-medium tracking-tight text-foreground tabular-nums">
              {sopDocuments.length}
              <span className="mx-1 text-sm font-medium text-muted-foreground">/</span>
              <span>{totalProcesses}</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">Total SOP documents and extracted processes.</p>
          </div>
          <div className="surface-card p-4">
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Tools
            </p>
            <p className="mt-1.5 text-2xl font-medium tracking-tight text-foreground tabular-nums">
              {activeTools}
              <span className="ml-1 text-sm font-medium text-muted-foreground">active</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {resources.length} total tool{resources.length === 1 ? "" : "s"} configured.
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div key={idx} className="surface-card h-64 animate-pulse bg-muted/30" />
            ))}
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {categoriesWithCount.map((category, index) => {
              const Icon = category.icon;
              const categoryRules = groupedRules[category.key];
              return (
                <motion.section
                  key={category.key}
                  custom={index}
                  variants={listItemVariants}
                  initial="hidden"
                  animate="visible"
                  whileHover={{ y: -2, transition: { duration: 0.2 } }}
                  className="surface-card group p-4"
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <div
                        className={cn(
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                          category.accentClass,
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-medium text-foreground">{category.label}</h3>
                        <p className="mt-0.5 text-xs text-muted-foreground">{category.description}</p>
                      </div>
                    </div>
                    <Badge variant="secondary">{category.count}</Badge>
                  </div>

                  {categoryRules.length === 0 ? (
                    <p className="rounded-lg border border-dashed border-border/70 bg-muted/20 px-3 py-5 text-center text-xs text-muted-foreground">
                      No rules in this group yet.
                    </p>
                  ) : (
                    <ul className="space-y-1.5">
                      {categoryRules.map((rule, ruleIndex) => (
                        <li
                          key={`${category.key}-${ruleIndex}`}
                          className="rounded-lg border border-border/70 bg-background/70 px-3 py-2 text-xs text-foreground transition-colors group-hover:border-border"
                        >
                          {rule}
                        </li>
                      ))}
                    </ul>
                  )}
                </motion.section>
              );
            })}
          </div>
        )}

        <motion.section
          className="mt-5 surface-card p-4"
          variants={fadeSlideUp}
          initial="hidden"
          animate="visible"
        >
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-foreground">Configured Tools</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Tools available for agent actions and SOP-linked execution.
              </p>
            </div>
            <motion.div {...buttonMotion}>
              <Link href="/resources">
                <Button variant="outline">
                  Open Tools
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </motion.div>
          </div>

          {resources.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border/70 bg-muted/20 px-3 py-5 text-center text-xs text-muted-foreground">
              No tools configured yet.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {resources.map((resource, index) => (
                <motion.div
                  key={resource.id}
                  custom={index}
                  variants={listItemVariants}
                  initial="hidden"
                  animate="visible"
                  whileHover={{ y: -1, transition: { duration: 0.18 } }}
                  className="rounded-lg border border-border/70 bg-background/70 p-3"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Hammer className="h-4 w-4 text-muted-foreground" />
                      <p className="truncate text-sm font-medium text-foreground">{resource.name}</p>
                    </div>
                    <motion.div {...buttonMotion}>
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
                  </div>
                  <div className="mb-2">
                    {resource.active ? (
                      <Badge variant="secondary" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Visible to Agent
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1">
                        <CircleOff className="h-3 w-3" />
                        Hidden from Agent
                      </Badge>
                    )}
                  </div>
                  <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {resource.description || "No description provided."}
                  </p>
                </motion.div>
              ))}
            </div>
          )}
        </motion.section>
      </div>
  );
}
