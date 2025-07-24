"""HTTP client for communicating with the backend API."""

import logging
import asyncio
import random
from typing import Any, Dict, Optional, Union, List
from enum import Enum
import httpx

from config.settings import config, logger


class RetryStrategy(Enum):
    """Retry strategy options."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""
    pass


class RateLimitError(APIError):
    """Exception raised when rate limits are exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConnectionError(APIError):
    """Exception raised for connection failures."""
    pass


class ValidationError(APIError):
    """Exception raised for validation failures."""
    pass

class BackendAPIClient:
    """HTTP client for communicating with the backend API."""
    
    def __init__(self, 
                 max_retries: int = 3,
                 retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 timeout: float = 30.0):
        """Initialize the HTTP client with configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_strategy: Strategy to use for retries
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            timeout: Request timeout (seconds)
        """
        self.base_url = config.api_url
        self.api_key = config.api_key
        self.max_retries = max_retries
        self.retry_strategy = retry_strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        # Create HTTP client with configuration
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot/1.0",
            }
        )
        
        # Add API key if available
        if self.api_key:
            self.client.headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.connected = False
        self._auth_token = None
    
    async def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        if self.retry_strategy == RetryStrategy.NO_RETRY:
            return 0.0
        elif self.retry_strategy == RetryStrategy.FIXED_DELAY:
            return self.base_delay
        else:  # EXPONENTIAL_BACKOFF
            # Exponential backoff with jitter
            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
            # Add jitter (±25% of delay)
            jitter = delay * 0.25 * (2 * random.random() - 1)
            return max(0.1, delay + jitter)
    
    async def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if a request should be retried.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            True if the request should be retried
        """
        if attempt >= self.max_retries:
            return False
        
        # Retry on connection errors
        if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        
        # Retry on server errors (5xx)
        if isinstance(exception, httpx.HTTPStatusError):
            return 500 <= exception.response.status_code < 600
        
        # Don't retry on client errors (4xx) except for rate limiting
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code == 429
        
        return False
    
    async def _handle_response_error(self, response: httpx.Response) -> None:
        """Handle HTTP response errors and raise appropriate exceptions.
        
        Args:
            response: HTTP response object
            
        Raises:
            APIError: Appropriate API error based on status code
        """
        try:
            error_data = response.json()
        except Exception:
            error_data = {"detail": response.text}
        
        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed",
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 403:
            raise AuthenticationError(
                "Access forbidden",
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 422:
            raise ValidationError(
                "Validation error",
                status_code=response.status_code,
                response_data=error_data
            )
        elif response.status_code == 429:
            retry_after = None
            if "retry-after" in response.headers:
                try:
                    retry_after = int(response.headers["retry-after"])
                except ValueError:
                    pass
            raise RateLimitError(
                "Rate limit exceeded",
                status_code=response.status_code,
                response_data=error_data,
                retry_after=retry_after
            )
        else:
            raise APIError(
                f"API request failed with status {response.status_code}",
                status_code=response.status_code,
                response_data=error_data
            )
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for the request
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails after all retries
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Make the request
                response = await getattr(self.client, method.lower())(endpoint, **kwargs)
                
                # Handle non-2xx responses
                if not response.is_success:
                    await self._handle_response_error(response)
                
                # Return successful response
                return response.json()
                
            except Exception as e:
                last_exception = e
                
                # Log the attempt
                if attempt < self.max_retries:
                    logger.warning(f"Request {method} {endpoint} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                
                # Check if we should retry
                if not await self._should_retry(e, attempt):
                    break
                
                # Calculate delay and wait
                if attempt < self.max_retries:
                    delay = await self._calculate_delay(attempt)
                    if delay > 0:
                        await asyncio.sleep(delay)
        
        # All retries exhausted, raise the last exception
        if isinstance(last_exception, (APIError, AuthenticationError, RateLimitError, ValidationError)):
            raise last_exception
        elif isinstance(last_exception, (httpx.ConnectError, httpx.TimeoutException)):
            raise ConnectionError(f"Failed to connect to backend API: {last_exception}")
        else:
            raise APIError(f"Request failed: {last_exception}")
    
    async def check_connection(self) -> bool:
        """Check if the backend API is reachable."""
        try:
            await self._make_request("GET", "/health")
            self.connected = True
            logger.info("Successfully connected to backend API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to backend API: {e}")
            self.connected = False
            return False
    
    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the backend API and store the token.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            
        Returns:
            True if authentication was successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            response = await self._make_request("POST", "/auth/login", json={
                "username": username,
                "password": password
            })
            
            token = response.get("access_token")
            if token:
                self._auth_token = token
                self.client.headers["Authorization"] = f"Bearer {token}"
                logger.info("Successfully authenticated with backend API")
                return True
            else:
                raise AuthenticationError("No access token in response")
                
        except APIError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}")
    
    async def refresh_token(self) -> bool:
        """Refresh the authentication token.
        
        Returns:
            True if token refresh was successful
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        if not self._auth_token:
            raise AuthenticationError("No token to refresh")
        
        try:
            response = await self._make_request("POST", "/auth/refresh", headers={
                "Authorization": f"Bearer {self._auth_token}"
            })
            
            new_token = response.get("access_token")
            if new_token:
                self._auth_token = new_token
                self.client.headers["Authorization"] = f"Bearer {new_token}"
                logger.info("Successfully refreshed authentication token")
                return True
            else:
                raise AuthenticationError("No access token in refresh response")
                
        except APIError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {e}")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a GET request to the backend API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
        """
        return await self._make_request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request to the backend API.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
        """
        return await self._make_request("POST", endpoint, json=data)
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a PUT request to the backend API.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
        """
        return await self._make_request("PUT", endpoint, json=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Send a DELETE request to the backend API.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
        """
        return await self._make_request("DELETE", endpoint)
    
    # Ticket-specific API methods
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new ticket.
        
        Args:
            ticket_data: Ticket creation data
            
        Returns:
            Created ticket data
        """
        return await self.post("/api/tickets", ticket_data)
    
    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket by ID.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Ticket data
        """
        return await self.get(f"/api/tickets/{ticket_id}")
    
    async def update_ticket(self, ticket_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a ticket.
        
        Args:
            ticket_id: Ticket ID
            update_data: Update data
            
        Returns:
            Updated ticket data
        """
        return await self.put(f"/api/tickets/{ticket_id}", update_data)
    
    async def close_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Close a ticket.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Closed ticket data
        """
        return await self.delete(f"/api/tickets/{ticket_id}")
    
    async def add_message(self, ticket_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a message to a ticket.
        
        Args:
            ticket_id: Ticket ID
            message_data: Message data
            
        Returns:
            Created message data
        """
        return await self.post(f"/api/tickets/{ticket_id}/messages", message_data)
    
    async def get_transcript(self, ticket_id: str) -> Dict[str, Any]:
        """Get ticket transcript.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Transcript data
        """
        return await self.get(f"/api/tickets/{ticket_id}/transcript")
    
    async def search_transcripts(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search ticket transcripts.
        
        Args:
            query: Search query
            filters: Additional search filters
            
        Returns:
            Search results
        """
        params = {"q": query}
        if filters:
            params.update(filters)
        return await self.get("/api/search/transcripts", params=params)
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Create a global client instance
api_client = None


async def get_api_client(max_retries: int = 3, 
                        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF) -> BackendAPIClient:
    """Get or create the API client instance.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_strategy: Strategy to use for retries
        
    Returns:
        BackendAPIClient instance
    """
    global api_client
    if api_client is None:
        api_client = BackendAPIClient(
            max_retries=max_retries,
            retry_strategy=retry_strategy
        )
        await api_client.check_connection()
    return api_client


async def reset_api_client() -> None:
    """Reset the global API client instance."""
    global api_client
    if api_client:
        await api_client.close()
        api_client = None