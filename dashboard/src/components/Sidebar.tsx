import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
} from '@mui/material';

// Placeholder icons (replace with actual MUI icons in implementation)
const DashboardIcon = () => <span>📊</span>;
const TicketsIcon = () => <span>🎫</span>;
const SearchIcon = () => <span>🔍</span>;

const drawerWidth = 240;

const Sidebar: React.FC = () => {
  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
      }}
    >
      <Toolbar />
      <List>
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/">
            <ListItemIcon>
              <DashboardIcon />
            </ListItemIcon>
            <ListItemText primary="Dashboard" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/tickets">
            <ListItemIcon>
              <TicketsIcon />
            </ListItemIcon>
            <ListItemText primary="Tickets" />
          </ListItemButton>
        </ListItem>
        
        <ListItem disablePadding>
          <ListItemButton component={RouterLink} to="/search">
            <ListItemIcon>
              <SearchIcon />
            </ListItemIcon>
            <ListItemText primary="Search Transcripts" />
          </ListItemButton>
        </ListItem>
      </List>
      <Divider />
    </Drawer>
  );
};

export default Sidebar;