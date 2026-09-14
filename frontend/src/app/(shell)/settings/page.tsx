"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  BookOpen,
  Bot,
  Cpu,
  Loader2,
  ScrollText,
  Shield,
  SlidersHorizontal,
  Sparkles,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  settingsToFormValues,
  useAgentSettings,
  useUpdateAgentSettings,
} from "@/hooks/use-agent-settings";
import { buttonMotion, fadeSlideUp, listItemVariants } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { AgentSettingsFormValues } from "@/types/agent-settings";

function SectionCard({
  title,
  description,
  icon: Icon,
  children,
  index = 0,
}: {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  index?: number;
}) {
  return (
    <motion.section
      custom={index}
      variants={listItemVariants}
      initial="hidden"
      animate="visible"
      className="surface-card p-6"
    >
      <div className="mb-5 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-foreground">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </motion.section>
  );
}

function CapabilityRow({
  id,
  label,
  description,
  checked,
  onCheckedChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 rounded-xl border border-border/70 bg-background/60 p-4 transition-colors hover:border-border"
    >
      <Checkbox id={id} checked={checked} onCheckedChange={onCheckedChange} className="mt-0.5" />
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </label>
  );
}

function OptionalNumberInput({
  label,
  hint,
  value,
  placeholder,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  hint: string;
  value: number | null;
  placeholder: string;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number | null) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input
        type="number"
        min={min}
        max={max}
        step={step ?? 1}
        placeholder={placeholder}
        value={value ?? ""}
        onChange={(event) => {
          const raw = event.target.value.trim();
          onChange(raw === "" ? null : Number(raw));
        }}
      />
      <p className="text-xs text-muted-foreground">{hint}</p>
    </div>
  );
}

const QUICK_LINKS = [
  { href: "/agent-rules", label: "Agent Rules", icon: ScrollText },
  { href: "/sops", label: "SOPs", icon: Bot },
  { href: "/kb", label: "Knowledge Base", icon: BookOpen },
  { href: "/resources", label: "Tools & Resources", icon: Wrench },
];

