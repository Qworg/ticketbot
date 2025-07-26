/**
 * Error Boundary component for catching and handling React errors.
 * 
 * This component provides comprehensive error handling for the React application,
 * including error boundaries, fallback UI, and error reporting.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button, Alert, Collapse, IconButton } from '@mui/material';
import { ExpandMore, ExpandLess, Refresh, Home, BugReport } from '@mui/icons-material';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
  retryCount: number;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  maxRetries?: number;
  showErrorDetails?: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryTimeoutId: NodeJS.Timeout | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      retryCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Update state with error info
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Report error to monitoring service (if available)
    this.reportError(error, errorInfo);
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // Here you would typically send the error to a monitoring service
    // like Sentry, LogRocket, or your own error reporting endpoint
    
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    // Example: Send to your error reporting endpoint
    try {
      fetch('/api/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(errorReport),
      }).catch(() => {
        // Silently fail if error reporting fails
      });
    } catch {
      // Silently fail if error reporting fails
    }
  };

  private handleRetry = () => {
    const { maxRetries = 3 } = this.props;
    const { retryCount } = this.state;

    if (retryCount < maxRetries) {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        showDetails: false,
        retryCount: retryCount + 1,
      });
    }
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/';
  };

  private toggleDetails = () => {
    this.setState(prevState => ({
      showDetails: !prevState.showDetails,
    }));
  };

  render() {
    const { hasError, error, errorInfo, showDetails, retryCount } = this.state;
    const { children, fallback, maxRetries = 3, showErrorDetails = true } = this.props;

    if (hasError) {
      // Custom fallback UI if provided
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '50vh',
            padding: 3,
            textAlign: 'center',
          }}
        >
          <Alert
            severity="error"
            sx={{ mb: 3, maxWidth: 600 }}
            action={
              showErrorDetails && (
                <IconButton
                  color="inherit"
                  size="small"
                  onClick={this.toggleDetails}
                  aria-label="toggle error details"
                >
                  {showDetails ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              )
            }
          >
            <Typography variant="h6" gutterBottom>
              Something went wrong
            </Typography>
            <Typography variant="body2">
              An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
            </Typography>
          </Alert>

          {showErrorDetails && (
            <Collapse in={showDetails} sx={{ width: '100%', maxWidth: 800, mb: 3 }}>
              <Alert severity="info" sx={{ textAlign: 'left' }}>
                <Typography variant="subtitle2" gutterBottom>
                  Error Details:
                </Typography>
                <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem', mb: 1 }}>
                  {error?.message}
                </Typography>
                {error?.stack && (
                  <>
                    <Typography variant="subtitle2" gutterBottom>
                      Stack Trace:
                    </Typography>
                    <Typography
                      variant="body2"
                      component="pre"
                      sx={{
                        fontSize: '0.7rem',
                        maxHeight: 200,
                        overflow: 'auto',
                        backgroundColor: 'rgba(0, 0, 0, 0.05)',
                        padding: 1,
                        borderRadius: 1,
                      }}
                    >
                      {error.stack}
                    </Typography>
                  </>
                )}
                {errorInfo?.componentStack && (
                  <>
                    <Typography variant="subtitle2" gutterBottom sx={{ mt: 1 }}>
                      Component Stack:
                    </Typography>
                    <Typography
                      variant="body2"
                      component="pre"
                      sx={{
                        fontSize: '0.7rem',
                        maxHeight: 150,
                        overflow: 'auto',
                        backgroundColor: 'rgba(0, 0, 0, 0.05)',
                        padding: 1,
                        borderRadius: 1,
                      }}
                    >
                      {errorInfo.componentStack}
                    </Typography>
                  </>
                )}
              </Alert>
            </Collapse>
          )}

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
            {retryCount < maxRetries && (
              <Button
                variant="contained"
                color="primary"
                startIcon={<Refresh />}
                onClick={this.handleRetry}
              >
                Try Again ({maxRetries - retryCount} attempts left)
              </Button>
            )}
            
            <Button
              variant="outlined"
              color="primary"
              startIcon={<Refresh />}
              onClick={this.handleReload}
            >
              Reload Page
            </Button>
            
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<Home />}
              onClick={this.handleGoHome}
            >
              Go Home
            </Button>
            
            {showErrorDetails && (
              <Button
                variant="text"
                color="info"
                startIcon={<BugReport />}
                onClick={() => {
                  const subject = encodeURIComponent('Error Report: ' + (error?.message || 'Unknown Error'));
                  const body = encodeURIComponent(
                    `Error: ${error?.message}\n\nStack: ${error?.stack}\n\nURL: ${window.location.href}\n\nTimestamp: ${new Date().toISOString()}`
                  );
                  window.open(`mailto:support@example.com?subject=${subject}&body=${body}`);
                }}
              >
                Report Issue
              </Button>
            )}
          </Box>

          {retryCount > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2 }}>
              Retry attempt: {retryCount}/{maxRetries}
            </Typography>
          )}
        </Box>
      );
    }

    return children;
  }
}

export default ErrorBoundary;

// Higher-order component for wrapping components with error boundary
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WithErrorBoundaryComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  WithErrorBoundaryComponent.displayName = `withErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name})`;

  return WithErrorBoundaryComponent;
}

// Hook for manually triggering error boundary
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    // This will trigger the nearest error boundary
    throw error;
  };
}