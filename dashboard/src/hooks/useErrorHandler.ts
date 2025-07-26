/**
 * Custom hook for handling errors with retry logic and user notifications.
 * 
 * This hook provides a centralized way to handle errors in React components,
 * including automatic retries, user notifications, and error recovery.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { AxiosError } from 'axios';
import { errorService, AppError, ErrorType } from '../services/errorService';
import { notificationService } from '../services/notificationService';

interface UseErrorHandlerOptions {
  showNotifications?: boolean;
  enableRetry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
  onError?: (error: AppError) => void;
  onRetry?: (attempt: number) => void;
  onMaxRetriesReached?: (error: AppError) => void;
}

interface ErrorState {
  error: AppError | null;
  isRetrying: boolean;
  retryCount: number;
  hasMaxRetriesReached: boolean;
}

interface UseErrorHandlerReturn {
  error: AppError | null;
  isRetrying: boolean;
  retryCount: number;
  hasMaxRetriesReached: boolean;
  handleError: (error: Error | AxiosError, context?: Record<string, any>) => AppError;
  retry: () => Promise<void>;
  clearError: () => void;
  withErrorHandling: <T extends any[], R>(
    fn: (...args: T) => Promise<R>,
    operationName?: string
  ) => (...args: T) => Promise<R | undefined>;
}

export function useErrorHandler(options: UseErrorHandlerOptions = {}): UseErrorHandlerReturn {
  const {
    showNotifications = true,
    enableRetry = true,
    maxRetries = 3,
    retryDelay = 1000,
    onError,
    onRetry,
    onMaxRetriesReached,
  } = options;

  const [errorState, setErrorState] = useState<ErrorState>({
    error: null,
    isRetrying: false,
    retryCount: 0,
    hasMaxRetriesReached: false,
  });

  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastOperationRef = useRef<(() => Promise<void>) | null>(null);
  const operationIdRef = useRef<string>('');

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  const handleError = useCallback((
    error: Error | AxiosError,
    context?: Record<string, any>
  ): AppError => {
    let appError: AppError;

    // Convert error to AppError
    if (error.name === 'AxiosError' || 'response' in error) {
      appError = errorService.handleAxiosError(error as AxiosError);
    } else {
      appError = errorService.handleGenericError(error as Error, context);
    }

    // Update error state
    setErrorState(prevState => ({
      ...prevState,
      error: appError,
      isRetrying: false,
    }));

    // Call custom error handler
    if (onError) {
      onError(appError);
    }

    // Show notification if enabled
    if (showNotifications) {
      const retryAction = enableRetry && appError.retryable && errorState.retryCount < maxRetries
        ? () => retry()
        : undefined;

      notificationService.showErrorFromAppError(appError, retryAction);
    }

    return appError;
  }, [enableRetry, maxRetries, onError, showNotifications, errorState.retryCount]);

  const retry = useCallback(async (): Promise<void> => {
    const { error, retryCount } = errorState;
    
    if (!error || !error.retryable || !lastOperationRef.current) {
      return;
    }

    if (retryCount >= maxRetries) {
      setErrorState(prevState => ({
        ...prevState,
        hasMaxRetriesReached: true,
      }));
      
      if (onMaxRetriesReached) {
        onMaxRetriesReached(error);
      }
      
      return;
    }

    const newRetryCount = retryCount + 1;
    
    setErrorState(prevState => ({
      ...prevState,
      isRetrying: true,
      retryCount: newRetryCount,
    }));

    // Call retry callback
    if (onRetry) {
      onRetry(newRetryCount);
    }

    // Calculate delay
    const delay = errorService.getRetryDelay(error, newRetryCount);

    // Wait for delay
    await new Promise(resolve => {
      retryTimeoutRef.current = setTimeout(resolve, delay);
    });

    try {
      // Execute the last operation
      await lastOperationRef.current();
      
      // Clear error on successful retry
      setErrorState({
        error: null,
        isRetrying: false,
        retryCount: 0,
        hasMaxRetriesReached: false,
      });

      // Clear error service retry attempts
      errorService.clearRetryAttempts(operationIdRef.current);

      // Show success notification
      if (showNotifications) {
        notificationService.showSuccess('Operation completed successfully after retry.');
      }
    } catch (retryError) {
      // Handle retry error
      handleError(retryError as Error);
    }
  }, [errorState, maxRetries, onMaxRetriesReached, onRetry, handleError, showNotifications]);

  const clearError = useCallback(() => {
    setErrorState({
      error: null,
      isRetrying: false,
      retryCount: 0,
      hasMaxRetriesReached: false,
    });

    // Clear timeout
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    // Clear operation reference
    lastOperationRef.current = null;
  }, []);

  const withErrorHandling = useCallback(<T extends any[], R>(
    fn: (...args: T) => Promise<R>,
    operationName?: string
  ) => {
    return async (...args: T): Promise<R | undefined> => {
      // Generate operation ID
      operationIdRef.current = operationName || `operation-${Date.now()}`;
      
      // Store operation for retry
      lastOperationRef.current = () => fn(...args) as Promise<void>;

      try {
        const result = await fn(...args);
        
        // Clear error on success
        if (errorState.error) {
          clearError();
        }
        
        return result;
      } catch (error) {
        handleError(error as Error, { operationName });
        return undefined;
      }
    };
  }, [errorState.error, clearError, handleError]);

  return {
    error: errorState.error,
    isRetrying: errorState.isRetrying,
    retryCount: errorState.retryCount,
    hasMaxRetriesReached: errorState.hasMaxRetriesReached,
    handleError,
    retry,
    clearError,
    withErrorHandling,
  };
}

// Hook for handling connection errors specifically
export function useConnectionErrorHandler() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [connectionError, setConnectionError] = useState<AppError | null>(null);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setConnectionError(null);
      notificationService.showSuccess('Connection restored');
    };

    const handleOffline = () => {
      setIsOnline(false);
      const error: AppError = {
        type: ErrorType.NETWORK_ERROR,
        severity: 'HIGH' as any,
        message: 'Network connection lost',
        userMessage: 'You are currently offline. Some features may not be available.',
        timestamp: new Date().toISOString(),
        retryable: true,
      };
      setConnectionError(error);
      notificationService.showConnectionError();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return {
    isOnline,
    connectionError,
  };
}

// Hook for handling form validation errors
export function useFormErrorHandler() {
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleValidationError = useCallback((error: AppError) => {
    if (error.type === ErrorType.VALIDATION_ERROR && error.details?.validation_errors) {
      const errors: Record<string, string> = {};
      
      error.details.validation_errors.forEach((validationError: any) => {
        if (validationError.field && validationError.message) {
          errors[validationError.field] = validationError.message;
        }
      });
      
      setFieldErrors(errors);
      
      // Show notification with field names
      const fieldNames = Object.keys(errors);
      if (fieldNames.length > 0) {
        notificationService.showValidationError(fieldNames);
      }
    }
  }, []);

  const clearFieldError = useCallback((field: string) => {
    setFieldErrors(prevErrors => {
      const newErrors = { ...prevErrors };
      delete newErrors[field];
      return newErrors;
    });
  }, []);

  const clearAllFieldErrors = useCallback(() => {
    setFieldErrors({});
  }, []);

  const getFieldError = useCallback((field: string): string | undefined => {
    return fieldErrors[field];
  }, [fieldErrors]);

  const hasFieldError = useCallback((field: string): boolean => {
    return field in fieldErrors;
  }, [fieldErrors]);

  return {
    fieldErrors,
    handleValidationError,
    clearFieldError,
    clearAllFieldErrors,
    getFieldError,
    hasFieldError,
  };
}

export default useErrorHandler;