import { apiService } from './api';
import { Transcript, PaginatedResponse, ApiResponse } from '../types';

export interface TranscriptSearchParams {
  search: string;
  search_mode?: 'basic' | 'fuzzy' | 'exact';
  created_after?: string;
  created_before?: string;
  staff_id?: number;
  status?: string;
  page?: number;
  size?: number;
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

export interface TranscriptSearchResponse {
  data: TranscriptSearchResult[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
  search_term: string;
  search_mode: string;
}

class TranscriptService {
  async searchTranscripts(params: TranscriptSearchParams): Promise<TranscriptSearchResponse> {
    return apiService.get<TranscriptSearchResponse>('/search/transcripts', params);
  }

  async getTranscript(ticketId: string): Promise<ApiResponse<Transcript>> {
    return apiService.get<ApiResponse<Transcript>>(`/tickets/${ticketId}/transcript`);
  }

  async shareTranscript(ticketId: string): Promise<ApiResponse<{ share_token: string; share_url: string }>> {
    return apiService.post<ApiResponse<{ share_token: string; share_url: string }>>(`/tickets/${ticketId}/transcript/share`);
  }

  async getSharedTranscript(shareToken: string): Promise<ApiResponse<Transcript>> {
    return apiService.get<ApiResponse<Transcript>>(`/transcripts/shared/${shareToken}`);
  }
}

export const transcriptService = new TranscriptService();
export default transcriptService;