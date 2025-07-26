/**
 * Error handling service for the React dashboard.
 * 
 * This service provides centralized error handling, logging, and user notification
 * for API calls, network errors, and application errors.
 */

import { AxiosError, AxiosResponse } from 'axios';

// Error types
export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  API_ERROR = 'API_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  NOT_FOUND_ERROR = 'NOT_FOUND_ERROR',
  RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

// Error severity levels
export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

// Structured error interface
export interface AppError {
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  userMessage: string;
  details?: Record<string, any>;
  timestamp: string;
  requestId?: string;
  statusCode?: number;
  retryable: boolean;
  originalError?: Error | AxiosError;
}

// Error handler configuration
interface ErrorHandlerConfig {
  enableLogging: boolean;
  enableReporting: boolean;
  reportingEndpoint?: string;
  maxRetries: number;
  retryDelay: number;
  showUserNotifications: boolean;
}

class ErrorService {
  private config: ErrorHandlerConfig = {
    enableLogging: true,
    enableReporting: true,
    reportingEndpoint: '/api/errors',
    maxRetries: 3,
    retryDelay: 1000,
    showUserNotifications: true,
  };

  private errorListeners: Array<(error: AppError) => void> = [];
  private retryAttempts: Map<string, number> = new Map();

  constructor(config?: Partial<ErrorHandlerConfig>) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  /**
   * Handle Axios errors from API calls
   */
  handleAxiosError(error: AxiosError): AppError {
    const appError = this.createAppError(error);
    this.processError(appError);
    return appError;
  }

  /**
   * Handle generic JavaScript errors
   */
  handleGenericError(error: Error, context?: Record<string, any>): AppError {
    const appError: AppError = {
      type: ErrorType.UNKNOWN_ERROR,
      severity: ErrorSeverity.MEDIUM,
      message: error.message,
      userMessage: 'An unexpected error occurred. Please try again.',
      details: context,
      timestamp: new Date().toISOString(),
      retryable: false,
      originalError: error,
    };

    this.processError(appError);
    return appError;
  }

  /**
   * Create structured error from Axios error
   */
  private createAppError(axiosError: AxiosError): AppError {
    const response = axiosError.response;
    const request = axiosError.request;

    // Network error (no response received)
    if (!response && request) {
      return {
        type: ErrorType.NETWORK_ERROR,
        severity: ErrorSeverity.HIGH,
        message: 'Network error: Unable to connect to server',
        userMessage: 'Unable to connect to the server. Please check your internet connection and try again.',
        timestamp: new Date().toISOString(),
        retryable: true,
        originalError: axiosError,
      };
    }

    // No request was made (configuration error)
    if (!request) {
      return {
        type: ErrorType.UNKNOWN_ERROR,
        severity: ErrorSeverity.CRITICAL,
        message: 'Request configuration error',
        userMessage: 'A configuration error occurred. Please contact support.',
        timestamp: new Date().toISOString(),
        retryable: false,
        originalError: axiosError,
      };
    }

    // Response received with error status
    const statusCode = response?.status || 0;
    const errorData = response?.data as any;
    const requestId = response?.headers?.['x-request-id'];

    let type: ErrorType;
    let severity: ErrorSeverity;
    let userMessage: string;
    let retryable = false;

    switch (statusCode) {
      case 400:
        type = ErrorType.VALIDATION_ERROR;
        severity = ErrorSeverity.LOW;
        userMessage = 'Invalid request. Please check your input and try again.';
        break;
      case 401:
        type = ErrorType.AUTHENTICATION_ERROR;
        severity = ErrorSeverity.MEDIUM;
        userMessage = 'Authentication failed. Please log in again.';
        break;
      case 403:
        type = ErrorType.AUTHORIZATION_ERROR;
        severity = ErrorSeverity.MEDIUM;
        userMessage = 'You do not have permission to perform this action.';
        break;
      case 404:
        type = ErrorType.NOT_FOUND_ERROR;
        severity = ErrorSeverity.LOW;
        userMessage = 'The requested resource was not found.';
        break;
      case 429:
        type = ErrorType.RATE_LIMIT_ERROR;
        severity = ErrorSeverity.MEDIUM;
        userMessage = 'Too many requests. Please wait a moment and try again.';
        retryable = true;
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        type = ErrorType.SERVER_ERROR;
        severity = ErrorSeverity.HIGH;
        userMessage = 'Server error. Please try again later.';
        retryable = true;
        break;
      default:
        type = ErrorType.API_ERROR;
        severity = ErrorSeverity.MEDIUM;
        userMessage = 'An error occurred while processing your request.';
        retryable = statusCode >= 500;
    }

    // Use server-provided error message if available
    if (errorData?.error?.message) {
      userMessage = errorData.error.message;
    }

    return {
      type,
      severity,
      message: errorData?.error?.message || axiosError.message,
      userMessage,
      details: {
        statusCode,
        url: axiosError.config?.url,
        method: axiosError.config?.method?.toUpperCase(),
        ...errorData?.error?.details,
      },
      timestamp: new Date().toISOString(),
      requestId,
      statusCode,
      retryable,
      originalError: axiosError,
    };
  }

