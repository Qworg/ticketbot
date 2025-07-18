import React from 'react';
import { Typography, Box, Paper } from '@mui/material';

const TicketList: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Tickets
      </Typography>
      
      <Paper sx={{ p: 2 }}>
        <Typography variant="body1" color="text.secondary">
          No tickets available. Ticket list will be implemented in a future task.
        </Typography>
      </Paper>
    </Box>
  );
};

export default TicketList;