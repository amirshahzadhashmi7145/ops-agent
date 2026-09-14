export type ProcessingStatus =
  | "queued"
  | "formatting"
  | "indexing"
  | "ready"
  | "failed";

export interface KbReferenceListItem {
  id: string;
  title: string;
  summary: string | null;
  source_url: string | null;
  enabled: boolean;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface KbReference extends KbReferenceListItem {
  raw_text: string;
  markdown: string | null;
  content_hash: string;
  embedding_model: string | null;
  chunk_count: number;
}

export interface ReferenceFormValues {
  title: string;
  raw_text: string;
  source_url?: string;
}

export type StatusFilter = "all" | ProcessingStatus | "disabled";
