import type { AgentRule, AgentRuleFormValues } from "@/types/agent-rules";
import type {
  ChatStreamEvent,
  ConversationDetail,
  ConversationListItem,
} from "@/types/chat";
import type { KbReference, KbReferenceListItem, ReferenceFormValues } from "@/types/kb";
import type {
  Resource,
  ResourceFormValues,
  ResourceListItem,
  ResourceTestResult,
} from "@/types/resource";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function fetchResources(): Promise<ResourceListItem[]> {
  return apiFetch<ResourceListItem[]>("/api/resources");
}

export function fetchResource(id: string): Promise<Resource> {
  return apiFetch<Resource>(`/api/resources/${id}`);
}

export function createResource(
  payload: ResourceFormValues & { force_save?: boolean; last_test_success?: boolean },
): Promise<Resource> {
  return apiFetch<Resource>("/api/resources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateResource(
  id: string,
  payload: ResourceFormValues & { force_save?: boolean; last_test_success?: boolean },
): Promise<Resource> {
  return apiFetch<Resource>(`/api/resources/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteResource(id: string): Promise<void> {
  return apiFetch<void>(`/api/resources/${id}`, { method: "DELETE" });
}

export function setResourceActive(id: string, active: boolean): Promise<Resource> {
  return apiFetch<Resource>(`/api/resources/${id}/active`, {
    method: "PATCH",
    body: JSON.stringify({ active }),
  });
}

export function testResourceDraft(
  payload: ResourceFormValues & {
    test_payload?: Record<string, unknown>;
    test_headers?: ResourceFormValues["fixed_headers"];
  },
): Promise<ResourceTestResult> {
  return apiFetch<ResourceTestResult>("/api/resources/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function testResourceSaved(
  id: string,
  payload: ResourceFormValues & {
    test_payload?: Record<string, unknown>;
    test_headers?: ResourceFormValues["fixed_headers"];
  },
): Promise<ResourceTestResult> {
  return apiFetch<ResourceTestResult>(`/api/resources/${id}/test`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchConversations(): Promise<ConversationListItem[]> {
  return apiFetch<ConversationListItem[]>("/api/conversations");
}

export function fetchConversation(id: string): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/api/conversations/${id}`);
}

export function createConversation(title = "New chat"): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export function deleteConversation(id: string): Promise<void> {
  return apiFetch<void>(`/api/conversations/${id}`, { method: "DELETE" });
}

export async function* streamChat(
  payload: { message: string; conversation_id?: string },
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let detail = "Chat request failed";
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("No response stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      yield JSON.parse(line) as ChatStreamEvent;
    }
  }

  if (buffer.trim()) {
    yield JSON.parse(buffer) as ChatStreamEvent;
  }
}

export function fetchReferences(filters?: {
  status?: string;
  enabled?: boolean;
  search?: string;
}): Promise<KbReferenceListItem[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.enabled !== undefined) params.set("enabled", String(filters.enabled));
  if (filters?.search) params.set("search", filters.search);
  const query = params.toString();
  return apiFetch<KbReferenceListItem[]>(`/api/kb/references${query ? `?${query}` : ""}`);
}

export function fetchReference(id: string): Promise<KbReference> {
  return apiFetch<KbReference>(`/api/kb/references/${id}`);
}

