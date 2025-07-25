import { format, formatDistanceToNow, parseISO } from 'date-fns';
import { TicketStatus, Priority } from '@/types';

export const formatDate = (dateString: string): string => {
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM dd, yyyy HH:mm');
  } catch {
    return 'Invalid date';
  }
};

export const formatRelativeTime = (dateString: string): string => {
  try {
    const date = parseISO(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
};

export const getStatusColor = (status: TicketStatus): string => {
  switch (status) {
    case TicketStatus.OPEN:
      return '#4caf50'; // green
    case TicketStatus.IN_PROGRESS:
      return '#ff9800'; // orange
    case TicketStatus.WAITING:
      return '#2196f3'; // blue
    case TicketStatus.CLOSED:
      return '#9e9e9e'; // grey
    case TicketStatus.ARCHIVED:
      return '#607d8b'; // blue grey
    default:
      return '#9e9e9e';
  }
};

export const getPriorityColor = (priority: Priority): string => {
  switch (priority) {
    case Priority.LOW:
      return '#4caf50'; // green
    case Priority.MEDIUM:
      return '#ff9800'; // orange
    case Priority.HIGH:
      return '#f44336'; // red
    case Priority.URGENT:
      return '#e91e63'; // pink
    default:
      return '#9e9e9e';
  }
};

export const formatStatusLabel = (status: TicketStatus): string => {
  return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
};

export const formatPriorityLabel = (priority: Priority): string => {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
};