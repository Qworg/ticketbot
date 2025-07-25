import { apiService } from './api';
import { Ticket, TicketFilters, PaginatedResponse, ApiResponse } from '../types';

export interface TicketListParams extends TicketFilters {
  page?: number;
  per_page?: number;
  sort_by?: keyof Ticket;
  sort_order?: 'asc' | 'desc';
}

class TicketService {
  async getTickets(params: TicketListParams = {}): Promise<PaginatedResponse<Ticket>> {
    return apiService.get<PaginatedResponse<Ticket>>('/tickets', params);
  }

  async getTicket(id: string): Promise<ApiResponse<Ticket>> {
    return apiService.get<ApiResponse<Ticket>>(`/tickets/${id}`);
  }

  async createTicket(ticketData: Partial<Ticket>): Promise<ApiResponse<Ticket>> {
    return apiService.post<ApiResponse<Ticket>>('/tickets', ticketData);
  }

  async updateTicket(id: string, ticketData: Partial<Ticket>): Promise<ApiResponse<Ticket>> {
    return apiService.put<ApiResponse<Ticket>>(`/tickets/${id}`, ticketData);
  }

  async deleteTicket(id: string): Promise<ApiResponse<void>> {
    return apiService.delete<ApiResponse<void>>(`/tickets/${id}`);
  }
}

export const ticketService = new TicketService();
export default ticketService;