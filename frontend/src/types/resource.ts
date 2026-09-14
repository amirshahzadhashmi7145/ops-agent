export type ParameterType = "string" | "number" | "boolean";
export type ToolScope = "internal" | "external";

export interface ParameterField {
  name: string;
  type: ParameterType;
  required: boolean;
  description: string;
  default_value: string;
}

export interface HeaderField {
  key: string;
  value: string;
  is_secret?: boolean;
}

export interface ResourceListItem {
  id: string;
  name: string;
  description: string;
  tool_scope: ToolScope;
  http_method: string;
  url: string;
  last_tested_at: string | null;
  last_test_success: boolean | null;
  active: boolean;
  resolved_url_preview?: string | null;
}

export interface Resource extends ResourceListItem {
  connection_mode: "direct" | "existing";
  connection_id: string | null;
  parameters: ParameterField[];
  fixed_headers: HeaderField[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ResourceFormValues {
  name: string;
  description: string;
  tool_scope: ToolScope;
  connection_mode: "direct" | "existing";
  connection_id: string | null;
  http_method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  url: string;
  parameters: ParameterField[];
  fixed_headers: HeaderField[];
}

export interface ResourceTestResult {
  success: boolean;
  status_code: number | null;
  headers: Record<string, string>;
  body: unknown;
  latency_ms: number;
  error: string | null;
  resolved_url: string | null;
}
