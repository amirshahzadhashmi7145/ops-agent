"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createSopCategory,
  createSopDocument,
  deleteSopDocument,
  fetchSopCategories,
  fetchSopDocument,
  fetchSopDocuments,
  reprocessSopDocument,
  setSopDocumentEnabled,
  updateSopDocument,
} from "@/lib/api";
import type { SopDocument, SopDocumentFormValues, SopDocumentListItem } from "@/types/sop";

const TERMINAL = new Set(["ready", "failed"]);

export function useSopCategories() {
  return useQuery({
    queryKey: ["sop-categories"],
    queryFn: fetchSopCategories,
    staleTime: 120_000,
  });
}

export function useCreateSopCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSopCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sop-categories"] });
      toast.success("Category created");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useSopDocuments(filters?: {
  status?: string;
  category?: string;
  enabled?: boolean;
  search?: string;
}) {
  return useQuery({
    queryKey: ["sop-documents", filters],
    queryFn: () => fetchSopDocuments(filters),
    refetchInterval: (query) => {
      const items = query.state.data as SopDocumentListItem[] | undefined;
      if (!items?.length) return false;
      return items.some((item) => !TERMINAL.has(item.processing_status)) ? 2000 : false;
    },
  });
}

export function useSopDocument(id: string | null, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: ["sop-documents", id],
    queryFn: () => fetchSopDocument(id!),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      if (!options?.poll) return false;
      const data = query.state.data as SopDocument | undefined;
      if (!data) return 2000;
      return TERMINAL.has(data.processing_status) ? false : 2000;
    },
  });
}

export function useCreateSopDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSopDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sop-documents"] });
      toast.success("SOP created — processing started");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useUpdateSopDocument(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SopDocumentFormValues) => updateSopDocument(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sop-documents"] });
      queryClient.invalidateQueries({ queryKey: ["sop-documents", id] });
      toast.success("SOP updated");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useSetSopEnabled() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      setSopDocumentEnabled(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sop-documents"] });
      toast.success("SOP updated");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useDeleteSopDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteSopDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sop-documents"] });
      toast.success("SOP deleted");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useReprocessSopDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reprocessSopDocument,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["sop-documents"] });
      queryClient.invalidateQueries({ queryKey: ["sop-documents", id] });
      toast.success("SOP reprocessing started");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
