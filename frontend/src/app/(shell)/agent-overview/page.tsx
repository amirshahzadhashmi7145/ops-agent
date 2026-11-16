"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  FileText,
  Library,
  MessageSquare,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { UsageOverviewCharts } from "@/components/home/usage-overview-charts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAgentRules } from "@/hooks/use-agent-rules";
import { useReferences } from "@/hooks/use-kb";
import { useResources } from "@/hooks/use-resources";
import { useSopDocuments } from "@/hooks/use-sops";
import { useUsageStats } from "@/hooks/use-usage";
import { buttonMotion, fadeSlideUp } from "@/lib/motion";
import { isAliasTool } from "@/lib/tool-aliases";
import type { AgentRuleCategory } from "@/types/agent-rules";

const RULE_CATEGORIES: AgentRuleCategory[] = [
  "business_context",
  "escalations",
  "response_tone_style",
  "agent_capabilities",
];

function formatUsd(value: number) {
  if (!Number.isFinite(value)) return "—";
  if (value > 0 && value < 0.01) return "<$0.01";
  return `$${value.toFixed(value >= 10 ? 2 : 3)}`;
}

export default function AgentOverviewPage() {
  const { data: rules = [], isLoading: rulesLoading } = useAgentRules();
  const { data: sopDocuments = [] } = useSopDocuments();
  const { data: resources = [] } = useResources();
  const { data: articles = [] } = useReferences();
  const { data: usage, isLoading: usageLoading } = useUsageStats(30);

  const populatedRuleGroups = useMemo(() => {
    const present = new Set(rules.map((rule) => rule.category));
    return RULE_CATEGORIES.filter((category) => present.has(category)).length;
  }, [rules]);

  const totalProcesses = sopDocuments.reduce((sum, document) => sum + document.process_count, 0);
  const canonicalTools = resources.filter((resource) => !isAliasTool(resource.name, resource.is_alias));
  const activeTools = canonicalTools.filter((resource) => resource.active).length;
  const readyArticles = articles.filter((article) => article.processing_status === "ready").length;

  const attention = useMemo(() => {
    const items: { label: string; href: string }[] = [];
    if (populatedRuleGroups < RULE_CATEGORIES.length) {
      items.push({
        label: `${RULE_CATEGORIES.length - populatedRuleGroups} rule group${
          RULE_CATEGORIES.length - populatedRuleGroups === 1 ? "" : "s"
        } empty`,
        href: "/agent-rules",
      });
    }
    if (sopDocuments.length === 0) {
      items.push({ label: "No workflows yet", href: "/sops" });
    }
    if (articles.length === 0) {
      items.push({ label: "No articles indexed", href: "/kb" });
    }
    if (canonicalTools.length > 0 && activeTools === 0) {
      items.push({ label: "All tools are off", href: "/resources" });
    }
    return items.slice(0, 4);
  }, [populatedRuleGroups, sopDocuments.length, articles.length, canonicalTools.length, activeTools]);

  return (
    <div className="w-full px-5 py-5">
      <div className="mb-5 overflow-hidden surface-card">
        <div className="flex flex-col gap-4 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl">
            <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-primary">
              Home
            </p>
            <h2 className="mt-1 text-xl font-medium tracking-tight text-foreground">
              Ready for the next ticket.
            </h2>
            <p className="page-description max-w-xl">
              Setup health, recent spend, and a short path into Chat — no config dump.
            </p>
          </div>
          <motion.div {...buttonMotion}>
            <Link href="/chat">
              <Button>
                Open Chat
                <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi
          label="Rules"
          value={`${populatedRuleGroups}/${RULE_CATEGORIES.length}`}
          hint="Groups with content"
          href="/agent-rules"
          icon={FileText}
          loading={rulesLoading}
        />
        <Kpi
          label="Workflows"
          value={String(sopDocuments.length)}
          hint={`${totalProcesses} step${totalProcesses === 1 ? "" : "s"}`}
          href="/sops"
          icon={BookOpen}
        />
        <Kpi
          label="Articles"
          value={String(readyArticles)}
          hint={`${articles.length} total`}
          href="/kb"
          icon={Library}
        />
        <Kpi
          label="Tools"
          value={String(activeTools)}
          hint={`${canonicalTools.length} in catalog`}
          href="/resources"
          icon={Wrench}
        />
        <Kpi
          label="Tickets (30d)"
          value={usage ? String(usage.tickets.conversations) : "—"}
          hint={
            usage?.tickets.observed
              ? `Avg ${formatUsd(usage.tickets.avg_cost_usd)}`
              : "After traffic"
          }
          href="/chat"
          icon={MessageSquare}
          loading={usageLoading}
        />
      </div>

      <motion.div variants={fadeSlideUp} initial="hidden" animate="visible" className="mb-5">
        {usageLoading && !usage ? (
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1.5fr)_minmax(220px,0.85fr)]">
            <div className="surface-card h-56 animate-pulse bg-muted/30" />
            <div className="surface-card h-56 animate-pulse bg-muted/30" />
          </div>
        ) : usage ? (
          <UsageOverviewCharts stats={usage} />
        ) : (
          <div className="surface-card p-6 text-center text-sm text-muted-foreground">
            Usage charts unavailable — API may be offline.
          </div>
        )}
      </motion.div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <section className="surface-card p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-medium text-foreground">Needs attention</h3>
              <p className="text-xs text-muted-foreground">Only gaps that block a clean demo.</p>
            </div>
            {attention.length === 0 ? <Badge variant="secondary">All clear</Badge> : null}
          </div>
          {attention.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border/70 bg-muted/20 px-3 py-6 text-center text-xs text-muted-foreground">
              Rules, workflows, articles, and tools look ready.
            </p>
          ) : (
            <ul className="space-y-2">
              {attention.map((item) => (
                <li key={item.href + item.label}>
                  <Link
                    href={item.href}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border/70 bg-background/70 px-3 py-2.5 text-sm transition-colors hover:border-border hover:bg-muted/40"
                  >
                    <span className="inline-flex items-center gap-2 text-foreground">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                      {item.label}
                    </span>
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="surface-card p-4">
          <h3 className="text-sm font-medium text-foreground">Quick links</h3>
          <p className="mb-3 text-xs text-muted-foreground">Jump to setup without cluttering Home.</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { href: "/sops", label: "Workflows" },
              { href: "/kb", label: "Articles" },
              { href: "/resources", label: "Tools" },
              { href: "/agent-rules", label: "Rules" },
              { href: "/settings", label: "Settings" },
              { href: "/history", label: "History" },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-lg border border-border/70 px-3 py-2 text-sm text-foreground transition-colors hover:bg-muted/40"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  hint,
  href,
  icon: Icon,
  loading,
}: {
  label: string;
  value: string;
  hint: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
}) {
  return (
    <Link href={href} className="surface-card block p-4 transition-colors hover:bg-muted/20">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </p>
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      </div>
      <p className="mt-1.5 text-2xl font-medium tracking-tight text-foreground tabular-nums">
        {loading ? "…" : value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
    </Link>
  );
}
