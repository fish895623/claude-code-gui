"""Claude Code SDK integration module for PyQt6 GUI."""

import asyncio
from pathlib import Path
from typing import AsyncIterator, Optional, List, Dict, Any
from dataclasses import dataclass, field

from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    Message,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    ResultMessage,
    ContentBlock,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)
from typing import Literal

from .rules_parser import RulesParser

PermissionMode = Literal["default", "acceptEdits", "bypassPermissions"]


@dataclass
class QueryConfig:
    """Configuration for Claude Code queries."""

    system_prompt: Optional[str] = None
    max_turns: Optional[int] = None
    allowed_tools: List[str] = field(default_factory=list)
    disallowed_tools: List[str] = field(default_factory=list)
    permission_mode: Optional[PermissionMode] = None
    cwd: Optional[Path] = None
    model: Optional[str] = None
    custom_rules_xml: Optional[str] = None  # XML rules to apply


class ClaudeCodeSDKWrapper:
    """Wrapper for Claude Code SDK with PyQt6 integration."""

    def __init__(self, config: Optional[QueryConfig] = None):
        self.config = config or QueryConfig()
        self._current_session_id: Optional[str] = None

    async def send_query(
        self, prompt: str, config_override: Optional[QueryConfig] = None
    ) -> AsyncIterator[Message]:
        """Send a query to Claude Code and yield messages."""
        config = config_override or self.config

        # Build system prompt with rules if provided
        system_prompt_parts = []

        if config.system_prompt:
            system_prompt_parts.append(config.system_prompt)

        if config.custom_rules_xml:
            rules, error = RulesParser.parse_xml(config.custom_rules_xml)
            if not error and rules:
                rules_prompt = RulesParser.rules_to_prompt(rules)
                if rules_prompt:
                    system_prompt_parts.append(rules_prompt)

        combined_system_prompt = (
            "\n\n".join(system_prompt_parts) if system_prompt_parts else None
        )

        options = ClaudeCodeOptions(
            system_prompt=combined_system_prompt,
            max_turns=config.max_turns,
            allowed_tools=config.allowed_tools,
            disallowed_tools=config.disallowed_tools,
            permission_mode=config.permission_mode,
            cwd=str(config.cwd) if config.cwd else None,
            model=config.model,
        )

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                self._current_session_id = message.session_id
            yield message

    def parse_message(self, message: Message) -> Dict[str, Any]:
        """Parse a message into a dictionary for Qt signal emission."""
        if isinstance(message, UserMessage):
            return {
                "type": "user",
                "content": message.content,
            }

        elif isinstance(message, AssistantMessage):
            content_blocks = []
            for block in message.content:
                if isinstance(block, TextBlock):
                    content_blocks.append(
                        {
                            "type": "text",
                            "text": block.text,
                        }
                    )
                elif isinstance(block, ToolUseBlock):
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                elif isinstance(block, ToolResultBlock):
                    content_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "output": getattr(block, "output", ""),
                            "is_error": block.is_error,
                        }
                    )

            return {
                "type": "assistant",
                "content": content_blocks,
            }

        elif isinstance(message, SystemMessage):
            return {
                "type": "system",
                "subtype": message.subtype,
                "data": message.data,
            }

        elif isinstance(message, ResultMessage):
            return {
                "type": "result",
                "subtype": message.subtype,
                "duration_ms": message.duration_ms,
                "duration_api_ms": message.duration_api_ms,
                "is_error": message.is_error,
                "num_turns": message.num_turns,
                "session_id": message.session_id,
                "total_cost_usd": message.total_cost_usd,
                "usage": message.usage,
                "result": message.result,
            }

        return {"type": "unknown", "data": str(message)}

    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session_id
