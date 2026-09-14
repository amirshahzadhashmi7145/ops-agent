"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { fetchAgentSettings, updateAgentSettings } from "@/lib/api";
import type { AgentSettingsFormValues } from "@/types/agent-settings";

const QUERY_KEY = ["agent-settings"];

export function useAgentSettings() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchAgentSettings,
    staleTime: 60_000,
  });
}

export function useUpdateAgentSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateAgentSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Agent settings saved");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function settingsToFormValues(
  settings: import("@/types/agent-settings").AgentSettings,
): AgentSettingsFormValues {
  return {
    agent_name: settings.agent_name,
    system_prompt: settings.system_prompt,
    greeting_message: settings.greeting_message,
    escalation_message: settings.escalation_message,
    enable_kb_search: settings.enable_kb_search,
    enable_sop_matching: settings.enable_sop_matching,
    enable_external_tools: settings.enable_external_tools,
    enable_internal_tools: settings.enable_internal_tools,
    max_tool_rounds: settings.max_tool_rounds,
    sop_auto_match_threshold: settings.sop_auto_match_threshold,
    sop_match_threshold: settings.sop_match_threshold,
    kb_search_top_k: settings.kb_search_top_k,
    llm_temperature: settings.llm_temperature,
    llm_max_tokens: settings.llm_max_tokens,
  };
}
