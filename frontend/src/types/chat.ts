export interface ConversationListItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  pipeline_trace: PipelineTraceEvent[];
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export type AgentMode = "general_chat" | "tool_call" | "sop" | "forced_tool_call";

export type PipelineTraceEvent =
  | { type: "mode"; mode: AgentMode; reason?: string }
  | { type: "status_update"; message: string }
  | { type: "resource_called"; name: string; status_code?: number | null; latency_ms?: number | null }
  | { type: "resource_result"; name: string; success: boolean; body?: unknown; error?: string }
  | { type: "kb_search"; query: string; reference_ids?: string[]; match_count: number }
  | {
      type: "sop_matched";
      process_id: string;
      title: string;
      score: number;
      tools?: string[];
    }
  | {
      type: "sop_search";
      query: string;
      match_count: number;
      best_title?: string | null;
      best_score?: number | null;
    }
  | { type: "sop_step"; process_id: string; tool: string }
  | { type: "final_answer"; content: string; mode?: string }
  | { type: "error"; message: string };

export type ChatStreamEvent =
  | { type: "status_update"; message: string }
  | { type: "resource_called"; name: string; status_code?: number | null; latency_ms?: number | null }
  | { type: "sop_matched"; process_id: string; title: string; score: number }
  | { type: "sop_search"; query: string; match_count: number }
  | { type: "sop_step"; process_id: string; tool: string }
  | { type: "final_answer"; content: string; pipeline_trace?: PipelineTraceEvent[] }
  | { type: "error"; message: string }
  | { type: "done"; conversation_id: string; message_id: string };
