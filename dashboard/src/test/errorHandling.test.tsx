/**
 * Tests for frontend error handling functionality.
 * 
 * This module tests the comprehensive error handling system including
 * error boundaries, error services, notifications, and hooks.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { AxiosError } from 'axios';

import ErrorBoundary, { withErrorBoundary } from '../components/ErrorBoundary';
import NotificationContainer from '../components/NotificationContainer';
import ConnectionFallback from '../components/ConnectionFallback';
import { errorService, ErrorType, ErrorSeverity } from '../services/errorService';
import { notificationService, NotificationType } from '../services/notificationService';
import { useErrorHandler, useConnectionErrorHandler, useFormErrorHandler } from '../hooks/useErrorHandler';

// Mock components for testing
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({ 
  shouldThrow = false, 
  errorMessage = 'Test error' 
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div>No error</div>;
};

const TestComponent: React.FC = () => {
  const { error, isRetrying, handleError, retry, clearError, withErrorHandling } = useErrorHandler({
    showNotifications: false, // Disable for testing
  });

  const testOperation = withErrorHandling(async () => {
    throw new Error('Test operation error');
  }, 'test-operation');

  return (
    <div>
      <div data-testid="error-state">
        {error ? error.message : 'No error'}
      </div>
      <div data-testid="retry-state">
        {isRetrying ? 'Retrying' : 'Not retrying'}
      </div>
      <button onClick={() => handleError(new Error('Manual error'))}>
        Trigger Error
      </button>
      <button onClick={testOperation}>
        Test Operation
      </button>
      <button onClick={retry}>
        Retry
      </button>
      <button onClick={clearError}>
        Clear Error
      </button>
    </div>
  );
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console.error for error boundary tests
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should catch and display errors', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} errorMessage="Test boundary error" />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/An unexpected error occurred/)).toBeInTheDocument();
  });

  it('should render children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByText('No error')).toBeInTheDocument();
  });

  it('should show retry button and handle retries', async () => {
    const { rerender } = render(
      <ErrorBoundary maxRetries={2}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    const retryButton = screen.getByText(/Try Again/);
    expect(retryButton).toBeInTheDocument();

    // Click retry
    fireEvent.click(retryButton);

    // Should still show error after retry (since component still throws)
    await waitFor(() => {
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });
  });

  it('should show error details when expanded', async () => {
    render(
      <ErrorBoundary showErrorDetails={true}>
        <ThrowError shouldThrow={true} errorMessage="Detailed test error" />
      </ErrorBoundary>
    );

    const expandButton = screen.getByLabelText('toggle error details');
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText('Detailed test error')).toBeInTheDocument();
    });
  });

  it('should call custom error handler', () => {
    const onError = vi.fn();
    
    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} errorMessage="Custom handler test" />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
  });

  it('should render custom fallback', () => {
    const customFallback = <div>Custom error fallback</div>;
    
    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error fallback')).toBeInTheDocument();
  });
});

describe('withErrorBoundary HOC', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should wrap component with error boundary', () => {
    const WrappedComponent = withErrorBoundary(ThrowError);
    
    render(<WrappedComponent shouldThrow={true} />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should pass props to wrapped component', () => {
    const WrappedComponent = withErrorBoundary(ThrowError);
    
    render(<WrappedComponent shouldThrow={false} />);

    expect(screen.getByText('No error')).toBeInTheDocument();
  });
});

describe('ErrorService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should handle Axios errors correctly', () => {
    const axiosError = {
      name: 'AxiosError',
      message: 'Request failed',
      response: {
        status: 404,
        data: { error: { message: 'Not found' } },
        headers: { 'x-request-id': 'test-123' }
      },
      config: { url: '/api/test', method: 'get' }
    } as AxiosError;

    const appError = errorService.handleAxiosError(axiosError);

    expect(appError.type).toBe(ErrorType.NOT_FOUND_ERROR);
    expect(appError.statusCode).toBe(404);
    expect(appError.requestId).toBe('test-123');
    expect(appError.userMessage).toContain('not found');
  });

  it('should handle network errors', () => {
    const networkError = {
      name: 'AxiosError',
      message: 'Network Error',
      request: {},
      response: undefined
    } as AxiosError;

    const appError = errorService.handleAxiosError(networkError);

    expect(appError.type).toBe(ErrorType.NETWORK_ERROR);
    expect(appError.retryable).toBe(true);
    expect(appError.userMessage).toContain('connect to the server');
  });

  it('should handle generic errors', () => {
    const genericError = new Error('Generic test error');
    const context = { operation: 'test' };

    const appError = errorService.handleGenericError(genericError, context);

    expect(appError.type).toBe(ErrorType.UNKNOWN_ERROR);
    expect(appError.message).toBe('Generic test error');
    expect(appError.details).toEqual(context);
  });

  it('should determine retry eligibility correctly', () => {
    const retryableError = {
      type: ErrorType.SERVER_ERROR,
      retryable: true
    } as any;

    const nonRetryableError = {
      type: ErrorType.VALIDATION_ERROR,
      retryable: false
    } as any;

    expect(errorService.isRetryable(retryableError)).toBe(true);
    expect(errorService.isRetryable(nonRetryableError)).toBe(false);
  });

  it('should calculate retry delays correctly', () => {
    const error = {
      type: ErrorType.SERVER_ERROR,
      retryable: true
    } as any;

    const delay1 = errorService.getRetryDelay(error, 1);
    const delay2 = errorService.getRetryDelay(error, 2);

    expect(delay2).toBeGreaterThan(delay1);
  });

  it('should handle rate limit errors with retry-after', () => {
    const rateLimitError = {
      type: ErrorType.RATE_LIMIT_ERROR,
      retryable: true,
      details: { retryAfter: 30 }
    } as any;

    const delay = errorService.getRetryDelay(rateLimitError, 1);
    expect(delay).toBe(30000); // 30 seconds in milliseconds
  });
});

describe('NotificationService', () => {
  beforeEach(() => {
    notificationService.clearAll();
  });

  it('should add and remove notifications', () => {
    const id = notificationService.showSuccess('Test success');
    
    expect(notificationService.getNotifications()).toHaveLength(1);
    
    notificationService.removeNotification(id);
    
    expect(notificationService.getNotifications()).toHaveLength(0);
  });

  it('should create notifications from app errors', () => {
    const appError = {
      type: ErrorType.VALIDATION_ERROR,
      severity: ErrorSeverity.MEDIUM,
      message: 'Validation failed',
      userMessage: 'Please check your input',
      retryable: false,
      timestamp: new Date().toISOString()
    } as any;

    const id = notificationService.showErrorFromAppError(appError);
    const notifications = notificationService.getNotifications();
    
    expect(notifications).toHaveLength(1);
    expect(notifications[0].type).toBe(NotificationType.WARNING);
    expect(notifications[0].message).toBe('Please check your input');
  });

  it('should clear notifications by type', () => {
    notificationService.showSuccess('Success 1');
    notificationService.showError('Error 1');
    notificationService.showSuccess('Success 2');

    expect(notificationService.getNotifications()).toHaveLength(3);

    notificationService.clearByType(NotificationType.SUCCESS);

    const remaining = notificationService.getNotifications();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].type).toBe(NotificationType.ERROR);
  });

  it('should notify listeners of changes', () => {
    const listener = vi.fn();
    const unsubscribe = notificationService.addListener(listener);

    notificationService.showInfo('Test info');

    expect(listener).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          type: NotificationType.INFO,
          message: 'Test info'
        })
      ])
    );

    unsubscribe();
  });
});

describe('useErrorHandler hook', () => {
  it('should handle errors and provide retry functionality', async () => {
    render(<TestComponent />);

    // Initially no error
    expect(screen.getByTestId('error-state')).toHaveTextContent('No error');

    // Trigger error
    fireEvent.click(screen.getByText('Trigger Error'));

    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toHaveTextContent('Manual error');
    });

    // Clear error
    fireEvent.click(screen.getByText('Clear Error'));

    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toHaveTextContent('No error');
    });
  });

  it('should handle operation errors with withErrorHandling', async () => {
    render(<TestComponent />);

    fireEvent.click(screen.getByText('Test Operation'));

    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toHaveTextContent('Test operation error');
    });
  });
});

describe('useConnectionErrorHandler hook', () => {
  const ConnectionTestComponent: React.FC = () => {
    const { isOnline, connectionError } = useConnectionErrorHandler();

    return (
      <div>
        <div data-testid="online-status">
          {isOnline ? 'Online' : 'Offline'}
        </div>
        <div data-testid="connection-error">
          {connectionError ? connectionError.message : 'No connection error'}
        </div>
      </div>
    );
  };

  it('should track online/offline status', async () => {
    // Mock navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true
    });

    render(<ConnectionTestComponent />);

    expect(screen.getByTestId('online-status')).toHaveTextContent('Online');

    // Simulate going offline
    Object.defineProperty(navigator, 'onLine', {
      value: false
    });

    act(() => {
      window.dispatchEvent(new Event('offline'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('online-status')).toHaveTextContent('Offline');
      expect(screen.getByTestId('connection-error')).toHaveTextContent('Network connection lost');
    });

    // Simulate coming back online
    Object.defineProperty(navigator, 'onLine', {
      value: true
    });

    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('online-status')).toHaveTextContent('Online');
      expect(screen.getByTestId('connection-error')).toHaveTextContent('No connection error');
    });
  });
});

describe('useFormErrorHandler hook', () => {
  const FormTestComponent: React.FC = () => {
    const { fieldErrors, handleValidationError, clearFieldError, getFieldError, hasFieldError } = useFormErrorHandler();

    const triggerValidationError = () => {
      const error = {
        type: ErrorType.VALIDATION_ERROR,
        details: {
          validation_errors: [
            { field: 'email', message: 'Invalid email format' },
            { field: 'password', message: 'Password too short' }
          ]
        }
      } as any;
      handleValidationError(error);
    };

    return (
      <div>
        <div data-testid="email-error">
          {getFieldError('email') || 'No email error'}
        </div>
        <div data-testid="password-error">
          {getFieldError('password') || 'No password error'}
        </div>
        <div data-testid="has-email-error">
          {hasFieldError('email') ? 'Has email error' : 'No email error flag'}
        </div>
        <button onClick={triggerValidationError}>
          Trigger Validation Error
        </button>
        <button onClick={() => clearFieldError('email')}>
          Clear Email Error
        </button>
      </div>
    );
  };

  it('should handle validation errors and field management', async () => {
    render(<FormTestComponent />);

    // Initially no errors
    expect(screen.getByTestId('email-error')).toHaveTextContent('No email error');
    expect(screen.getByTestId('has-email-error')).toHaveTextContent('No email error flag');

    // Trigger validation error
    fireEvent.click(screen.getByText('Trigger Validation Error'));

    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toHaveTextContent('Invalid email format');
      expect(screen.getByTestId('password-error')).toHaveTextContent('Password too short');
      expect(screen.getByTestId('has-email-error')).toHaveTextContent('Has email error');
    });

    // Clear specific field error
    fireEvent.click(screen.getByText('Clear Email Error'));

    await waitFor(() => {
      expect(screen.getByTestId('email-error')).toHaveTextContent('No email error');
      expect(screen.getByTestId('password-error')).toHaveTextContent('Password too short');
      expect(screen.getByTestId('has-email-error')).toHaveTextContent('No email error flag');
    });
  });
});

describe('ConnectionFallback component', () => {
  it('should render connection fallback UI', () => {
    render(<ConnectionFallback />);

    expect(screen.getByText('Connection Problem')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('should handle retry action', async () => {
    const onRetry = vi.fn().mockResolvedValue(undefined);
    
    render(<ConnectionFallback onRetry={onRetry} />);

    fireEvent.click(screen.getByText('Try Again'));

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalled();
    });
  });

  it('should render minimal version', () => {
    render(<ConnectionFallback minimal={true} />);

    expect(screen.getByText('Connection lost')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
    expect(screen.queryByText('Connection Problem')).not.toBeInTheDocument();
  });

  it('should show troubleshooting tips when expanded', async () => {
    render(<ConnectionFallback showDetails={true} />);

    const troubleshootingButton = screen.getByText('Troubleshooting Tips');
    fireEvent.click(troubleshootingButton);

    await waitFor(() => {
      expect(screen.getByText('Try these steps:')).toBeInTheDocument();
      expect(screen.getByText('Check your internet connection')).toBeInTheDocument();
    });
  });
});

describe('NotificationContainer component', () => {
  beforeEach(() => {
    notificationService.clearAll();
  });

  it('should render notifications from service', async () => {
    render(<NotificationContainer />);

    act(() => {
      notificationService.showSuccess('Test success message');
    });

    await waitFor(() => {
      expect(screen.getByText('Success')).toBeInTheDocument();
      expect(screen.getByText('Test success message')).toBeInTheDocument();
    });
  });

  it('should handle notification dismissal', async () => {
    render(<NotificationContainer />);

    act(() => {
      notificationService.showInfo('Test info message');
    });

    await waitFor(() => {
      expect(screen.getByText('Test info message')).toBeInTheDocument();
    });

    const closeButton = screen.getByLabelText('close notification');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText('Test info message')).not.toBeInTheDocument();
    });
  });
});

export {};