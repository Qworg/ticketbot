import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
  Divider,
} from '@mui/material';
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { Ticket, Message } from '../types';
import { ticketService } from '../services/ticketService';
import { messageService } from '../services/messageService';
import { useWebSocket } from '../hooks/useWebSocket';
import MessageList from '../components/MessageList';
import MessageInput from '../components/MessageInput';
import TicketStatusManager from '../components/TicketStatusManager';

const TicketDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { subscribe } = useWebSocket();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load ticket data
  const loadTicket = useCallback(async () => {
    if (!id) return;

    try {
      setLoading(true);
      setError(null);
      const response = await ticketService.getTicket(id);
      setTicket(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ticket');
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Load messages
  const loadMessages = useCallback(async () => {
    if (!id) return;

    try {
      setMessagesLoading(true);
      const response = await messageService.getTicketMessages(id, {
        sort_order: 'asc',
        per_page: 100,
      });
      setMessages(response.data);
    } catch (err) {
      console.error('Failed to load messages:', err);
    } finally {
      setMessagesLoading(false);
    }
  }, [id]);

  // Handle sending new messages
  const handleSendMessage = useCallback(async (content: string) => {
    if (!id) return;

    try {
      const response = await messageService.addMessage(id, content);
      setMessages(prev => [...prev, response.data]);
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to send message');
    }
  }, [id]);

  // Handle ticket updates
  const handleUpdateTicket = useCallback(async (updates: Partial<Ticket>) => {
    if (!id || !ticket) return;

    try {
      const response = await ticketService.updateTicket(id, updates);
      setTicket(response.data);
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to update ticket');
    }
  }, [id, ticket]);

  // Set up real-time subscriptions
  useEffect(() => {
    if (!id) return;

    const unsubscribeTicketUpdated = subscribe('ticket_updated', (data) => {
      if (data.id === id) {
        setTicket(data);
      }
    });

    const unsubscribeMessageAdded = subscribe('message_added', (data) => {
      if (data.ticket_id === id) {
        setMessages(prev => [...prev, data]);
      }
    });

    return () => {
      unsubscribeTicketUpdated();
      unsubscribeMessageAdded();
    };
  }, [id, subscribe]);

  // Load initial data
  useEffect(() => {
    loadTicket();
    loadMessages();
  }, [loadTicket, loadMessages]);

  if (!id) {
    return (
      <Box>
        <Alert severity="error">
          Invalid ticket ID
        </Alert>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error">
          {error}
        </Alert>
      </Box>
    );
  }

  if (!ticket) {
    return (
      <Box>
        <Alert severity="warning">
          Ticket not found
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/tickets')}
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          <ArrowBackIcon fontSize="small" />
          Tickets
        </Link>
        <Typography variant="body2" color="text.primary">
          {ticket.title}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Typography variant="h4" gutterBottom>
        {ticket.title}
      </Typography>

      <Grid container spacing={3}>
        {/* Main Content */}
        <Grid item xs={12} md={8}>
          {/* Ticket Info */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Ticket Information
              </Typography>
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Description
                </Typography>
                <Typography variant="body1">
                  {ticket.description || 'No description provided'}
                </Typography>
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Created
                  </Typography>
                  <Typography variant="body1">
                    {format(new Date(ticket.created_at), 'PPpp')}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Last Updated
                  </Typography>
                  <Typography variant="body1">
                    {format(new Date(ticket.updated_at), 'PPpp')}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Creator
                  </Typography>
                  <Typography variant="body1">
                    User {ticket.creator_discord_id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Discord Channel
                  </Typography>
                  <Typography variant="body1">
                    {ticket.discord_channel_id}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Messages */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Conversation
              </Typography>
              
              <MessageList messages={messages} loading={messagesLoading} />
              
              <Divider sx={{ my: 2 }} />
              
              <MessageInput
                onSendMessage={handleSendMessage}
                disabled={ticket.status === 'closed' || ticket.status === 'archived'}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} md={4}>
          <TicketStatusManager
            ticket={ticket}
            onUpdateTicket={handleUpdateTicket}
            disabled={ticket.status === 'archived'}
          />
        </Grid>
      </Grid>
    </Box>
  );
};

export default TicketDetail;