export function createReference(payload: ReferenceFormValues): Promise<KbReference> {
  return apiFetch<KbReference>("/api/kb/references", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateReference(
  id: string,
  payload: Partial<ReferenceFormValues>,
): Promise<KbReference> {
  return apiFetch<KbReference>(`/api/kb/references/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function setReferenceEnabled(id: string, enabled: boolean): Promise<KbReference> {
  return apiFetch<KbReference>(`/api/kb/references/${id}/enabled`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
}

export function deleteReference(id: string): Promise<void> {
  return apiFetch<void>(`/api/kb/references/${id}`, { method: "DELETE" });
}

export function reprocessReference(id: string): Promise<KbReference> {
  return apiFetch<KbReference>(`/api/kb/references/${id}/reprocess`, {
    method: "POST",
  });
}

export function fetchAgentRules(): Promise<AgentRule[]> {
  return apiFetch<AgentRule[]>("/api/agent-rules");
}

export function createAgentRule(payload: AgentRuleFormValues): Promise<AgentRule> {
  return apiFetch<AgentRule>("/api/agent-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAgentRule(
  id: string,
  payload: Partial<AgentRuleFormValues>,
): Promise<AgentRule> {
  return apiFetch<AgentRule>(`/api/agent-rules/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAgentRule(id: string): Promise<void> {
  return apiFetch<void>(`/api/agent-rules/${id}`, { method: "DELETE" });
}

export function fetchAgentSettings(): Promise<import("@/types/agent-settings").AgentSettings> {
  return apiFetch("/api/agent-settings");
}

export function updateAgentSettings(
  payload: import("@/types/agent-settings").AgentSettingsFormValues,
): Promise<import("@/types/agent-settings").AgentSettings> {
  return apiFetch("/api/agent-settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function fetchAppConfig(): Promise<{ internal_api_base_url: string }> {
  return apiFetch<{ internal_api_base_url: string }>("/api/config");
}

export function fetchSopCategories(): Promise<import("@/types/sop").SopCategory[]> {
  return apiFetch("/api/sops/categories");
}

export function createSopCategory(payload: {
  name: string;
  description?: string;
}): Promise<import("@/types/sop").SopCategory> {
  return apiFetch("/api/sops/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchSopDocuments(filters?: {
  status?: string;
  category?: string;
  enabled?: boolean;
  search?: string;
}): Promise<import("@/types/sop").SopDocumentListItem[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.category) params.set("category", filters.category);
  if (filters?.enabled !== undefined) params.set("enabled", String(filters.enabled));
  if (filters?.search) params.set("search", filters.search);
  const query = params.toString();
  return apiFetch(`/api/sops/documents${query ? `?${query}` : ""}`);
}

export function fetchSopDocument(id: string): Promise<import("@/types/sop").SopDocument> {
  return apiFetch(`/api/sops/documents/${id}`);
}

export function createSopDocument(
  payload: import("@/types/sop").SopDocumentFormValues,
): Promise<import("@/types/sop").SopDocument> {
  return apiFetch("/api/sops/documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSopDocument(
  id: string,
  payload: import("@/types/sop").SopDocumentFormValues,
): Promise<import("@/types/sop").SopDocument> {
  return apiFetch(`/api/sops/documents/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function setSopDocumentEnabled(
  id: string,
  enabled: boolean,
): Promise<import("@/types/sop").SopDocument> {
  return apiFetch(`/api/sops/documents/${id}/enabled`, {
    method: "PATCH",
    body: JSON.stringify({ enabled }),
  });
}

export function deleteSopDocument(id: string): Promise<void> {
  return apiFetch(`/api/sops/documents/${id}`, { method: "DELETE" });
}

export function reprocessSopDocument(id: string): Promise<import("@/types/sop").SopDocument> {
  return apiFetch(`/api/sops/documents/${id}/reprocess`, { method: "POST" });
}

export function fetchSimCatalog(): Promise<import("@/types/sim").SimCatalog> {
  return apiFetch("/api/sim/catalog");
}

export function fetchMessages(): Promise<import("@/types/messages").OutboundMessageListItem[]> {
  return apiFetch("/api/messages");
}

export function fetchMessage(id: string): Promise<import("@/types/messages").OutboundMessage> {
  return apiFetch(`/api/messages/${id}`);
}

export function clearMessages(): Promise<void> {
  return apiFetch("/api/messages", { method: "DELETE" });
}

export function fetchToolLogSummary(): Promise<import("@/types/tool-log").ToolCallSummary[]> {
  return apiFetch("/api/tool-logs/summary");
}

export function fetchToolLogs(options?: {
  toolName?: string | null;
  resourceId?: string | null;
  limit?: number;
}): Promise<import("@/types/tool-log").ToolCallLogListItem[]> {
  const params = new URLSearchParams();
  if (options?.toolName) params.set("tool_name", options.toolName);
  if (options?.resourceId) params.set("resource_id", options.resourceId);
  params.set("limit", String(options?.limit ?? 200));
  const query = params.toString();
  return apiFetch(`/api/tool-logs${query ? `?${query}` : ""}`);
}

export function fetchToolLog(id: string): Promise<import("@/types/tool-log").ToolCallLogDetail> {
  return apiFetch(`/api/tool-logs/${id}`);
}
