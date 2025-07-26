import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Pagination,
  CircularProgress,
  Alert,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Share as ShareIcon,
  OpenInNew as OpenInNewIcon,
  FilterList as FilterListIcon,
  ContentCopy as ContentCopyIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import { transcriptService, TranscriptSearchParams } from '../services/transcriptService';
import { TranscriptSearchResult, TicketStatus } from '../types';

interface SearchFilters extends TranscriptSearchParams {
  search: string;
}

const TranscriptSearch: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    search: '',
    search_mode: 'basic',
    highlight_results: true,
    page: 1,
    size: 10
  });
  const [results, setResults] = useState<TranscriptSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [shareDialog, setShareDialog] = useState<{ open: boolean; ticketId: string; shareUrl?: string }>({
    open: false,
    ticketId: ''
  });
  const [shareLoading, setShareLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const handleSearch = async (newFilters?: Partial<SearchFilters>) => {
    const searchFilters = { ...filters, ...newFilters, search: searchTerm };
    
    if (!searchFilters.search.trim()) {
      setError('Please enter a search term');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await transcriptService.searchTranscripts(searchFilters);
      setResults(response.data);
      setTotalResults(response.total);
      setTotalPages(response.total_pages);
      setCurrentPage(response.page);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to search transcripts');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, page: number) => {
    setFilters(prev => ({ ...prev, page }));
    handleSearch({ page });
  };

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSearch({ page: 1 });
    }
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      search_mode: 'basic',
      highlight_results: true,
      page: 1,
      size: 10
    });
    setSearchTerm('');
    setResults([]);
    setError(null);
  };

  const handleShareTranscript = async (ticketId: string) => {
    setShareDialog({ open: true, ticketId });
    setShareLoading(true);

    try {
      const response = await transcriptService.shareTranscript(ticketId);
      const shareUrl = `${window.location.origin}/shared/${response.data.share_token}`;
      setShareDialog({ open: true, ticketId, shareUrl });
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to create share link',
        severity: 'error'
      });
      setShareDialog({ open: false, ticketId: '' });
    } finally {
      setShareLoading(false);
    }
  };

  const handleCopyShareUrl = async () => {
    if (shareDialog.shareUrl) {
      try {
        await navigator.clipboard.writeText(shareDialog.shareUrl);
        setSnackbar({
          open: true,
          message: 'Share link copied to clipboard',
          severity: 'success'
        });
      } catch (err) {
        setSnackbar({
          open: true,
          message: 'Failed to copy link to clipboard',
          severity: 'error'
        });
      }
    }
  };

  const handleCloseShareDialog = () => {
    setShareDialog({ open: false, ticketId: '' });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const renderHighlightedContent = (content: string, snippets?: string[]) => {
    if (snippets && snippets.length > 0) {
      return (
        <Box>
          {snippets.map((snippet, index) => (
            <Typography
              key={index}
              variant="body2"
              sx={{ 
                mb: 1,
                '& mark': {
                  backgroundColor: 'yellow',
                  fontWeight: 'bold'
                }
              }}
              dangerouslySetInnerHTML={{ __html: snippet }}
            />
          ))}
        </Box>
      );
    }
    
    return (
      <Typography variant="body2" color="text.secondary">
        {content.substring(0, 200)}...
      </Typography>
    );
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search Transcripts
      </Typography>
      
      {/* Search Form */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <Box sx={{ flex: 1, minWidth: '300px' }}>
            <TextField
              fullWidth
              label="Search transcripts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={handleKeyPress}
              InputProps={{
                startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
              }}
              placeholder="Enter keywords to search in ticket conversations"
            />
          </Box>
          <Button
            variant="contained"
            onClick={() => handleSearch({ page: 1 })}
            disabled={loading || !searchTerm.trim()}
            startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
            data-testid="search-button"
          >
            {loading ? 'Searching...' : 'Search'}
          </Button>
          <Button
            variant="outlined"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            startIcon={<FilterListIcon />}
          >
            Filters
          </Button>
        </Box>

        {/* Advanced Filters */}
        <Accordion expanded={showAdvancedFilters} onChange={() => setShowAdvancedFilters(!showAdvancedFilters)}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">Advanced Search Options</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <FormControl sx={{ minWidth: 200 }}>
                <InputLabel id="search-mode-label">Search Mode</InputLabel>
                <Select
                  labelId="search-mode-label"
                  value={filters.search_mode || 'basic'}
                  onChange={(e) => handleFilterChange('search_mode', e.target.value)}
                  label="Search Mode"
                >
                  <MenuItem value="basic">Basic</MenuItem>
                  <MenuItem value="fuzzy">Fuzzy</MenuItem>
                  <MenuItem value="exact">Exact Match</MenuItem>
                </Select>
              </FormControl>
              <TextField
                type="date"
                label="Created After"
                value={filters.created_after || ''}
                onChange={(e) => handleFilterChange('created_after', e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 200 }}
              />
              <TextField
                type="date"
                label="Created Before"
                value={filters.created_before || ''}
                onChange={(e) => handleFilterChange('created_before', e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 200 }}
              />
              <FormControl sx={{ minWidth: 200 }}>
                <InputLabel id="ticket-status-label">Ticket Status</InputLabel>
                <Select
                  labelId="ticket-status-label"
                  value={filters.status || ''}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  label="Ticket Status"
                >
                  <MenuItem value="">All Statuses</MenuItem>
                  <MenuItem value={TicketStatus.OPEN}>Open</MenuItem>
                  <MenuItem value={TicketStatus.IN_PROGRESS}>In Progress</MenuItem>
                  <MenuItem value={TicketStatus.WAITING}>Waiting</MenuItem>
                  <MenuItem value={TicketStatus.CLOSED}>Closed</MenuItem>
                  <MenuItem value={TicketStatus.ARCHIVED}>Archived</MenuItem>
                </Select>
              </FormControl>
              <TextField
                type="number"
                label="Staff ID"
                value={filters.staff_id || ''}
                onChange={(e) => handleFilterChange('staff_id', e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="Filter by staff member"
                sx={{ minWidth: 200 }}
              />
              <Button variant="outlined" onClick={clearFilters}>
                Clear Filters
              </Button>
            </Box>
          </AccordionDetails>
        </Accordion>
      </Paper>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Search Results */}
      {results.length > 0 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              Search Results ({totalResults} found)
            </Typography>
            <Chip 
              label={`Page ${currentPage} of ${totalPages}`} 
              variant="outlined" 
            />
          </Box>

          {results.map((result) => (
            <Card key={result.id} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="h6" component="h3">
                      {result.ticket_title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Ticket ID: {result.ticket_id} • Created: {format(new Date(result.created_at), 'MMM dd, yyyy HH:mm')}
                    </Typography>
                    {result.relevance_score && (
                      <Chip 
                        label={`Relevance: ${Math.round(result.relevance_score * 100)}%`} 
                        size="small" 
                        color="primary" 
                        variant="outlined"
                        sx={{ mt: 1 }}
                      />
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Tooltip title="View Ticket">
                      <IconButton 
                        size="small"
                        onClick={() => window.open(`/tickets/${result.ticket_id}`, '_blank')}
                      >
                        <OpenInNewIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Share Transcript">
                      <IconButton 
                        size="small"
                        onClick={() => handleShareTranscript(result.ticket_id)}
                      >
                        <ShareIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>

                <Divider sx={{ mb: 2 }} />

                {/* Highlighted Content */}
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 'bold' }}>
                    Matching Content:
                  </Typography>
                  {renderHighlightedContent(result.content, result.context_snippets)}
                </Box>
              </CardContent>
            </Card>
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={handlePageChange}
                color="primary"
                size="large"
              />
            </Box>
          )}
        </Box>
      )}

      {/* No Results */}
      {!loading && results.length === 0 && searchTerm && !error && (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No transcripts found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your search terms or filters
          </Typography>
        </Paper>
      )}

      {/* Initial State */}
      {!loading && results.length === 0 && !searchTerm && !error && (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <SearchIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            Search Ticket Transcripts
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Enter keywords to search through all ticket conversations and find relevant information quickly.
          </Typography>
        </Paper>
      )}

      {/* Share Dialog */}
      <Dialog open={shareDialog.open} onClose={handleCloseShareDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Share Transcript</DialogTitle>
        <DialogContent>
          {shareLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : shareDialog.shareUrl ? (
            <Box>
              <Typography variant="body2" sx={{ mb: 2 }}>
                Share this link to give others access to the transcript:
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <TextField
                  fullWidth
                  value={shareDialog.shareUrl}
                  InputProps={{
                    readOnly: true,
                  }}
                  variant="outlined"
                  size="small"
                />
                <Button
                  variant="outlined"
                  onClick={handleCopyShareUrl}
                  startIcon={<ContentCopyIcon />}
                >
                  Copy
                </Button>
              </Box>
              <Alert severity="info" sx={{ mt: 2 }}>
                This link will allow anyone with access to view the transcript. Share responsibly.
              </Alert>
            </Box>
          ) : (
            <Typography>Failed to generate share link</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseShareDialog}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TranscriptSearch;