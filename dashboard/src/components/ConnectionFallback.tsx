/**
 * Connection fallback component for handling network connectivity issues.
 * 
 * This component provides a fallback UI when the application loses
 * connection to the backend or when network issues occur.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  WifiOff,
  Refresh,
  ExpandMore,
  ExpandLess,
  SignalWifiOff,
  Router,
  Cloud,
  Settings,
} from '@mui/icons-material';
import { useConnectionErrorHandler } from '../hooks/useErrorHandler';

interface ConnectionFallbackProps {
  onRetry?: () => Promise<void>;
  showDetails?: boolean;
  minimal?: boolean;
}

const ConnectionFallback: React.FC<ConnectionFallbackProps> = ({
  onRetry,
  showDetails = true,
  minimal = false,
}) => {
  const { isOnline, connectionError } = useConnectionErrorHandler();
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [showTroubleshooting, setShowTroubleshooting] = useState(false);
  const [lastRetryTime, setLastRetryTime] = useState<Date | null>(null);

  const handleRetry = async () => {
    if (isRetrying) return;

    setIsRetrying(true);
    setRetryCount(prev => prev + 1);
    setLastRetryTime(new Date());

    try {
      if (onRetry) {
        await onRetry();
      } else {
        // Default retry: reload the page
        window.location.reload();
      }
    } catch (error) {
      console.error('Retry failed:', error);
    } finally {
      setIsRetrying(false);
    }
  };

  const getConnectionStatus = () => {
    if (!isOnline) {
      return {
        status: 'offline',
        message: 'No internet connection',
        color: 'error' as const,
        icon: <SignalWifiOff />,
      };
    } else if (connectionError) {
      return {
        status: 'server-error',
        message: 'Cannot connect to server',
        color: 'warning' as const,
        icon: <Cloud />,
      };
    } else {
      return {
        status: 'online',
        message: 'Connected',
        color: 'success' as const,
        icon: <Router />,
      };
    }
  };

  const connectionStatus = getConnectionStatus();

  // Minimal version for inline use
  if (minimal) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1 }}>
        <WifiOff color="error" fontSize="small" />
        <Typography variant="body2" color="error">
          Connection lost
        </Typography>
        <Button
          size="small"
          variant="outlined"
          onClick={handleRetry}
          disabled={isRetrying}
          startIcon={isRetrying ? <CircularProgress size={16} /> : <Refresh />}
        >
          Retry
        </Button>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        padding: 3,
        textAlign: 'center',
      }}
    >
      <Card sx={{ maxWidth: 600, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          {/* Connection Status */}
          <Box sx={{ mb: 3 }}>
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 80,
                height: 80,
                borderRadius: '50%',
                backgroundColor: `${connectionStatus.color}.light`,
                color: `${connectionStatus.color}.main`,
                mb: 2,
              }}
            >
              {React.cloneElement(connectionStatus.icon, { sx: { fontSize: 40 } })}
            </Box>
            
            <Typography variant="h5" gutterBottom>
              Connection Problem
            </Typography>
            
            <Chip
              label={connectionStatus.message}
              color={connectionStatus.color}
              variant="outlined"
              sx={{ mb: 2 }}
            />
          </Box>

          {/* Error Message */}
          <Alert severity={connectionStatus.color} sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="body1" gutterBottom>
              {!isOnline
                ? 'Your device is not connected to the internet. Please check your network connection.'
                : 'Unable to connect to the server. This might be a temporary issue.'}
            </Typography>
            
            {retryCount > 0 && (
              <Typography variant="body2" color="text.secondary">
                Retry attempts: {retryCount}
                {lastRetryTime && (
                  <> • Last attempt: {lastRetryTime.toLocaleTimeString()}</>
                )}
              </Typography>
            )}
          </Alert>

          {/* Retry Button */}
          <Box sx={{ mb: 3 }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleRetry}
              disabled={isRetrying}
              startIcon={isRetrying ? <CircularProgress size={20} /> : <Refresh />}
              sx={{ minWidth: 140 }}
            >
              {isRetrying ? 'Retrying...' : 'Try Again'}
            </Button>
          </Box>

          {/* Progress indicator during retry */}
          {isRetrying && (
            <Box sx={{ mb: 3 }}>
              <LinearProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Attempting to reconnect...
              </Typography>
            </Box>
          )}

          {/* Troubleshooting Section */}
          {showDetails && (
            <Box>
              <Button
                variant="text"
                onClick={() => setShowTroubleshooting(!showTroubleshooting)}
                endIcon={showTroubleshooting ? <ExpandLess /> : <ExpandMore />}
                sx={{ mb: 2 }}
              >
                Troubleshooting Tips
              </Button>

              <Collapse in={showTroubleshooting}>
                <Alert severity="info" sx={{ textAlign: 'left' }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Try these steps:
                  </Typography>
                  <Box component="ul" sx={{ pl: 2, m: 0 }}>
                    <li>Check your internet connection</li>
                    <li>Refresh the page or restart your browser</li>
                    <li>Disable VPN or proxy if you're using one</li>
                    <li>Check if the server is under maintenance</li>
                    <li>Try accessing the site from a different device</li>
                    <li>Contact support if the problem persists</li>
                  </Box>
                  
                  <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => window.location.reload()}
                      startIcon={<Refresh />}
                    >
                      Reload Page
                    </Button>
                    
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => {
                        if ('serviceWorker' in navigator) {
                          navigator.serviceWorker.getRegistrations().then(registrations => {
                            registrations.forEach(registration => registration.unregister());
                          });
                        }
                        localStorage.clear();
                        sessionStorage.clear();
                        window.location.reload();
                      }}
                      startIcon={<Settings />}
                    >
                      Clear Cache
                    </Button>
                  </Box>
                </Alert>
              </Collapse>
            </Box>
          )}

          {/* Additional Actions */}
          <Box sx={{ mt: 3, display: 'flex', gap: 1, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Button
              variant="text"
              onClick={() => window.open('https://downdetector.com', '_blank')}
            >
              Check Service Status
            </Button>
            
            <Button
              variant="text"
              onClick={() => {
                const subject = encodeURIComponent('Connection Issue Report');
                const body = encodeURIComponent(
                  `I'm experiencing connection issues with the Discord Ticket Dashboard.\n\n` +
                  `Details:\n` +
                  `- Online status: ${isOnline ? 'Online' : 'Offline'}\n` +
                  `- Error: ${connectionError?.message || 'None'}\n` +
                  `- Retry attempts: ${retryCount}\n` +
                  `- Timestamp: ${new Date().toISOString()}\n` +
                  `- User Agent: ${navigator.userAgent}\n` +
                  `- URL: ${window.location.href}`
                );
                window.open(`mailto:support@example.com?subject=${subject}&body=${body}`);
              }}
            >
              Contact Support
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ConnectionFallback;