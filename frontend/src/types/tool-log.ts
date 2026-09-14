export interface ToolCallSummary {
  tool_name: string;
  call_count: number;
  success_count: number;
  last_called_at: string | null;
}

export interface ToolCallLogListItem {
  id: string;
  tool_name: string;
  source: string;
  http_method: string | null;
  response_status: number | null;
  latency_ms: number | null;
  success: boolean;
  created_by: string;
  created_at: string;
  conversation_id: string | null;
}

export interface ToolCallLogDetail extends ToolCallLogListItem {
  resource_id: string | null;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
}