export default function SettingsPage() {
  const { data: settings, isLoading, isError, error, refetch } = useAgentSettings();
  const updateMutation = useUpdateAgentSettings();
  const [form, setForm] = useState<AgentSettingsFormValues | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(settingsToFormValues(settings));
    }
  }, [settings]);

  const patch = (partial: Partial<AgentSettingsFormValues>) => {
    setForm((current) => (current ? { ...current, ...partial } : current));
  };

  const handleSave = async () => {
    if (!form) return;
    await updateMutation.mutateAsync(form);
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl space-y-5 px-8 py-10">
        <div className="space-y-2">
          <Skeleton className="h-8 w-52" />
          <Skeleton className="h-4 w-full max-w-2xl" />
        </div>
        <div className="surface-card space-y-4 p-6">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-52 w-full" />
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </div>
        <div className="surface-card space-y-3 p-6">
          <div className="grid gap-3 md:grid-cols-2">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-16">
        <div className="surface-card space-y-4 p-6 text-center">
          <h3 className="text-lg font-semibold text-foreground">Couldn&apos;t load agent settings</h3>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : "Request failed while loading settings."}
          </p>
          <div className="flex justify-center">
            <Button variant="outline" onClick={() => void refetch()}>
              Try again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!form || !settings) {
    return null;
  }

  const runtime = settings.runtime;

  return (
    <motion.div
      className="mx-auto max-w-6xl px-8 py-10"
      variants={fadeSlideUp}
      initial="hidden"
      animate="visible"
    >
      <div className="mb-8 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="page-header">Agent Settings</h2>
          <p className="page-description max-w-2xl">
            Configure global agent identity, capabilities, and runtime behavior. Changes apply to
            every new chat message.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Last updated by {settings.updated_by} ·{" "}
            {new Date(settings.updated_at).toLocaleString()}
          </p>
        </div>
        <motion.div {...buttonMotion}>
          <Button onClick={() => void handleSave()} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : (
              "Save settings"
            )}
          </Button>
        </motion.div>
      </div>

      <div className="space-y-5">
        <SectionCard
          index={0}
          title="Identity & prompt"
          description="Core persona and base instructions sent with every request, before agent rules."
          icon={Sparkles}
        >
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Agent name</Label>
              <Input
                id="agent-name"
                value={form.agent_name}
                onChange={(event) => patch({ agent_name: event.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="system-prompt">Base system prompt</Label>
              <Textarea
                id="system-prompt"
                value={form.system_prompt}
                onChange={(event) => patch({ system_prompt: event.target.value })}
                className="min-h-[280px] font-mono text-xs leading-relaxed"
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="greeting">Default greeting</Label>
                <Textarea
                  id="greeting"
                  value={form.greeting_message}
                  onChange={(event) => patch({ greeting_message: event.target.value })}
                  className="min-h-[88px]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="escalation">Escalation guidance</Label>
                <Textarea
                  id="escalation"
                  value={form.escalation_message}
                  onChange={(event) => patch({ escalation_message: event.target.value })}
                  placeholder="Optional instructions for when to hand off to a human."
                  className="min-h-[88px]"
                />
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          index={1}
          title="Capabilities"
          description="Master switches for what the agent can access during conversations."
          icon={Bot}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <CapabilityRow
              id="enable-kb"
              label="Knowledge Base search"
              description="Allow search_knowledge_base for policy and documentation questions."
              checked={form.enable_kb_search}
              onCheckedChange={(checked) => patch({ enable_kb_search: checked })}
            />
            <CapabilityRow
              id="enable-sop"
              label="SOP matching"
              description="Allow automatic and manual SOP process matching for operational workflows."
              checked={form.enable_sop_matching}
              onCheckedChange={(checked) => patch({ enable_sop_matching: checked })}
            />
            <CapabilityRow
              id="enable-internal"
              label="Internal tools"
              description="Expose internal REST tools registered in Tools & Resources."
              checked={form.enable_internal_tools}
              onCheckedChange={(checked) => patch({ enable_internal_tools: checked })}
            />
            <CapabilityRow
              id="enable-external"
              label="External tools"
              description="Expose external API tools registered in Tools & Resources."
              checked={form.enable_external_tools}
              onCheckedChange={(checked) => patch({ enable_external_tools: checked })}
            />
          </div>
        </SectionCard>

        <SectionCard
          index={2}
          title="Behavior tuning"
          description="Optional overrides. Leave blank to use deployment defaults from environment."
          icon={SlidersHorizontal}
        >
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <OptionalNumberInput
              label="Max tool rounds"
              hint={`Default: ${runtime.env_max_tool_rounds}`}
              value={form.max_tool_rounds}
              placeholder={String(runtime.env_max_tool_rounds)}
              min={1}
              max={20}
              onChange={(value) => patch({ max_tool_rounds: value })}
            />
            <OptionalNumberInput
              label="SOP auto-match threshold"
              hint={`Default: ${runtime.env_sop_auto_match_threshold}`}
              value={form.sop_auto_match_threshold}
              placeholder={String(runtime.env_sop_auto_match_threshold)}
              min={0}
              max={1}
              step={0.05}
              onChange={(value) => patch({ sop_auto_match_threshold: value })}
            />
            <OptionalNumberInput
              label="SOP search threshold"
              hint={`Default: ${runtime.env_sop_match_threshold}`}
              value={form.sop_match_threshold}
              placeholder={String(runtime.env_sop_match_threshold)}
              min={0}
              max={1}
              step={0.05}
              onChange={(value) => patch({ sop_match_threshold: value })}
            />
            <OptionalNumberInput
              label="KB results count"
              hint={`Default: ${runtime.env_kb_search_top_k}`}
              value={form.kb_search_top_k}
              placeholder={String(runtime.env_kb_search_top_k)}
              min={1}
              max={20}
              onChange={(value) => patch({ kb_search_top_k: value })}
            />
            <OptionalNumberInput
              label="LLM temperature"
              hint={`Default: ${runtime.env_llm_temperature}`}
              value={form.llm_temperature}
              placeholder={String(runtime.env_llm_temperature)}
              min={0}
              max={2}
              step={0.1}
              onChange={(value) => patch({ llm_temperature: value })}
            />
            <OptionalNumberInput
              label="LLM max tokens"
              hint={`Default: ${runtime.env_llm_max_tokens}`}
              value={form.llm_max_tokens}
              placeholder={String(runtime.env_llm_max_tokens)}
              min={256}
              max={8192}
              step={128}
              onChange={(value) => patch({ llm_max_tokens: value })}
            />
          </div>
        </SectionCard>

        <SectionCard
          index={3}
          title="Model & infrastructure"
          description="Read-only deployment configuration. API keys remain in environment secrets."
          icon={Cpu}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-border/70 bg-background/60 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
                LLM
              </p>
              <p className="mt-2 text-sm font-medium text-foreground">
                {runtime.llm_provider} · {runtime.llm_model}
              </p>
            </div>
            <div className="rounded-xl border border-border/70 bg-background/60 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
                Embeddings
              </p>
              <p className="mt-2 text-sm font-medium text-foreground">
                {runtime.embedding_provider} · {runtime.embedding_model}
              </p>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          index={4}
          title="Related configuration"
          description="Manage detailed content and per-item enablement on dedicated pages."
          icon={Shield}
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {QUICK_LINKS.map((link) => {
              const Icon = link.icon;
              return (
                <Link key={link.href} href={link.href}>
                  <motion.div
                    {...buttonMotion}
                    className={cn(
                      "flex items-center justify-between rounded-xl border border-border/70",
                      "bg-background/60 px-4 py-3 text-sm font-medium text-foreground transition-colors hover:border-border",
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      {link.label}
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </motion.div>
                </Link>
              );
            })}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge variant="secondary">Agent rules are appended after the base prompt</Badge>
            <Badge variant="outline">Per-tool active state lives in Tools & Resources</Badge>
          </div>
        </SectionCard>
      </div>
    </motion.div>
  );
}
