import { apiService } from './api';
import { Message, ApiResponse, PaginatedResponse } from '../types';

export interface MessageListParams {
  page?: number;
  per_page?: number;
  sort_order?: 'asc' | 'desc';
}

class MessageService {
  async getTicketMessages(ticketId: string, params: MessageListParams = {}): Promise<PaginatedResponse<Message>> {
    return apiService.get<PaginatedResponse<Message>>(`/tickets/${ticketId}/messages`, params);
  }

  async addMessage(ticketId: string, content: string): Promise<ApiResponse<Message>> {
    return apiService.post<ApiResponse<Message>>(`/tickets/${ticketId}/messages`, { content });
  }
}

export const messageService = new MessageService();
export default messageService;