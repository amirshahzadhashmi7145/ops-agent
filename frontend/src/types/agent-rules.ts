export type AgentRuleCategory =
  | "business_context"
  | "escalations"
  | "response_tone_style"
  | "agent_capabilities";

export interface AgentRule {
  id: string;
  category: AgentRuleCategory;
  content: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AgentRuleFormValues {
  category: AgentRuleCategory;
  content: string;
}
