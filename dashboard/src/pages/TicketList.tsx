import React, { useState, useEffect, useCallback } from 'react';
import {
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Tooltip,
  TableSortLabel,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { ticketService } from '../services/ticketService';
import { Ticket, TicketStatus, Priority, TicketFilters, PaginatedResponse } from '../types';

interface SortConfig {
  field: keyof Ticket;
  direction: 'asc' | 'desc';
}

const TicketList: React.FC = () => {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [totalCount, setTotalCount] = useState(0);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'created_at', direction: 'desc' });
  
  // Filter states
  const [filters, setFilters] = useState<TicketFilters>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<TicketStatus[]>([]);
  const [priorityFilter, setPriorityFilter] = useState<Priority[]>([]);

  const fetchTickets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = {
        page: page + 1, // API uses 1-based pagination
        per_page: rowsPerPage,
        sort_by: sortConfig.field,
        sort_order: sortConfig.direction,
        ...filters,
        ...(searchTerm && { search: searchTerm }),
        ...(statusFilter.length > 0 && { status: statusFilter }),
        ...(priorityFilter.length > 0 && { priority: priorityFilter }),
      };

      const response = await ticketService.getTickets(params);
      setTickets(response.data);
      setTotalCount(response.total);
    } catch (err) {
      setError('Failed to fetch tickets. Please try again.');
      console.error('Error fetching tickets:', err);
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, sortConfig, filters, searchTerm, statusFilter, priorityFilter]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  const handleSort = (field: keyof Ticket) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handlePageChange = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
    setPage(0); // Reset to first page when searching
  };

  const handleStatusFilterChange = (event: any) => {
    setStatusFilter(event.target.value as TicketStatus[]);
    setPage(0);
  };

  const handlePriorityFilterChange = (event: any) => {
    setPriorityFilter(event.target.value as Priority[]);
    setPage(0);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setStatusFilter([]);
    setPriorityFilter([]);
    setFilters({});
    setPage(0);
  };

  const getStatusColor = (status: TicketStatus): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status) {
      case TicketStatus.OPEN:
        return 'primary';
      case TicketStatus.IN_PROGRESS:
        return 'info';
      case TicketStatus.WAITING:
        return 'warning';
      case TicketStatus.CLOSED:
        return 'success';
      case TicketStatus.ARCHIVED:
        return 'default';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority: Priority): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (priority) {
      case Priority.LOW:
        return 'success';
      case Priority.MEDIUM:
        return 'info';
      case Priority.HIGH:
        return 'warning';
      case Priority.URGENT:
        return 'error';
      default:
        return 'default';
    }
  };

  const handleViewTicket = (ticketId: string) => {
    navigate(`/tickets/${ticketId}`);
  };

  if (error) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          Tickets
        </Typography>
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Tickets
      </Typography>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                fullWidth
                label="Search tickets"
                value={searchTerm}
                onChange={handleSearchChange}
                placeholder="Search by title or description..."
                size="small"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  multiple
                  value={statusFilter}
                  onChange={handleStatusFilterChange}
                  label="Status"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {Object.values(TicketStatus).map((status) => (
                    <MenuItem key={status} value={status}>
                      {status.replace('_', ' ').toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Priority</InputLabel>
                <Select
                  multiple
                  value={priorityFilter}
                  onChange={handlePriorityFilterChange}
                  label="Priority"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {Object.values(Priority).map((priority) => (
                    <MenuItem key={priority} value={priority}>
                      {priority.toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <Tooltip title="Clear all filters">
                <IconButton onClick={clearFilters} color="primary">
                  <ClearIcon />
                </IconButton>
              </Tooltip>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Tickets Table */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={sortConfig.field === 'title'}
                    direction={sortConfig.field === 'title' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('title')}
                  >
                    Title
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortConfig.field === 'status'}
                    direction={sortConfig.field === 'status' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('status')}
                  >
                    Status
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortConfig.field === 'priority'}
                    direction={sortConfig.field === 'priority' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('priority')}
                  >
                    Priority
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortConfig.field === 'created_at'}
                    direction={sortConfig.field === 'created_at' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('created_at')}
                  >
                    Created
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sortConfig.field === 'updated_at'}
                    direction={sortConfig.field === 'updated_at' ? sortConfig.direction : 'asc'}
                    onClick={() => handleSort('updated_at')}
                  >
                    Updated
                  </TableSortLabel>
                </TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : tickets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      No tickets found
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                tickets.map((ticket) => (
                  <TableRow key={ticket.id} hover>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {ticket.title}
                        </Typography>
                        {ticket.description && (
                          <Typography variant="caption" color="text.secondary" noWrap>
                            {ticket.description.length > 50 
                              ? `${ticket.description.substring(0, 50)}...` 
                              : ticket.description}
                          </Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={ticket.status.replace('_', ' ').toUpperCase()}
                        color={getStatusColor(ticket.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={ticket.priority.toUpperCase()}
                        color={getPriorityColor(ticket.priority)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {format(new Date(ticket.created_at), 'MMM dd, yyyy HH:mm')}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {format(new Date(ticket.updated_at), 'MMM dd, yyyy HH:mm')}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Tooltip title="View ticket">
                        <IconButton
                          size="small"
                          onClick={() => handleViewTicket(ticket.id)}
                          color="primary"
                        >
                          <ViewIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          component="div"
          count={totalCount}
          page={page}
          onPageChange={handlePageChange}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={handleRowsPerPageChange}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </Paper>
    </Box>
  );
};

export default TicketList;