export interface Ticket {
  id: string;
  discord_channel_id: number;
  title: string;
  description?: string;
  status: TicketStatus;
  priority: Priority;
  creator_discord_id: number;
  assigned_staff_id?: number;
  created_at: string;
  updated_at: string;
  closed_at?: string;
}

export interface Message {
  id: string;
  ticket_id: string;
  discord_message_id?: number;
  author_discord_id: number;
  content: string;
  message_type: MessageType;
  created_at: string;
}

export interface Transcript {
  id: string;
  ticket_id: string;
  content: string;
  formatted_content?: any;
  share_token?: string;
  created_at: string;
  updated_at: string;
}

export interface Staff {
  id: string;
  discord_id: number;
  username: string;
  role: string;
  permissions: Record<string, any>;
  active: boolean;
  created_at: string;
}

export enum TicketStatus {
  OPEN = 'open',
  IN_PROGRESS = 'in_progress',
  WAITING = 'waiting',
  CLOSED = 'closed',
  ARCHIVED = 'archived',
}

export enum Priority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
}

export enum MessageType {
  USER_MESSAGE = 'user_message',
  STAFF_MESSAGE = 'staff_message',
  SYSTEM_MESSAGE = 'system_message',
  BOT_MESSAGE = 'bot_message',
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface TicketFilters {
  status?: TicketStatus[];
  priority?: Priority[];
  assigned_staff_id?: number;
  creator_discord_id?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface TranscriptSearchFilters {
  search: string;
  search_mode?: 'basic' | 'fuzzy' | 'exact';
  created_after?: string;
  created_before?: string;
  staff_id?: number;
  status?: TicketStatus;
  highlight_results?: boolean;
}

export interface TranscriptSearchResult {
  id: string;
  ticket_id: string;
  ticket_title: string;
  content: string;
  formatted_content?: any;
  share_token?: string;
  created_at: string;
  updated_at: string;
  context_snippets?: string[];
  highlighted_content?: string;
  relevance_score?: number;
}