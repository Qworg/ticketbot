import React from 'react';
import { useParams } from 'react-router-dom';
import { Typography, Box, Paper } from '@mui/material';

const TicketDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Ticket Details
      </Typography>
      
      <Paper sx={{ p: 2 }}>
        <Typography variant="body1">
          Viewing ticket ID: {id}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Ticket details will be implemented in a future task.
        </Typography>
      </Paper>
    </Box>
  );
};

export default TicketDetail;