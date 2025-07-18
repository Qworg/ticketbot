import React from 'react';
import { Typography, Box, Grid, Paper } from '@mui/material';

const Dashboard: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="primary">
              Active Tickets
            </Typography>
            <Typography variant="h3" sx={{ mt: 2 }}>
              0
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="primary">
              Assigned to Me
            </Typography>
            <Typography variant="h3" sx={{ mt: 2 }}>
              0
            </Typography>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', height: 140 }}>
            <Typography variant="h6" color="primary">
              Closed Today
            </Typography>
            <Typography variant="h3" sx={{ mt: 2 }}>
              0
            </Typography>
          </Paper>
        </Grid>
      </Grid>
      
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Recent Activity
        </Typography>
        <Paper sx={{ p: 2 }}>
          <Typography variant="body1" color="text.secondary">
            No recent activity to display.
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
};

export default Dashboard;