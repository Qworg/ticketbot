/**
 * Notification container component for displaying user notifications.
 * 
 * This component renders notifications from the notification service
 * and provides user interaction capabilities.
 */

import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  Button,
  Box,
  Slide,
  SlideProps,
  IconButton,
  Collapse,
} from '@mui/material';
import { Close, ExpandMore, ExpandLess } from '@mui/icons-material';
import { TransitionProps } from '@mui/material/transitions';
import { Notification, NotificationType, notificationService } from '../services/notificationService';

// Slide transition component
function SlideTransition(props: SlideProps) {
  return <Slide {...props} direction="up" />;
}

interface NotificationItemProps {
  notification: Notification;
  onClose: (id: string) => void;
}

const NotificationItem: React.FC<NotificationItemProps> = ({ notification, onClose }) => {
  const [expanded, setExpanded] = useState(false);
  const [open, setOpen] = useState(true);

  const handleClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setOpen(false);
  };

  const handleExited = () => {
    onClose(notification.id);
  };

  const handleActionClick = (action: () => void) => {
    action();
    if (!notification.persistent) {
      handleClose();
    }
  };

  const getSeverity = (): 'success' | 'info' | 'warning' | 'error' => {
    switch (notification.type) {
      case NotificationType.SUCCESS:
        return 'success';
      case NotificationType.INFO:
        return 'info';
      case NotificationType.WARNING:
        return 'warning';
      case NotificationType.ERROR:
        return 'error';
      default:
        return 'info';
    }
  };

  const shouldAutoHide = !notification.persistent && notification.duration !== undefined;

  return (
    <Snackbar
      open={open}
      autoHideDuration={shouldAutoHide ? notification.duration : null}
      onClose={handleClose}
      TransitionComponent={SlideTransition}
      TransitionProps={{
        onExited: handleExited,
      } as TransitionProps}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      sx={{ position: 'relative', zIndex: 1400 }}
    >
      <Alert
        severity={getSeverity()}
        variant="filled"
        sx={{
          minWidth: 300,
          maxWidth: 500,
          '& .MuiAlert-message': {
            width: '100%',
          },
        }}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {notification.message.length > 100 && (
              <IconButton
                size="small"
                color="inherit"
                onClick={() => setExpanded(!expanded)}
                aria-label="expand notification"
              >
                {expanded ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            )}
            <IconButton
              size="small"
              color="inherit"
              onClick={handleClose}
              aria-label="close notification"
            >
              <Close fontSize="small" />
            </IconButton>
          </Box>
        }
      >
        <AlertTitle>{notification.title}</AlertTitle>
        
        <Collapse in={expanded || notification.message.length <= 100}>
          <Box sx={{ mb: notification.actions ? 1 : 0 }}>
            {notification.message}
          </Box>
        </Collapse>

        {!expanded && notification.message.length > 100 && (
          <Box sx={{ mb: notification.actions ? 1 : 0 }}>
            {notification.message.substring(0, 100)}...
          </Box>
        )}

        {notification.actions && notification.actions.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
            {notification.actions.map((action, index) => (
              <Button
                key={index}
                size="small"
                variant={action.variant || 'text'}
                color="inherit"
                onClick={() => handleActionClick(action.action)}
                sx={{
                  color: 'inherit',
                  borderColor: 'currentColor',
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                {action.label}
              </Button>
            ))}
          </Box>
        )}
      </Alert>
    </Snackbar>
  );
};

const NotificationContainer: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    // Subscribe to notification changes
    const unsubscribe = notificationService.addListener(setNotifications);
    
    // Get initial notifications
    setNotifications(notificationService.getNotifications());

    return unsubscribe;
  }, []);

  const handleNotificationClose = (id: string) => {
    notificationService.removeNotification(id);
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 1400,
        pointerEvents: 'none',
        '& > *': {
          pointerEvents: 'auto',
          mb: 1,
        },
      }}
    >
      {notifications.map((notification) => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onClose={handleNotificationClose}
        />
      ))}
    </Box>
  );
};

export default NotificationContainer;