"""Qt worker threads for async Claude Code operations."""

import asyncio
import sys
from typing import Optional, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal, QObject

from .sdk_integration import ClaudeCodeSDKWrapper, QueryConfig


class ClaudeQueryWorker(QObject):
    """Worker for executing Claude Code queries in a separate thread."""

    # Signals
    message_received = pyqtSignal(dict)  # Emits parsed message data
    query_started = pyqtSignal()
    query_completed = pyqtSignal(dict)  # Emits result message data
    error_occurred = pyqtSignal(str)

    def __init__(self, sdk_wrapper: ClaudeCodeSDKWrapper):
        super().__init__()
        self.sdk_wrapper = sdk_wrapper
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def _run_query(self, prompt: str, config: Optional[QueryConfig] = None):
        """Run the query and emit signals for each message."""
        try:
            self.query_started.emit()
            self._is_running = True

            async for message in self.sdk_wrapper.send_query(prompt, config):
                if not self._is_running:
                    break

                parsed = self.sdk_wrapper.parse_message(message)
                self.message_received.emit(parsed)

                # If this is a result message, also emit completion signal
                if parsed["type"] == "result":
                    self.query_completed.emit(parsed)

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._is_running = False

    def run_query(self, prompt: str, config: Optional[QueryConfig] = None):
        """Entry point for running a query."""
        # Create new event loop for this thread
        if sys.platform == "win32":
            # Windows requires ProactorEventLoop for subprocess support
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        else:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._run_query(prompt, config))
        finally:
            self._loop.close()
            self._loop = None

    def stop(self):
        """Stop the current query."""
        self._is_running = False
        if self._loop and self._loop.is_running():
            self._loop.stop()


class ClaudeQueryThread(QThread):
    """Thread for running Claude queries."""

    def __init__(
        self,
        worker: ClaudeQueryWorker,
        prompt: str,
        config: Optional[QueryConfig] = None,
    ):
        super().__init__()
        self.worker = worker
        self.prompt = prompt
        self.config = config

        # Move worker to this thread
        self.worker.moveToThread(self)

    def run(self):
        """Run the query in this thread."""
        self.worker.run_query(self.prompt, self.config)

    def stop(self):
        """Stop the query and thread."""
        self.worker.stop()
        self.quit()
        self.wait()
