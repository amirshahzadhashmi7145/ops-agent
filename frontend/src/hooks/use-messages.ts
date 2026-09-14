"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { clearMessages, fetchMessage, fetchMessages } from "@/lib/api";

export function useMessages() {
  return useQuery({
    queryKey: ["messages"],
    queryFn: fetchMessages,
    refetchInterval: 5000,
  });
}

export function useMessage(id: string | null) {
  return useQuery({
    queryKey: ["messages", id],
    queryFn: () => fetchMessage(id!),
    enabled: Boolean(id),
  });
}

export function useClearMessages() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: clearMessages,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["messages"] });
      toast.success("Message outbox cleared");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}