  /**
   * Process error (log, report, notify)
   */
  private processError(error: AppError): void {
    // Log error
    if (this.config.enableLogging) {
      this.logError(error);
    }

    // Report error
    if (this.config.enableReporting) {
      this.reportError(error);
    }

    // Notify listeners
    this.notifyListeners(error);
  }

  /**
   * Log error to console
   */
  private logError(error: AppError): void {
    const logLevel = this.getLogLevel(error.severity);
    const logMessage = `[${error.type}] ${error.message}`;
    
    console[logLevel](logMessage, {
      error,
      timestamp: error.timestamp,
      requestId: error.requestId,
    });
  }

  /**
   * Get appropriate console log level for error severity
   */
  private getLogLevel(severity: ErrorSeverity): 'error' | 'warn' | 'info' {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        return 'error';
      case ErrorSeverity.MEDIUM:
        return 'warn';
      case ErrorSeverity.LOW:
        return 'info';
      default:
        return 'error';
    }
  }

  /**
   * Report error to monitoring service
   */
  private async reportError(error: AppError): Promise<void> {
    if (!this.config.reportingEndpoint) {
      return;
    }

    try {
      const reportData = {
        ...error,
        userAgent: navigator.userAgent,
        url: window.location.href,
        originalError: undefined, // Don't send the original error object
      };

      await fetch(this.config.reportingEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(reportData),
      });
    } catch (reportingError) {
      console.warn('Failed to report error:', reportingError);
    }
  }

  /**
   * Notify error listeners
   */
  private notifyListeners(error: AppError): void {
    this.errorListeners.forEach(listener => {
      try {
        listener(error);
      } catch (listenerError) {
        console.error('Error in error listener:', listenerError);
      }
    });
  }

  /**
   * Add error listener
   */
  addErrorListener(listener: (error: AppError) => void): () => void {
    this.errorListeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.errorListeners.indexOf(listener);
      if (index > -1) {
        this.errorListeners.splice(index, 1);
      }
    };
  }

  /**
   * Check if error is retryable
   */
  isRetryable(error: AppError): boolean {
    return error.retryable;
  }

  /**
   * Get retry delay for error
   */
  getRetryDelay(error: AppError, attempt: number): number {
    // Exponential backoff with jitter
    const baseDelay = this.config.retryDelay;
    const exponentialDelay = baseDelay * Math.pow(2, attempt - 1);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    
    // Special handling for rate limit errors
    if (error.type === ErrorType.RATE_LIMIT_ERROR && error.details?.retryAfter) {
      return error.details.retryAfter * 1000; // Convert to milliseconds
    }
    
    return exponentialDelay + jitter;
  }

  /**
   * Check if should retry based on attempt count
   */
  shouldRetry(error: AppError, attempt: number): boolean {
    return error.retryable && attempt <= this.config.maxRetries;
  }

  /**
   * Create user-friendly error message
   */
  getUserMessage(error: AppError): string {
    return error.userMessage;
  }

  /**
   * Get error icon based on type
   */
  getErrorIcon(error: AppError): string {
    switch (error.type) {
      case ErrorType.NETWORK_ERROR:
        return 'wifi_off';
      case ErrorType.AUTHENTICATION_ERROR:
        return 'lock';
      case ErrorType.AUTHORIZATION_ERROR:
        return 'block';
      case ErrorType.NOT_FOUND_ERROR:
        return 'search_off';
      case ErrorType.RATE_LIMIT_ERROR:
        return 'hourglass_empty';
      case ErrorType.SERVER_ERROR:
        return 'dns';
      case ErrorType.VALIDATION_ERROR:
        return 'error_outline';
      default:
        return 'error';
    }
  }

  /**
   * Get error color based on severity
   */
  getErrorColor(error: AppError): 'error' | 'warning' | 'info' {
    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        return 'error';
      case ErrorSeverity.MEDIUM:
        return 'warning';
      case ErrorSeverity.LOW:
        return 'info';
      default:
        return 'error';
    }
  }

  /**
   * Clear retry attempts for a specific operation
   */
  clearRetryAttempts(operationId: string): void {
    this.retryAttempts.delete(operationId);
  }

  /**
   * Get current retry attempt count
   */
  getRetryAttemptCount(operationId: string): number {
    return this.retryAttempts.get(operationId) || 0;
  }

  /**
   * Increment retry attempt count
   */
  incrementRetryAttempt(operationId: string): number {
    const currentCount = this.getRetryAttemptCount(operationId);
    const newCount = currentCount + 1;
    this.retryAttempts.set(operationId, newCount);
    return newCount;
  }
}

// Create singleton instance
export const errorService = new ErrorService();

// Export types and service
export default errorService;