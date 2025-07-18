import React from 'react';
import { Outlet } from 'react-router-dom';
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#5865F2', // Discord blue
    },
    secondary: {
      main: '#EB459E', // Discord pink
    },
  },
});

const Layout: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        <Navbar />
        <Sidebar />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            overflow: 'auto',
            backgroundColor: (theme) => theme.palette.background.default,
          }}
        >
          <Box sx={{ height: 64 }} /> {/* Toolbar spacer */}
          <Outlet />
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default Layout;