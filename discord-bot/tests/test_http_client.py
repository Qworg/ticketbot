"""Tests for the HTTP client."""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import httpx

# Set test environment variables before importing modules
os.environ["DISCORD_BOT_TOKEN"] = "test_token"
os.environ["DISCORD_GUILD_ID"] = "123456789"
os.environ["BACKEND_API_URL"] = "http://localhost:8000"

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.http_client import (
    BackendAPIClient, 
    RetryStrategy, 
    APIError, 
    AuthenticationError, 
    RateLimitError, 
    ConnectionError, 
    ValidationError
)


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client for testing."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.headers = {}
    mock_response.text = "OK"
    
    # Configure the mock client methods to return the mock response
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_client.put.return_value = mock_response
    mock_client.delete.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    mock_config = MagicMock()
    mock_config.api_url = "http://localhost:8000"
    mock_config.api_key = "test_api_key"
    return mock_config


@pytest.mark.asyncio
async def test_api_client_initialization(mock_config):
    """Test that the API client initializes correctly."""
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient") as mock_async_client:
            # Create the client
            client = BackendAPIClient(max_retries=5, retry_strategy=RetryStrategy.FIXED_DELAY)
            
            # Check that the client was initialized correctly
            assert client.base_url == "http://localhost:8000"
            assert client.api_key == "test_api_key"
            assert client.max_retries == 5
            assert client.retry_strategy == RetryStrategy.FIXED_DELAY
            assert client.connected is False
            
            # Check that the AsyncClient was created with the correct parameters
            mock_async_client.assert_called_once()
            _, kwargs = mock_async_client.call_args
            assert kwargs["base_url"] == "http://localhost:8000"


@pytest.mark.asyncio
async def test_api_client_check_connection_success(mock_httpx_client, mock_config):
    """Test that check_connection returns True when the API is reachable."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call check_connection
            result = await client.check_connection()
            
            # Check that the method returned True
            assert result is True
            assert client.connected is True
            
            # Check that the get method was called correctly
            mock_httpx_client.get.assert_called_once_with("/health")


@pytest.mark.asyncio
async def test_api_client_check_connection_failure(mock_httpx_client, mock_config):
    """Test that check_connection returns False when the API is not reachable."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Configure the mock to raise an exception
            mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")
            
            # Create the client
            client = BackendAPIClient()
            
            # Call check_connection
            result = await client.check_connection()
            
            # Check that the method returned False
            assert result is False
            assert client.connected is False


@pytest.mark.asyncio
async def test_api_client_get(mock_httpx_client, mock_config):
    """Test the get method."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call get
            result = await client.get("/test", {"param": "value"})
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the get method was called correctly
            mock_httpx_client.get.assert_called_once_with("/test", params={"param": "value"})


@pytest.mark.asyncio
async def test_api_client_post(mock_httpx_client, mock_config):
    """Test the post method."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call post
            result = await client.post("/test", {"data": "value"})
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the post method was called correctly
            mock_httpx_client.post.assert_called_once_with("/test", json={"data": "value"})


@pytest.mark.asyncio
async def test_api_client_put(mock_httpx_client, mock_config):
    """Test the put method."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call put
            result = await client.put("/test", {"data": "value"})
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the put method was called correctly
            mock_httpx_client.put.assert_called_once_with("/test", json={"data": "value"})


@pytest.mark.asyncio
async def test_api_client_delete(mock_httpx_client, mock_config):
    """Test the delete method."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call delete
            result = await client.delete("/test")
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the delete method was called correctly
            mock_httpx_client.delete.assert_called_once_with("/test")


# New tests for enhanced functionality

@pytest.mark.asyncio
async def test_retry_logic_exponential_backoff(mock_httpx_client, mock_config):
    """Test retry logic with exponential backoff."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            with patch("asyncio.sleep") as mock_sleep:
                # Configure the mock to fail twice then succeed
                mock_httpx_client.get.side_effect = [
                    httpx.ConnectError("Connection failed"),
                    httpx.ConnectError("Connection failed"),
                    MagicMock(is_success=True, json=lambda: {"status": "ok"})
                ]
                
                # Create the client with retry enabled
                client = BackendAPIClient(max_retries=3, retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
                
                # Call get
                result = await client.get("/test")
                
                # Check that the method eventually succeeded
                assert result == {"status": "ok"}
                
                # Check that get was called 3 times
                assert mock_httpx_client.get.call_count == 3
                
                # Check that sleep was called for retries
                assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_retry_logic_max_retries_exceeded(mock_httpx_client, mock_config):
    """Test that retry logic stops after max retries."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            with patch("asyncio.sleep"):
                # Configure the mock to always fail
                mock_httpx_client.get.side_effect = httpx.ConnectError("Connection failed")
                
                # Create the client with limited retries
                client = BackendAPIClient(max_retries=2)
                
                # Call get and expect it to raise ConnectionError
                with pytest.raises(ConnectionError):
                    await client.get("/test")
                
                # Check that get was called max_retries + 1 times
                assert mock_httpx_client.get.call_count == 3


