"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createReference,
  deleteReference,
  fetchReference,
  fetchReferences,
  reprocessReference,
  setReferenceEnabled,
  updateReference,
} from "@/lib/api";
import type { KbReference, KbReferenceListItem, ReferenceFormValues } from "@/types/kb";

const TERMINAL_STATUSES = new Set(["ready", "failed"]);

export function useReferences(filters?: {
  status?: string;
  enabled?: boolean;
  search?: string;
}) {
  return useQuery({
    queryKey: ["kb-references", filters],
    queryFn: () => fetchReferences(filters),
    refetchInterval: (query) => {
      const items = query.state.data as KbReferenceListItem[] | undefined;
      if (!items?.length) return false;
      const hasProcessing = items.some((item) => !TERMINAL_STATUSES.has(item.processing_status));
      return hasProcessing ? 2000 : false;
    },
  });
}

export function useReference(id: string | null, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ["kb-references", id],
    queryFn: () => fetchReference(id!),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      if (!options?.poll) return false;
      const data = query.state.data as KbReference | undefined;
      if (!data) return 2000;
      return TERMINAL_STATUSES.has(data.processing_status) ? false : 2000;
    },
  });
}

export function useCreateReference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createReference,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-references"] });
      toast.success("Reference created — processing started");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useUpdateReference(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Partial<ReferenceFormValues>) => updateReference(id, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["kb-references"] });
      queryClient.invalidateQueries({ queryKey: ["kb-references", id] });
      if (data.processing_status === "queued") {
        toast.success("Reference updated — reprocessing started");
      } else {
        toast.success("Reference updated");
      }
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useSetReferenceEnabled() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      setReferenceEnabled(id, enabled),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["kb-references"] });
      queryClient.invalidateQueries({ queryKey: ["kb-references", variables.id] });
      toast.success(variables.enabled ? "Reference enabled" : "Reference disabled");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useDeleteReference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteReference,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-references"] });
      toast.success("Reference deleted");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useReprocessReference() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reprocessReference,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["kb-references"] });
      queryClient.invalidateQueries({ queryKey: ["kb-references", id] });
      toast.success("Reprocessing started");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
