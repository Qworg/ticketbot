import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ticketService } from '../ticketService';
import { apiService } from '../api';
import { TicketStatus, Priority } from '../../types';

// Mock the API service
vi.mock('../api');

const mockTicket = {
  id: '1',
  discord_channel_id: 123456789,
  title: 'Test Ticket',
  description: 'Test description',
  status: TicketStatus.OPEN,
  priority: Priority.HIGH,
  creator_discord_id: 987654321,
  assigned_staff_id: 111222333,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:30:00Z',
};

const mockPaginatedResponse = {
  data: [mockTicket],
  total: 1,
  page: 1,
  per_page: 10,
  total_pages: 1,
};

const mockApiResponse = {
  data: mockTicket,
  success: true,
  message: 'Success',
};

describe('TicketService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getTickets', () => {
    it('calls API with correct parameters', async () => {
      vi.mocked(apiService.get).mockResolvedValue(mockPaginatedResponse);

      const params = {
        page: 1,
        per_page: 10,
        sort_by: 'created_at' as const,
        sort_order: 'desc' as const,
        status: [TicketStatus.OPEN],
        priority: [Priority.HIGH],
        search: 'test',
      };

      const result = await ticketService.getTickets(params);

      expect(apiService.get).toHaveBeenCalledWith('/tickets', params);
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('calls API with default parameters when none provided', async () => {
      vi.mocked(apiService.get).mockResolvedValue(mockPaginatedResponse);

      await ticketService.getTickets();

      expect(apiService.get).toHaveBeenCalledWith('/tickets', {});
    });

    it('handles API errors', async () => {
      const error = new Error('API Error');
      vi.mocked(apiService.get).mockRejectedValue(error);

      await expect(ticketService.getTickets()).rejects.toThrow('API Error');
    });
  });

  describe('getTicket', () => {
    it('calls API with correct ticket ID', async () => {
      vi.mocked(apiService.get).mockResolvedValue(mockApiResponse);

      const result = await ticketService.getTicket('1');

      expect(apiService.get).toHaveBeenCalledWith('/tickets/1');
      expect(result).toEqual(mockApiResponse);
    });

    it('handles API errors', async () => {
      const error = new Error('Ticket not found');
      vi.mocked(apiService.get).mockRejectedValue(error);

      await expect(ticketService.getTicket('999')).rejects.toThrow('Ticket not found');
    });
  });

  describe('createTicket', () => {
    it('calls API with ticket data', async () => {
      vi.mocked(apiService.post).mockResolvedValue(mockApiResponse);

      const ticketData = {
        title: 'New Ticket',
        description: 'New ticket description',
        priority: Priority.MEDIUM,
      };

      const result = await ticketService.createTicket(ticketData);

      expect(apiService.post).toHaveBeenCalledWith('/tickets', ticketData);
      expect(result).toEqual(mockApiResponse);
    });

    it('handles API errors', async () => {
      const error = new Error('Validation error');
      vi.mocked(apiService.post).mockRejectedValue(error);

      await expect(ticketService.createTicket({})).rejects.toThrow('Validation error');
    });
  });

  describe('updateTicket', () => {
    it('calls API with ticket ID and update data', async () => {
      vi.mocked(apiService.put).mockResolvedValue(mockApiResponse);

      const updateData = {
        status: TicketStatus.IN_PROGRESS,
        assigned_staff_id: 222333444,
      };

      const result = await ticketService.updateTicket('1', updateData);

      expect(apiService.put).toHaveBeenCalledWith('/tickets/1', updateData);
      expect(result).toEqual(mockApiResponse);
    });

    it('handles API errors', async () => {
      const error = new Error('Update failed');
      vi.mocked(apiService.put).mockRejectedValue(error);

      await expect(ticketService.updateTicket('1', {})).rejects.toThrow('Update failed');
    });
  });

  describe('deleteTicket', () => {
    it('calls API with ticket ID', async () => {
      const mockDeleteResponse = { data: undefined, success: true };
      vi.mocked(apiService.delete).mockResolvedValue(mockDeleteResponse);

      const result = await ticketService.deleteTicket('1');

      expect(apiService.delete).toHaveBeenCalledWith('/tickets/1');
      expect(result).toEqual(mockDeleteResponse);
    });

    it('handles API errors', async () => {
      const error = new Error('Delete failed');
      vi.mocked(apiService.delete).mockRejectedValue(error);

      await expect(ticketService.deleteTicket('1')).rejects.toThrow('Delete failed');
    });
  });
});