@pytest.mark.asyncio
async def test_authentication_error_handling(mock_httpx_client, mock_config):
    """Test authentication error handling."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Configure the mock to return 401
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 401
            mock_response.json.return_value = {"detail": "Unauthorized"}
            mock_httpx_client.get.return_value = mock_response
            
            # Create the client
            client = BackendAPIClient()
            
            # Call get and expect AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                await client.get("/test")
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.response_data == {"detail": "Unauthorized"}


@pytest.mark.asyncio
async def test_rate_limit_error_handling(mock_httpx_client, mock_config):
    """Test rate limit error handling."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Configure the mock to return 429
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 429
            mock_response.headers = {"retry-after": "60"}
            mock_response.json.return_value = {"detail": "Rate limit exceeded"}
            mock_httpx_client.get.return_value = mock_response
            
            # Create the client
            client = BackendAPIClient()
            
            # Call get and expect RateLimitError
            with pytest.raises(RateLimitError) as exc_info:
                await client.get("/test")
            
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 60


@pytest.mark.asyncio
async def test_validation_error_handling(mock_httpx_client, mock_config):
    """Test validation error handling."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Configure the mock to return 422
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 422
            mock_response.json.return_value = {"detail": "Validation failed"}
            mock_httpx_client.post.return_value = mock_response
            
            # Create the client
            client = BackendAPIClient()
            
            # Call post and expect ValidationError
            with pytest.raises(ValidationError) as exc_info:
                await client.post("/test", {"data": "invalid"})
            
            assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_authenticate_success(mock_httpx_client, mock_config):
    """Test successful authentication."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Configure the mock to return auth token
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.json.return_value = {"access_token": "new_token"}
            mock_httpx_client.post.return_value = mock_response
            
            # Create the client
            client = BackendAPIClient()
            
            # Call authenticate
            result = await client.authenticate("username", "password")
            
            # Check that authentication succeeded
            assert result is True
            assert client._auth_token == "new_token"
            # Note: client.client.headers is a mock, so we just check the token was stored
            
            # Check that post was called correctly
            mock_httpx_client.post.assert_called_once_with("/auth/login", json={
                "username": "username",
                "password": "password"
            })


@pytest.mark.asyncio
async def test_ticket_specific_methods(mock_httpx_client, mock_config):
    """Test ticket-specific API methods."""
    mock_config.api_key = None
    
    with patch("utils.http_client.config", mock_config):
        with patch("utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Test create_ticket
            await client.create_ticket({"title": "Test ticket"})
            mock_httpx_client.post.assert_called_with("/api/tickets", json={"title": "Test ticket"})
            
            # Test get_ticket
            await client.get_ticket("123")
            mock_httpx_client.get.assert_called_with("/api/tickets/123", params=None)
            
            # Test update_ticket
            await client.update_ticket("123", {"status": "closed"})
            mock_httpx_client.put.assert_called_with("/api/tickets/123", json={"status": "closed"})
            
            # Test close_ticket
            await client.close_ticket("123")
            mock_httpx_client.delete.assert_called_with("/api/tickets/123")
            
            # Test add_message
            await client.add_message("123", {"content": "Hello"})
            mock_httpx_client.post.assert_called_with("/api/tickets/123/messages", json={"content": "Hello"})
            
            # Test get_transcript
            await client.get_transcript("123")
            mock_httpx_client.get.assert_called_with("/api/tickets/123/transcript", params=None)
            
            # Test search_transcripts
            await client.search_transcripts("query", {"status": "open"})
            mock_httpx_client.get.assert_called_with("/api/search/transcripts", params={"q": "query", "status": "open"})