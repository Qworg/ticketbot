import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Typography,
  Box,
  Paper,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Divider,
  Chip
} from '@mui/material';
import { format } from 'date-fns';
import { transcriptService } from '../services/transcriptService';
import { Transcript } from '../types';

const SharedTranscript: React.FC = () => {
  const { shareToken } = useParams();
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSharedTranscript = async () => {
      if (!shareToken) {
        setError('Invalid share token');
        setLoading(false);
        return;
      }

      try {
        const response = await transcriptService.getSharedTranscript(shareToken);
        setTranscript(response.data);
      } catch (err: any) {
        if (err.response?.status === 404) {
          setError('This transcript link has expired or is invalid');
        } else if (err.response?.status === 403) {
          setError('You do not have permission to view this transcript');
        } else {
          setError('Failed to load transcript');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchSharedTranscript();
  }, [shareToken]);

  const renderTranscriptContent = (content: string, formattedContent?: any) => {
    if (formattedContent && formattedContent.messages) {
      return (
        <Box>
          {formattedContent.messages.map((message: any, index: number) => (
            <Box key={index} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                  {message.author}
                </Typography>
                <Chip 
                  label={message.type} 
                  size="small" 
                  variant="outlined"
                  color={message.type === 'staff_message' ? 'primary' : 'default'}
                />
                <Typography variant="caption" color="text.secondary">
                  {format(new Date(message.timestamp), 'MMM dd, yyyy HH:mm')}
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ pl: 2, whiteSpace: 'pre-wrap' }}>
                {message.content}
              </Typography>
              {index < formattedContent.messages.length - 1 && (
                <Divider sx={{ mt: 2 }} />
              )}
            </Box>
          ))}
        </Box>
      );
    }

    // Fallback to plain text content
    return (
      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
        {content}
      </Typography>
    );
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4 }}>
        <Alert severity="error">
          {error}
        </Alert>
      </Box>
    );
  }

  if (!transcript) {
    return (
      <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4 }}>
        <Alert severity="warning">
          Transcript not found
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 2 }}>
      <Paper sx={{ p: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" gutterBottom>
            Shared Transcript
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Created: {format(new Date(transcript.created_at), 'MMM dd, yyyy HH:mm')}
          </Typography>
          {transcript.updated_at !== transcript.created_at && (
            <Typography variant="body2" color="text.secondary">
              Last updated: {format(new Date(transcript.updated_at), 'MMM dd, yyyy HH:mm')}
            </Typography>
          )}
        </Box>

        <Divider sx={{ mb: 3 }} />

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Conversation Transcript
            </Typography>
            {renderTranscriptContent(transcript.content, transcript.formatted_content)}
          </CardContent>
        </Card>

        <Box sx={{ mt: 3, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            This is a shared transcript. Some information may be redacted for privacy.
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default SharedTranscript;