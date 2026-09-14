export interface AgentSettingsRuntimeInfo {
  llm_provider: string;
  llm_model: string;
  embedding_provider: string;
  embedding_model: string;
  env_max_tool_rounds: number;
  env_sop_auto_match_threshold: number;
  env_sop_match_threshold: number;
  env_kb_search_top_k: number;
  env_llm_temperature: number;
  env_llm_max_tokens: number;
}

export interface AgentSettings {
  id: string;
  agent_name: string;
  system_prompt: string;
  greeting_message: string;
  escalation_message: string;
  enable_kb_search: boolean;
  enable_sop_matching: boolean;
  enable_external_tools: boolean;
  enable_internal_tools: boolean;
  max_tool_rounds: number | null;
  sop_auto_match_threshold: number | null;
  sop_match_threshold: number | null;
  kb_search_top_k: number | null;
  llm_temperature: number | null;
  llm_max_tokens: number | null;
  updated_by: string;
  updated_at: string;
  runtime: AgentSettingsRuntimeInfo;
}

export interface AgentSettingsFormValues {
  agent_name: string;
  system_prompt: string;
  greeting_message: string;
  escalation_message: string;
  enable_kb_search: boolean;
  enable_sop_matching: boolean;
  enable_external_tools: boolean;
  enable_internal_tools: boolean;
  max_tool_rounds: number | null;
  sop_auto_match_threshold: number | null;
  sop_match_threshold: number | null;
  kb_search_top_k: number | null;
  llm_temperature: number | null;
  llm_max_tokens: number | null;
}
