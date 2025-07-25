import React from 'react';
import { Box, Typography, Paper, Avatar, Chip } from '@mui/material';
import { Message, MessageType } from '../types';
import { formatDistanceToNow } from 'date-fns';

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ messages, loading = false }) => {
  const getMessageTypeColor = (type: MessageType) => {
    switch (type) {
      case MessageType.STAFF_MESSAGE:
        return 'primary';
      case MessageType.USER_MESSAGE:
        return 'default';
      case MessageType.SYSTEM_MESSAGE:
        return 'warning';
      case MessageType.BOT_MESSAGE:
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getMessageTypeLabel = (type: MessageType) => {
    switch (type) {
      case MessageType.STAFF_MESSAGE:
        return 'Staff';
      case MessageType.USER_MESSAGE:
        return 'User';
      case MessageType.SYSTEM_MESSAGE:
        return 'System';
      case MessageType.BOT_MESSAGE:
        return 'Bot';
      default:
        return 'Unknown';
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Loading messages...
        </Typography>
      </Box>
    );
  }

  if (messages.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No messages yet. Start the conversation!
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxHeight: '400px', overflowY: 'auto', p: 1 }}>
      {messages.map((message) => (
        <Paper
          key={message.id}
          elevation={1}
          sx={{
            p: 2,
            mb: 1,
            backgroundColor: message.message_type === MessageType.STAFF_MESSAGE 
              ? 'action.hover' 
              : 'background.paper'
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
            <Avatar sx={{ width: 32, height: 32 }}>
              {message.author_discord_id.toString().slice(-2)}
            </Avatar>
            
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="subtitle2" fontWeight="bold">
                  User {message.author_discord_id}
                </Typography>
                <Chip
                  label={getMessageTypeLabel(message.message_type)}
                  size="small"
                  color={getMessageTypeColor(message.message_type)}
                  variant="outlined"
                />
                <Typography variant="caption" color="text.secondary">
                  {formatDistanceToNow(new Date(message.created_at), { addSuffix: true })}
                </Typography>
              </Box>
              
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {message.content}
              </Typography>
            </Box>
          </Box>
        </Paper>
      ))}
    </Box>
  );
};

export default MessageList;