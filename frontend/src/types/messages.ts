export interface OutboundMessageListItem {
  id: string;
  from_address: string;
  to_address: string;
  subject: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
  read: boolean;
  created_at: string;
  message_kind?: string | null;
}

export interface OutboundMessage extends OutboundMessageListItem {
  body: string;
  metadata?: Record<string, unknown> | null;
}
