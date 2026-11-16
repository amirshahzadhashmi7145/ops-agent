"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  createConversation,
  deleteConversation,
  endConversation,
  fetchConversation,
  fetchConversations,
  reopenConversation,
  streamChat,
} from "@/lib/api";
import type { ChatMessage, ConversationStatus, PipelineTraceEvent } from "@/types/chat";

export function useConversations(status?: ConversationStatus) {
  return useQuery({
    queryKey: ["conversations", status ?? "all"],
    queryFn: () => fetchConversations(status),
  });
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ["conversations", id],
    queryFn: () => fetchConversation(id!),
    enabled: Boolean(id),
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => createConversation(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useEndConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: endConversation,
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.setQueryData(["conversations", conversation.id], conversation);
      toast.success("Conversation ended");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useReopenConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reopenConversation,
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.setQueryData(["conversations", conversation.id], conversation);
      toast.success("Conversation reopened");
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export interface SendMessageResult {
  conversationId: string;
  assistantMessage: ChatMessage;
}

export async function sendMessageWithStream(
  {
    conversationId,
    message,
    onEvent,
  }: {
    conversationId?: string | null;
    message: string;
    onEvent: (event: import("@/types/chat").ChatStreamEvent) => void;
  },
  signal?: AbortSignal,
): Promise<SendMessageResult> {
  let finalContent = "";
  let pipelineTrace: PipelineTraceEvent[] = [];
  let resolvedConversationId = conversationId || "";
  let messageId = "";

  for await (const event of streamChat(
    { message, conversation_id: conversationId || undefined },
    signal,
  )) {
    onEvent(event);
    if (event.type === "final_answer") {
      finalContent = event.content;
      pipelineTrace = event.pipeline_trace || [];
    }
    if (event.type === "done") {
      resolvedConversationId = event.conversation_id;
      messageId = event.message_id;
    }
    if (event.type === "error") {
      throw new Error(event.message);
    }
  }

  return {
    conversationId: resolvedConversationId,
    assistantMessage: {
      id: messageId || crypto.randomUUID(),
      role: "assistant",
      content: finalContent,
      pipeline_trace: pipelineTrace,
      created_at: new Date().toISOString(),
    },
  };
}
