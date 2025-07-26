/**
 * Notification service for displaying user notifications.
 * 
 * This service provides a centralized way to display notifications,
 * including error messages, success messages, and other user feedback.
 */

import { AppError, ErrorSeverity } from './errorService';

export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number; // Auto-dismiss after this many milliseconds
  persistent?: boolean; // Don't auto-dismiss
  actions?: NotificationAction[];
  timestamp: string;
}

export interface NotificationAction {
  label: string;
  action: () => void;
  variant?: 'text' | 'outlined' | 'contained';
}

type NotificationListener = (notifications: Notification[]) => void;

class NotificationService {
  private notifications: Notification[] = [];
  private listeners: NotificationListener[] = [];
  private nextId = 1;

  /**
   * Add a notification
   */
  addNotification(notification: Omit<Notification, 'id' | 'timestamp'>): string {
    const id = `notification-${this.nextId++}`;
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp: new Date().toISOString(),
    };

    this.notifications.push(newNotification);
    this.notifyListeners();

    // Auto-dismiss if duration is specified and not persistent
    if (notification.duration && !notification.persistent) {
      setTimeout(() => {
        this.removeNotification(id);
      }, notification.duration);
    }

    return id;
  }

  /**
   * Remove a notification by ID
   */
  removeNotification(id: string): void {
    const index = this.notifications.findIndex(n => n.id === id);
    if (index > -1) {
      this.notifications.splice(index, 1);
      this.notifyListeners();
    }
  }

  /**
   * Clear all notifications
   */
  clearAll(): void {
    this.notifications = [];
    this.notifyListeners();
  }

  /**
   * Clear notifications of a specific type
   */
  clearByType(type: NotificationType): void {
    this.notifications = this.notifications.filter(n => n.type !== type);
    this.notifyListeners();
  }

  /**
   * Get all notifications
   */
  getNotifications(): Notification[] {
    return [...this.notifications];
  }

  /**
   * Add listener for notification changes
   */
  addListener(listener: NotificationListener): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * Notify all listeners of changes
   */
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener([...this.notifications]);
      } catch (error) {
        console.error('Error in notification listener:', error);
      }
    });
  }

  /**
   * Show success notification
   */
  showSuccess(message: string, title = 'Success', duration = 5000): string {
    return this.addNotification({
      type: NotificationType.SUCCESS,
      title,
      message,
      duration,
    });
  }

  /**
   * Show error notification
   */
  showError(message: string, title = 'Error', persistent = false): string {
    return this.addNotification({
      type: NotificationType.ERROR,
      title,
      message,
      persistent,
      duration: persistent ? undefined : 10000,
    });
  }

  /**
   * Show warning notification
   */
  showWarning(message: string, title = 'Warning', duration = 7000): string {
    return this.addNotification({
      type: NotificationType.WARNING,
      title,
      message,
      duration,
    });
  }

  /**
   * Show info notification
   */
  showInfo(message: string, title = 'Info', duration = 5000): string {
    return this.addNotification({
      type: NotificationType.INFO,
      title,
      message,
      duration,
    });
  }

  /**
   * Show error notification from AppError
   */
  showErrorFromAppError(error: AppError, retryAction?: () => void): string {
    const actions: NotificationAction[] = [];

    // Add retry action if error is retryable
    if (error.retryable && retryAction) {
      actions.push({
        label: 'Retry',
        action: retryAction,
        variant: 'outlined',
      });
    }

    // Add dismiss action for persistent errors
    const persistent = error.severity === ErrorSeverity.CRITICAL || error.severity === ErrorSeverity.HIGH;
    
    if (persistent) {
      actions.push({
        label: 'Dismiss',
        action: () => {}, // Will be handled by the notification component
        variant: 'text',
      });
    }

    return this.addNotification({
      type: this.getNotificationTypeFromError(error),
      title: this.getErrorTitle(error),
      message: error.userMessage,
      persistent,
      duration: persistent ? undefined : this.getErrorDuration(error),
      actions: actions.length > 0 ? actions : undefined,
    });
  }

  /**
   * Get notification type from error
   */
  private getNotificationTypeFromError(error: AppError): NotificationType {
    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        return NotificationType.ERROR;
      case ErrorSeverity.MEDIUM:
        return NotificationType.WARNING;
      case ErrorSeverity.LOW:
        return NotificationType.INFO;
      default:
        return NotificationType.ERROR;
    }
  }

  /**
   * Get error title based on error type
   */
  private getErrorTitle(error: AppError): string {
    switch (error.type) {
      case 'NETWORK_ERROR':
        return 'Connection Error';
      case 'API_ERROR':
        return 'API Error';
      case 'VALIDATION_ERROR':
        return 'Validation Error';
      case 'AUTHENTICATION_ERROR':
        return 'Authentication Error';
      case 'AUTHORIZATION_ERROR':
        return 'Permission Error';
      case 'NOT_FOUND_ERROR':
        return 'Not Found';
      case 'RATE_LIMIT_ERROR':
        return 'Rate Limit Exceeded';
      case 'SERVER_ERROR':
        return 'Server Error';
      default:
        return 'Error';
    }
  }

  /**
   * Get error duration based on severity
   */
  private getErrorDuration(error: AppError): number {
    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
        return 0; // Persistent
      case ErrorSeverity.HIGH:
        return 15000; // 15 seconds
      case ErrorSeverity.MEDIUM:
        return 10000; // 10 seconds
      case ErrorSeverity.LOW:
        return 7000; // 7 seconds
      default:
        return 10000;
    }
  }

  /**
   * Show connection error with retry action
   */
  showConnectionError(retryAction?: () => void): string {
    const actions: NotificationAction[] = [];
    
    if (retryAction) {
      actions.push({
        label: 'Retry',
        action: retryAction,
        variant: 'contained',
      });
    }

    return this.addNotification({
      type: NotificationType.ERROR,
      title: 'Connection Lost',
      message: 'Unable to connect to the server. Please check your internet connection.',
      persistent: true,
      actions,
    });
  }

  /**
   * Show loading error with retry action
   */
  showLoadingError(resource: string, retryAction?: () => void): string {
    const actions: NotificationAction[] = [];
    
    if (retryAction) {
      actions.push({
        label: 'Retry',
        action: retryAction,
        variant: 'outlined',
      });
    }

    return this.addNotification({
      type: NotificationType.ERROR,
      title: 'Loading Error',
      message: `Failed to load ${resource}. Please try again.`,
      duration: 8000,
      actions,
    });
  }

  /**
   * Show save error with retry action
   */
  showSaveError(retryAction?: () => void): string {
    const actions: NotificationAction[] = [];
    
    if (retryAction) {
      actions.push({
        label: 'Retry',
        action: retryAction,
        variant: 'contained',
      });
    }

    return this.addNotification({
      type: NotificationType.ERROR,
      title: 'Save Failed',
      message: 'Failed to save changes. Please try again.',
      duration: 10000,
      actions,
    });
  }

  /**
   * Show validation error
   */
  showValidationError(fields: string[]): string {
    const fieldList = fields.length > 1 
      ? `${fields.slice(0, -1).join(', ')} and ${fields[fields.length - 1]}`
      : fields[0];

    return this.addNotification({
      type: NotificationType.WARNING,
      title: 'Validation Error',
      message: `Please check the following field${fields.length > 1 ? 's' : ''}: ${fieldList}`,
      duration: 8000,
    });
  }

  /**
   * Show operation success
   */
  showOperationSuccess(operation: string): string {
    return this.addNotification({
      type: NotificationType.SUCCESS,
      title: 'Success',
      message: `${operation} completed successfully.`,
      duration: 4000,
    });
  }

  /**
   * Show operation in progress
   */
  showOperationInProgress(operation: string): string {
    return this.addNotification({
      type: NotificationType.INFO,
      title: 'Processing',
      message: `${operation} in progress...`,
      persistent: true,
    });
  }
}

// Create singleton instance
export const notificationService = new NotificationService();

export default notificationService;