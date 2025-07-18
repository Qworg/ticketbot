import React from 'react';
import { Typography, Box, Paper } from '@mui/material';

const TranscriptSearch: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search Transcripts
      </Typography>
      
      <Paper sx={{ p: 2 }}>
        <Typography variant="body1" color="text.secondary">
          Transcript search functionality will be implemented in a future task.
        </Typography>
      </Paper>
    </Box>
  );
};

export default TranscriptSearch;