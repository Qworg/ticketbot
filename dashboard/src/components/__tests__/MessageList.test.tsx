import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import MessageList from '../MessageList';
import { Message, MessageType } from '../../types';

const mockMessages: Message[] = [
  {
    id: 'msg-1',
    ticket_id: 'ticket-1',
    discord_message_id: 123456,
    author_discord_id: 987654321,
    content: 'Hello, I need help',
    message_type: MessageType.USER_MESSAGE,
    created_at: '2024-01-01T10:00:00Z',
  },
  {
    id: 'msg-2',
    ticket_id: 'ticket-1',
    discord_message_id: 123457,
    author_discord_id: 111222333,
    content: 'Hi! How can I help you?',
    message_type: MessageType.STAFF_MESSAGE,
    created_at: '2024-01-01T10:05:00Z',
  },
  {
    id: 'msg-3',
    ticket_id: 'ticket-1',
    author_discord_id: 0,
    content: 'Ticket created automatically',
    message_type: MessageType.SYSTEM_MESSAGE,
    created_at: '2024-01-01T09:55:00Z',
  },
];

describe('MessageList', () => {
  it('renders messages correctly', () => {
    render(<MessageList messages={mockMessages} />);

    expect(screen.getByText('Hello, I need help')).toBeInTheDocument();
    expect(screen.getByText('Hi! How can I help you?')).toBeInTheDocument();
    expect(screen.getByText('Ticket created automatically')).toBeInTheDocument();
  });

  it('displays message types correctly', () => {
    render(<MessageList messages={mockMessages} />);

    expect(screen.getByText('User')).toBeInTheDocument();
    expect(screen.getByText('Staff')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
  });

  it('displays author information', () => {
    render(<MessageList messages={mockMessages} />);

    expect(screen.getByText('User 987654321')).toBeInTheDocument();
    expect(screen.getByText('User 111222333')).toBeInTheDocument();
    expect(screen.getByText('User 0')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<MessageList messages={[]} loading={true} />);

    expect(screen.getByText('Loading messages...')).toBeInTheDocument();
  });

  it('shows empty state when no messages', () => {
    render(<MessageList messages={[]} />);

    expect(screen.getByText('No messages yet. Start the conversation!')).toBeInTheDocument();
  });

  it('displays timestamps', () => {
    render(<MessageList messages={mockMessages} />);

    // Should show relative time (e.g., "3 years ago")
    expect(screen.getAllByText(/ago/)).toHaveLength(3);
  });

  it('handles multiline content', () => {
    const multilineMessage: Message = {
      id: 'msg-multiline',
      ticket_id: 'ticket-1',
      author_discord_id: 123456789,
      content: 'Line 1\nLine 2\nLine 3',
      message_type: MessageType.USER_MESSAGE,
      created_at: '2024-01-01T10:00:00Z',
    };

    render(<MessageList messages={[multilineMessage]} />);

    expect(screen.getByText('Line 1\nLine 2\nLine 3')).toBeInTheDocument();
  });

  it('applies different styling for staff messages', () => {
    render(<MessageList messages={mockMessages} />);

    const staffMessage = screen.getByText('Hi! How can I help you?').closest('[class*="MuiPaper-root"]');
    const userMessage = screen.getByText('Hello, I need help').closest('[class*="MuiPaper-root"]');

    // Staff messages should have different background
    expect(staffMessage).toHaveStyle({ backgroundColor: expect.any(String) });
    expect(userMessage).toHaveStyle({ backgroundColor: expect.any(String) });
  });

  it('displays bot message type correctly', () => {
    const botMessage: Message = {
      id: 'msg-bot',
      ticket_id: 'ticket-1',
      author_discord_id: 123456789,
      content: 'Bot response',
      message_type: MessageType.BOT_MESSAGE,
      created_at: '2024-01-01T10:00:00Z',
    };

    render(<MessageList messages={[botMessage]} />);

    expect(screen.getByText('Bot')).toBeInTheDocument();
  });
});