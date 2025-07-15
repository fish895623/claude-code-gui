"""Data models for claude-code-gui session management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class MessageRole(Enum):
    """Role of the message sender."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """Represents a single message in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationSession:
    """Represents a complete conversation session."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Session-specific settings
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    tools_enabled: List[str] = field(default_factory=list)
    sdk_session_id: Optional[str] = (
        None  # Claude SDK session ID for resuming conversations
    )
    custom_rules: Optional[str] = None  # XML rules for this session

    # Usage statistics
    total_tokens: int = 0
    total_cost: float = 0.0

    # Subtasks
    subtasks: List["Subtask"] = field(default_factory=list)

    def add_message(self, role: MessageRole, content: str, **metadata) -> Message:
        """Add a new message to the conversation."""
        message = Message(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.now()
        return message

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "tools_enabled": self.tools_enabled,
            "sdk_session_id": self.sdk_session_id,
            "custom_rules": self.custom_rules,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "subtasks": [task.to_dict() for task in self.subtasks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSession":
        """Create session from dictionary."""
        session = cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", "New Conversation"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            model=data.get("model"),
            system_prompt=data.get("system_prompt"),
            tools_enabled=data.get("tools_enabled", []),
            sdk_session_id=data.get("sdk_session_id"),
            custom_rules=data.get("custom_rules"),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
        )
        session.messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        session.subtasks = [
            Subtask.from_dict(task) for task in data.get("subtasks", [])
        ]
        return session


@dataclass
class ApplicationSettings:
    """Application-wide settings and preferences."""

    # Window settings
    window_geometry: Optional[Dict[str, int]] = None
    window_state: Optional[bytes] = None

    # UI preferences
    theme: str = "system"
    font_family: str = "default"
    font_size: int = 12

    # Session management
    auto_save_enabled: bool = True
    auto_save_interval: int = 300  # seconds
    max_recent_sessions: int = 10
    session_storage_path: str = ""
    restore_last_session: bool = True  # Whether to restore the last session on startup

    # Default query settings
    default_model: Optional[str] = None
    default_system_prompt: Optional[str] = None
    default_tools: List[str] = field(default_factory=list)
    default_rules: Optional[str] = None  # Default XML rules for new sessions
    default_permission_mode: str = "acceptEdits"  # acceptEdits, bypassPermissions
    enable_plan_mode: bool = False  # Whether to use plan mode by default
    enable_dangerous_skip: bool = False  # Whether to enable dangerous skip mode

    # History settings
    history_retention_days: int = 30
    export_formats: List[str] = field(
        default_factory=lambda: ["json", "markdown", "html"]
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization."""
        return {
            "window_geometry": self.window_geometry,
            "window_state": self.window_state.hex() if self.window_state else None,
            "theme": self.theme,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "auto_save_enabled": self.auto_save_enabled,
            "auto_save_interval": self.auto_save_interval,
            "max_recent_sessions": self.max_recent_sessions,
            "session_storage_path": self.session_storage_path,
            "restore_last_session": self.restore_last_session,
            "default_model": self.default_model,
            "default_system_prompt": self.default_system_prompt,
            "default_tools": self.default_tools,
            "default_rules": self.default_rules,
            "default_permission_mode": self.default_permission_mode,
            "enable_plan_mode": self.enable_plan_mode,
            "enable_dangerous_skip": self.enable_dangerous_skip,
            "history_retention_days": self.history_retention_days,
            "export_formats": self.export_formats,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationSettings":
        """Create settings from dictionary."""
        settings = cls()
        if data.get("window_geometry"):
            settings.window_geometry = data["window_geometry"]
        if data.get("window_state"):
            settings.window_state = bytes.fromhex(data["window_state"])

        settings.theme = data.get("theme", "system")
        settings.font_family = data.get("font_family", "default")
        settings.font_size = data.get("font_size", 12)
        settings.auto_save_enabled = data.get("auto_save_enabled", True)
        settings.auto_save_interval = data.get("auto_save_interval", 300)
        settings.max_recent_sessions = data.get("max_recent_sessions", 10)
        settings.session_storage_path = data.get("session_storage_path", "")
        settings.restore_last_session = data.get("restore_last_session", True)
        settings.default_model = data.get("default_model")
        settings.default_system_prompt = data.get("default_system_prompt")
        settings.default_tools = data.get("default_tools", [])
        settings.default_rules = data.get("default_rules")
        settings.default_permission_mode = data.get(
            "default_permission_mode", "acceptEdits"
        )
        settings.enable_plan_mode = data.get("enable_plan_mode", False)
        settings.enable_dangerous_skip = data.get("enable_dangerous_skip", False)
        settings.history_retention_days = data.get("history_retention_days", 30)
        settings.export_formats = data.get(
            "export_formats", ["json", "markdown", "html"]
        )

        return settings


@dataclass
class SessionMetadata:
    """Lightweight metadata for session listing."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int
    total_cost: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """Create metadata from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            message_count=data["message_count"],
            total_tokens=data["total_tokens"],
            total_cost=data["total_cost"],
        )

    @classmethod
    def from_session(cls, session: ConversationSession) -> "SessionMetadata":
        """Create metadata from a conversation session."""
        return cls(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
            total_tokens=session.total_tokens,
            total_cost=session.total_cost,
        )


@dataclass
class Subtask:
    """Represents a subtask generated from main task analysis."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    is_completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    priority: int = 0  # 0=normal, 1=high, -1=low

    def to_dict(self) -> Dict[str, Any]:
        """Convert subtask to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_completed": self.is_completed,
            "created_at": self.created_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subtask":
        """Create subtask from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description", ""),
            is_completed=data.get("is_completed", False),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            priority=data.get("priority", 0),
        )
