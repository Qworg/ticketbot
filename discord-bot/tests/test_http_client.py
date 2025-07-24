"""Tests for the HTTP client."""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock

import httpx

# Add the parent directory to sys.path to allow imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from discord_bot.utils.http_client import BackendAPIClient


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    
    # Configure the mock client methods
    mock_client.get.return_value = asyncio.Future()
    mock_client.get.return_value.set_result(mock_response)
    
    mock_client.post.return_value = asyncio.Future()
    mock_client.post.return_value.set_result(mock_response)
    
    mock_client.put.return_value = asyncio.Future()
    mock_client.put.return_value.set_result(mock_response)
    
    mock_client.delete.return_value = asyncio.Future()
    mock_client.delete.return_value.set_result(mock_response)
    
    return mock_client


@pytest.mark.asyncio
async def test_api_client_initialization():
    """Test that the API client initializes correctly."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = "test_api_key"
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient") as mock_async_client:
            # Create the client
            client = BackendAPIClient()
            
            # Check that the client was initialized correctly
            assert client.base_url == "http://localhost:8000"
            assert client.api_key == "test_api_key"
            assert client.connected is False
            
            # Check that the AsyncClient was created with the correct parameters
            mock_async_client.assert_called_once()
            _, kwargs = mock_async_client.call_args
            assert kwargs["base_url"] == "http://localhost:8000"
            assert kwargs["headers"]["Authorization"] == "Bearer test_api_key"


@pytest.mark.asyncio
async def test_api_client_check_connection_success(mock_httpx_client):
    """Test that check_connection returns True when the API is reachable."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = None
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
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
async def test_api_client_check_connection_failure(mock_httpx_client):
    """Test that check_connection returns False when the API is not reachable."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = None
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
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
async def test_api_client_get(mock_httpx_client):
    """Test the get method."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = None
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call get
            result = await client.get("/test", {"param": "value"})
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the get method was called correctly
            mock_httpx_client.get.assert_called_once_with("/test", params={"param": "value"})


@pytest.mark.asyncio
async def test_api_client_post(mock_httpx_client):
    """Test the post method."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = None
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call post
            result = await client.post("/test", {"data": "value"})
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the post method was called correctly
            mock_httpx_client.post.assert_called_once_with("/test", json={"data": "value"})


@pytest.mark.asyncio
async def test_api_client_put(mock_httpx_client):
    """Test the put method."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = None
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call put
            result = await client.put("/test", {"data": "value"})
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the put method was called correctly
            mock_httpx_client.put.assert_called_once_with("/test", json={"data": "value"})


@pytest.mark.asyncio
async def test_api_client_delete(mock_httpx_client):
    """Test the delete method."""
    with patch("discord_bot.utils.http_client.config", create=True) as mock_config:
        # Configure the mock
        mock_config.api_url = "http://localhost:8000"
        mock_config.api_key = None
        
        with patch("discord_bot.utils.http_client.httpx.AsyncClient", return_value=mock_httpx_client):
            # Create the client
            client = BackendAPIClient()
            
            # Call delete
            result = await client.delete("/test")
            
            # Check that the method returned the expected result
            assert result == {"status": "ok"}
            
            # Check that the delete method was called correctly
            mock_httpx_client.delete.assert_called_once_with("/test")