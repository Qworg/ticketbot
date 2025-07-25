import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TicketStatusManager from '../TicketStatusManager';
import { Ticket, TicketStatus, Priority } from '../../types';

const mockTicket: Ticket = {
  id: 'test-ticket-id',
  discord_channel_id: 123456789,
  title: 'Test Ticket',
  description: 'Test description',
  status: TicketStatus.OPEN,
  priority: Priority.MEDIUM,
  creator_discord_id: 987654321,
  assigned_staff_id: 111222333,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T11:00:00Z',
};

describe('TicketStatusManager', () => {
  it('renders current ticket status correctly', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    expect(screen.getByText('open')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
    expect(screen.getByText('Staff 111222333')).toBeInTheDocument();
  });

  it('renders status and priority selects with current values', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const statusSelect = screen.getByDisplayValue('open');
    const prioritySelect = screen.getByDisplayValue('medium');

    expect(statusSelect).toBeInTheDocument();
    expect(prioritySelect).toBeInTheDocument();
  });

  it('renders assigned staff ID input with current value', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const staffInput = screen.getByDisplayValue('111222333');
    expect(staffInput).toBeInTheDocument();
  });

  it('disables save button when no changes are made', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    expect(saveButton).toBeDisabled();
  });

  it('enables save button when changes are made', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);
    
    const inProgressOption = screen.getByText('IN_PROGRESS');
    fireEvent.click(inProgressOption);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    expect(saveButton).not.toBeDisabled();
  });

  it('calls onUpdateTicket with correct data when status is changed', async () => {
    const mockOnUpdateTicket = vi.fn().mockResolvedValue(undefined);
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);
    
    const inProgressOption = screen.getByText('IN_PROGRESS');
    fireEvent.click(inProgressOption);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnUpdateTicket).toHaveBeenCalledWith({
        status: TicketStatus.IN_PROGRESS,
        priority: Priority.MEDIUM,
        assigned_staff_id: 111222333,
      });
    });
  });

  it('calls onUpdateTicket with correct data when priority is changed', async () => {
    const mockOnUpdateTicket = vi.fn().mockResolvedValue(undefined);
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const prioritySelect = screen.getByLabelText('Priority');
    fireEvent.mouseDown(prioritySelect);
    
    const highOption = screen.getByText('HIGH');
    fireEvent.click(highOption);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnUpdateTicket).toHaveBeenCalledWith({
        status: TicketStatus.OPEN,
        priority: Priority.HIGH,
        assigned_staff_id: 111222333,
      });
    });
  });

  it('calls onUpdateTicket with correct data when staff assignment is changed', async () => {
    const mockOnUpdateTicket = vi.fn().mockResolvedValue(undefined);
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const staffInput = screen.getByLabelText('Assigned Staff ID');
    fireEvent.change(staffInput, { target: { value: '444555666' } });

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnUpdateTicket).toHaveBeenCalledWith({
        status: TicketStatus.OPEN,
        priority: Priority.MEDIUM,
        assigned_staff_id: 444555666,
      });
    });
  });

  it('handles empty staff assignment', async () => {
    const mockOnUpdateTicket = vi.fn().mockResolvedValue(undefined);
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const staffInput = screen.getByLabelText('Assigned Staff ID');
    fireEvent.change(staffInput, { target: { value: '' } });

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnUpdateTicket).toHaveBeenCalledWith({
        status: TicketStatus.OPEN,
        priority: Priority.MEDIUM,
        assigned_staff_id: undefined,
      });
    });
  });

  it('shows error message when update fails', async () => {
    const mockOnUpdateTicket = vi.fn().mockRejectedValue(new Error('Update failed'));
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);
    
    const inProgressOption = screen.getByText('IN_PROGRESS');
    fireEvent.click(inProgressOption);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Update failed')).toBeInTheDocument();
    });
  });

  it('disables all controls when disabled prop is true', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} disabled={true} />);

    const statusSelect = screen.getByLabelText('Status');
    const prioritySelect = screen.getByLabelText('Priority');
    const staffInput = screen.getByLabelText('Assigned Staff ID');
    const saveButton = screen.getByRole('button', { name: /save changes/i });

    expect(statusSelect).toBeDisabled();
    expect(prioritySelect).toBeDisabled();
    expect(staffInput).toBeDisabled();
    expect(saveButton).toBeDisabled();
  });

  it('shows loading state while updating', async () => {
    let resolvePromise: () => void;
    const mockOnUpdateTicket = vi.fn(() => new Promise<void>((resolve) => {
      resolvePromise = resolve;
    }));

    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);
    
    const inProgressOption = screen.getByText('IN_PROGRESS');
    fireEvent.click(inProgressOption);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    // Should show loading state
    expect(screen.getByText('Saving...')).toBeInTheDocument();
    expect(saveButton).toBeDisabled();

    // Resolve the promise
    resolvePromise!();

    await waitFor(() => {
      expect(screen.getByText('Save Changes')).toBeInTheDocument();
    });
  });

  it('renders ticket without assigned staff correctly', () => {
    const ticketWithoutStaff = { ...mockTicket, assigned_staff_id: undefined };
    const mockOnUpdateTicket = vi.fn();
    
    render(<TicketStatusManager ticket={ticketWithoutStaff} onUpdateTicket={mockOnUpdateTicket} />);

    // Should not show staff chip
    expect(screen.queryByText(/Staff/)).not.toBeInTheDocument();
    
    // Staff input should be empty
    const staffInput = screen.getByLabelText('Assigned Staff ID');
    expect((staffInput as HTMLInputElement).value).toBe('');
  });

  it('displays all status options in select', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);

    expect(screen.getByText('OPEN')).toBeInTheDocument();
    expect(screen.getByText('IN_PROGRESS')).toBeInTheDocument();
    expect(screen.getByText('WAITING')).toBeInTheDocument();
    expect(screen.getByText('CLOSED')).toBeInTheDocument();
    expect(screen.getByText('ARCHIVED')).toBeInTheDocument();
  });

  it('displays all priority options in select', () => {
    const mockOnUpdateTicket = vi.fn();
    render(<TicketStatusManager ticket={mockTicket} onUpdateTicket={mockOnUpdateTicket} />);

    const prioritySelect = screen.getByLabelText('Priority');
    fireEvent.mouseDown(prioritySelect);

    expect(screen.getByText('LOW')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('URGENT')).toBeInTheDocument();
  });
});