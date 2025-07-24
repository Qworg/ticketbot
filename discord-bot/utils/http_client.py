"""HTTP client for communicating with the backend API."""

import logging
import asyncio
from typing import Any, Dict, Optional, Union
import httpx

from discord_bot.config.settings import config, logger

class BackendAPIClient:
    """HTTP client for communicating with the backend API."""
    
    def __init__(self):
        """Initialize the HTTP client with configuration."""
        self.base_url = config.api_url
        self.api_key = config.api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DiscordBot/1.0",
            }
        )
        
        # Add API key if available
        if self.api_key:
            self.client.headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.connected = False
    
    async def check_connection(self) -> bool:
        """Check if the backend API is reachable."""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to backend API: {e}")
            self.connected = False
            return False
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a GET request to the backend API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        try:
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during GET {endpoint}: {e}")
            raise
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request to the backend API.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        try:
            response = await self.client.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during POST {endpoint}: {e}")
            raise
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a PUT request to the backend API.
        
        Args:
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        try:
            response = await self.client.put(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during PUT {endpoint}: {e}")
            raise
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Send a DELETE request to the backend API.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        try:
            response = await self.client.delete(endpoint)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during DELETE {endpoint}: {e}")
            raise
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


# Create a global client instance
api_client = None


async def get_api_client() -> BackendAPIClient:
    """Get or create the API client instance."""
    global api_client
    if api_client is None:
        api_client = BackendAPIClient()
        await api_client.check_connection()
    return api_client