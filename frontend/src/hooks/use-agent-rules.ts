"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createAgentRule,
  deleteAgentRule,
  fetchAgentRules,
  updateAgentRule,
} from "@/lib/api";
import type { AgentRuleFormValues } from "@/types/agent-rules";

const QUERY_KEY = ["agent-rules"];

export function useAgentRules() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchAgentRules,
    staleTime: 120_000,
  });
}

export function useCreateAgentRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAgentRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Rule added");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useUpdateAgentRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<AgentRuleFormValues> }) =>
      updateAgentRule(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Rule updated");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useDeleteAgentRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteAgentRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Rule deleted");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
