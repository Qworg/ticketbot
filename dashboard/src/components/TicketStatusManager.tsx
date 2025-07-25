import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Chip,
  Alert,
  TextField,
} from '@mui/material';
import { Save as SaveIcon, Person as PersonIcon } from '@mui/icons-material';
import { Ticket, TicketStatus, Priority } from '../types';

interface TicketStatusManagerProps {
  ticket: Ticket;
  onUpdateTicket: (updates: Partial<Ticket>) => Promise<void>;
  disabled?: boolean;
}

const TicketStatusManager: React.FC<TicketStatusManagerProps> = ({
  ticket,
  onUpdateTicket,
  disabled = false,
}) => {
  const [status, setStatus] = useState(ticket.status);
  const [priority, setPriority] = useState(ticket.priority);
  const [assignedStaffId, setAssignedStaffId] = useState(ticket.assigned_staff_id || '');
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasChanges = 
    status !== ticket.status ||
    priority !== ticket.priority ||
    assignedStaffId !== (ticket.assigned_staff_id?.toString() || '');

  const handleSave = async () => {
    if (!hasChanges || updating) return;

    setUpdating(true);
    setError(null);

    try {
      const updates: Partial<Ticket> = {
        status,
        priority,
        assigned_staff_id: assignedStaffId ? parseInt(assignedStaffId) : undefined,
      };

      await onUpdateTicket(updates);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update ticket');
    } finally {
      setUpdating(false);
    }
  };

  const getStatusColor = (status: TicketStatus) => {
    switch (status) {
      case TicketStatus.OPEN:
        return 'success';
      case TicketStatus.IN_PROGRESS:
        return 'primary';
      case TicketStatus.WAITING:
        return 'warning';
      case TicketStatus.CLOSED:
        return 'default';
      case TicketStatus.ARCHIVED:
        return 'default';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority: Priority) => {
    switch (priority) {
      case Priority.LOW:
        return 'success';
      case Priority.MEDIUM:
        return 'primary';
      case Priority.HIGH:
        return 'warning';
      case Priority.URGENT:
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Ticket Management
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Current Status Display */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Current Status
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip
                label={ticket.status}
                color={getStatusColor(ticket.status)}
                variant="filled"
              />
              <Chip
                label={ticket.priority}
                color={getPriorityColor(ticket.priority)}
                variant="outlined"
              />
              {ticket.assigned_staff_id && (
                <Chip
                  icon={<PersonIcon />}
                  label={`Staff ${ticket.assigned_staff_id}`}
                  variant="outlined"
                />
              )}
            </Box>
          </Box>

          {/* Status Controls */}
          <FormControl fullWidth size="small">
            <InputLabel>Status</InputLabel>
            <Select
              value={status}
              label="Status"
              onChange={(e) => setStatus(e.target.value as TicketStatus)}
              disabled={disabled || updating}
            >
              {Object.values(TicketStatus).map((statusOption) => (
                <MenuItem key={statusOption} value={statusOption}>
                  {statusOption.replace('_', ' ').toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small">
            <InputLabel>Priority</InputLabel>
            <Select
              value={priority}
              label="Priority"
              onChange={(e) => setPriority(e.target.value as Priority)}
              disabled={disabled || updating}
            >
              {Object.values(Priority).map((priorityOption) => (
                <MenuItem key={priorityOption} value={priorityOption}>
                  {priorityOption.toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            size="small"
            label="Assigned Staff ID"
            type="number"
            value={assignedStaffId}
            onChange={(e) => setAssignedStaffId(e.target.value)}
            disabled={disabled || updating}
            placeholder="Enter staff Discord ID"
          />

          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={!hasChanges || disabled || updating}
            fullWidth
          >
            {updating ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default TicketStatusManager;