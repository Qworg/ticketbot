import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box } from '@mui/material';

const Navbar: React.FC = () => {
  return (
    <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar>
        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
          Discord Ticket Bot
        </Typography>
        <Box>
          {/* Add user profile, notifications, etc. here */}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;