import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MessageInput from '../MessageInput';

describe('MessageInput', () => {
  it('renders input field and send button', () => {
    const mockOnSendMessage = vi.fn();
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('enables send button when message is typed', () => {
    const mockOnSendMessage = vi.fn();
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    expect(sendButton).toBeDisabled();

    fireEvent.change(input, { target: { value: 'Test message' } });
    expect(sendButton).not.toBeDisabled();
  });

  it('calls onSendMessage when form is submitted', async () => {
    const mockOnSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
    });
  });

  it('clears input after successful send', async () => {
    const mockOnSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...') as HTMLInputElement;
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(input.value).toBe('');
    });
  });

  it('trims whitespace from message', async () => {
    const mockOnSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: '  Test message  ' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
    });
  });

  it('does not send empty or whitespace-only messages', () => {
    const mockOnSendMessage = vi.fn();
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    // Test empty message
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();

    // Test whitespace-only message
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(sendButton);
    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it('shows error message when send fails', async () => {
    const mockOnSendMessage = vi.fn().mockRejectedValue(new Error('Send failed'));
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText('Send failed')).toBeInTheDocument();
    });
  });

  it('disables input and button when disabled prop is true', () => {
    const mockOnSendMessage = vi.fn();
    render(<MessageInput onSendMessage={mockOnSendMessage} disabled={true} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    expect(input).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('disables input and button while sending', async () => {
    let resolvePromise: () => void;
    const mockOnSendMessage = vi.fn(() => new Promise<void>((resolve) => {
      resolvePromise = resolve;
    }));

    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    // Should be disabled while sending
    expect(input).toBeDisabled();
    expect(sendButton).toBeDisabled();

    // Resolve the promise
    resolvePromise!();

    await waitFor(() => {
      expect(input).not.toBeDisabled();
      expect(sendButton).toBeDisabled(); // Still disabled because input is now empty
    });
  });

  it('supports multiline input', () => {
    const mockOnSendMessage = vi.fn();
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');
    
    fireEvent.change(input, { target: { value: 'Line 1\nLine 2' } });
    
    expect((input as HTMLTextAreaElement).value).toBe('Line 1\nLine 2');
  });

  it('submits form on Enter key press', async () => {
    const mockOnSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith('Test message');
    });
  });

  it('does not submit on Shift+Enter', () => {
    const mockOnSendMessage = vi.fn();
    render(<MessageInput onSendMessage={mockOnSendMessage} />);

    const input = screen.getByPlaceholderText('Type your message...');

    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', shiftKey: true });

    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });
});