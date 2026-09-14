"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createResource,
  deleteResource,
  fetchResource,
  fetchResources,
  setResourceActive,
  testResourceDraft,
  testResourceSaved,
  updateResource,
} from "@/lib/api";
import type { ResourceFormValues } from "@/types/resource";

const STABLE_STALE_TIME = 120_000;

export function useResources() {
  return useQuery({
    queryKey: ["resources"],
    queryFn: fetchResources,
    staleTime: STABLE_STALE_TIME,
  });
}

export function useResource(id: string | null) {
  return useQuery({
    queryKey: ["resources", id],
    queryFn: () => fetchResource(id!),
    enabled: Boolean(id),
    staleTime: STABLE_STALE_TIME,
  });
}

export function useCreateResource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createResource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast.success("REST query created");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useUpdateResource(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ResourceFormValues & { force_save?: boolean; last_test_success?: boolean }) =>
      updateResource(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      queryClient.invalidateQueries({ queryKey: ["resources", id] });
      toast.success("REST query updated");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useDeleteResource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteResource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast.success("REST query deleted");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useSetResourceActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => setResourceActive(id, active),
    onSuccess: (_resource, variables) => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast.success(variables.active ? "Tool enabled for agent" : "Tool disabled for agent");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useTestResource(resourceId?: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (
      payload: ResourceFormValues & {
        test_payload?: Record<string, unknown>;
        test_headers?: ResourceFormValues["fixed_headers"];
        resource_id?: string;
      },
    ) => {
      const { resource_id, ...testBody } = payload;
      const id = resource_id ?? resourceId ?? null;
      return id ? testResourceSaved(id, testBody) : testResourceDraft(testBody);
    },
    onSuccess: (result, variables) => {
      const id = variables.resource_id ?? resourceId;
      if (id) {
        queryClient.invalidateQueries({ queryKey: ["resources"] });
        queryClient.invalidateQueries({ queryKey: ["resources", id] });
      }
      queryClient.invalidateQueries({ queryKey: ["tool-logs"] });
      return result;
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
