"""
Command management utilities for automatic cleanup and monitoring.
"""

import asyncio
import logging
from typing import Optional

from .registry import get_command_registry


logger = logging.getLogger(__name__)


class CommandManager:
    """Manages command lifecycle and maintenance tasks."""
    
    def __init__(self):
        """Initialize command manager."""
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_maintenance(self) -> None:
        """Start background maintenance tasks."""
        if self._running:
            logger.warning("Command manager already running")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started command manager maintenance tasks")
    
    async def stop_maintenance(self) -> None:
        """Stop background maintenance tasks."""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped command manager maintenance tasks")
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up command tracking data."""
        while self._running:
            try:
                # Clean up every 5 minutes
                await asyncio.sleep(300)
                
                if not self._running:
                    break
                
                # Clean up command tracking data
                registry = get_command_registry()
                registry.cleanup_tracking()
                
                logger.debug("Completed command cleanup cycle")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in command cleanup loop: {e}", exc_info=True)
                # Continue running even if cleanup fails
                await asyncio.sleep(60)  # Wait 1 minute before retrying


# Global manager instance
_manager: Optional[CommandManager] = None


def get_command_manager() -> CommandManager:
    """Get the global command manager instance."""
    global _manager
    
    if _manager is None:
        _manager = CommandManager()
    
    return _manager
