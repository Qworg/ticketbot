import { describe, it, expect, vi, beforeEach } from 'vitest';
import { transcriptService, TranscriptSearchParams } from '../transcriptService';
import { apiService } from '../api';

// Mock the API service
vi.mock('../api', () => ({
  apiService: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('TranscriptService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('searchTranscripts', () => {
    it('calls API with correct parameters for basic search', async () => {
      const mockResponse = {
        data: [],
        total: 0,
        page: 1,
        size: 10,
        total_pages: 0,
        search_term: 'test',
        search_mode: 'basic'
      };

      vi.mocked(apiService.get).mockResolvedValue(mockResponse);

      const params: TranscriptSearchParams = {
        search: 'test',
        page: 1,
        size: 10
      };

      const result = await transcriptService.searchTranscripts(params);

      expect(apiService.get).toHaveBeenCalledWith('/search/transcripts', params);
      expect(result).toEqual(mockResponse);
    });

    it('calls API with advanced search parameters', async () => {
      const mockResponse = {
        data: [],
        total: 0,
        page: 1,
        size: 20,
        total_pages: 0,
        search_term: 'advanced search',
        search_mode: 'fuzzy'
      };

      vi.mocked(apiService.get).mockResolvedValue(mockResponse);

      const params: TranscriptSearchParams = {
        search: 'advanced search',
        search_mode: 'fuzzy',
        created_after: '2024-01-01',
        created_before: '2024-12-31',
        staff_id: 123,
        status: 'open',
        page: 1,
        size: 20,
        highlight_results: true
      };

      const result = await transcriptService.searchTranscripts(params);

      expect(apiService.get).toHaveBeenCalledWith('/search/transcripts', params);
      expect(result).toEqual(mockResponse);
    });

    it('handles API errors correctly', async () => {
      const errorResponse = {
        response: {
          data: {
            detail: 'Search service unavailable'
          }
        }
      };

      vi.mocked(apiService.get).mockRejectedValue(errorResponse);

      const params: TranscriptSearchParams = {
        search: 'test'
      };

      await expect(transcriptService.searchTranscripts(params)).rejects.toEqual(errorResponse);
    });
  });

  describe('getTranscript', () => {
    it('calls API with correct ticket ID', async () => {
      const mockResponse = {
        data: {
          id: 'transcript-1',
          ticket_id: 'ticket-1',
          content: 'Transcript content',
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:30:00Z'
        },
        success: true
      };

      vi.mocked(apiService.get).mockResolvedValue(mockResponse);

      const result = await transcriptService.getTranscript('ticket-1');

      expect(apiService.get).toHaveBeenCalledWith('/tickets/ticket-1/transcript');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('shareTranscript', () => {
    it('calls API to create share token', async () => {
      const mockResponse = {
        data: {
          share_token: 'abc123',
          share_url: 'https://example.com/shared/abc123'
        },
        success: true
      };

      vi.mocked(apiService.post).mockResolvedValue(mockResponse);

      const result = await transcriptService.shareTranscript('ticket-1');

      expect(apiService.post).toHaveBeenCalledWith('/tickets/ticket-1/transcript/share');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getSharedTranscript', () => {
    it('calls API with share token', async () => {
      const mockResponse = {
        data: {
          id: 'transcript-1',
          ticket_id: 'ticket-1',
          content: 'Shared transcript content',
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:30:00Z'
        },
        success: true
      };

      vi.mocked(apiService.get).mockResolvedValue(mockResponse);

      const result = await transcriptService.getSharedTranscript('abc123');

      expect(apiService.get).toHaveBeenCalledWith('/transcripts/shared/abc123');
      expect(result).toEqual(mockResponse);
    });
  });
});