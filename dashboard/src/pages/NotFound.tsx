import React from 'react';
import { Typography, Box, Button } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

const NotFound: React.FC = () => {
  return (
    <Box sx={{ textAlign: 'center', mt: 8 }}>
      <Typography variant="h1" component="h1" gutterBottom>
        404
      </Typography>
      <Typography variant="h4" component="h2" gutterBottom>
        Page Not Found
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        The page you are looking for does not exist.
      </Typography>
      <Button 
        variant="contained" 
        component={RouterLink} 
        to="/"
      >
        Back to Dashboard
      </Button>
    </Box>
  );
};

export default NotFound;