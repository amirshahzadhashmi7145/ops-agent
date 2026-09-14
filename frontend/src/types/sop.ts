export type SopProcessingStatus =
  | "queued"
  | "formatting"
  | "indexing"
  | "ready"
  | "failed";

export interface SopCategory {
  id: string;
  slug: string;
  name: string;
  description?: string | null;
}

export interface SopProcessStep {
  id?: string;
  type?: string;
  instruction?: string;
  tool?: string;
  inputs?: Record<string, unknown>;
}

export interface SopProcess {
  id: string;
  process_key: string;
  title: string;
  description: string;
  trigger_phrases: string[];
  steps: SopProcessStep[];
  tools: string[];
  sort_order: number;
}

export interface SopDocumentListItem {
  id: string;
  title: string;
  category_id: string;
  category_slug?: string | null;
  category_name?: string | null;
  summary: string | null;
  enabled: boolean;
  processing_status: SopProcessingStatus;
  processing_error: string | null;
  process_count: number;
  tool_warnings?: string[] | null;
  updated_at: string;
}

export interface SopDocument extends SopDocumentListItem {
  raw_text: string;
  markdown: string | null;
  content_hash: string;
  embedding_model: string | null;
  processes: SopProcess[];
  created_by: string;
  created_at: string;
}

export interface SopDocumentFormValues {
  title: string;
  category_id: string;
  raw_text: string;
}
