"""Session management for claude-code-gui."""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from PyQt6.QtCore import QSettings, QStandardPaths, QTimer, QObject, pyqtSignal

from .models import (
    ConversationSession,
    ApplicationSettings,
    SessionMetadata,
    Message,
    MessageRole,
)


class SessionManager(QObject):
    """Manages conversation sessions and application settings."""

    # Signals
    session_saved = pyqtSignal(str)  # session_id
    session_loaded = pyqtSignal(str)  # session_id
    settings_changed = pyqtSignal()

    def __init__(self, app_name: str = "claude-code-gui"):
        super().__init__()
        self.app_name = app_name
        self.settings = QSettings(app_name, app_name)
        self.current_session: Optional[ConversationSession] = None
        self.app_settings = self._load_app_settings()

        # Set up session storage directory
        if not self.app_settings.session_storage_path:
            self.app_settings.session_storage_path = self._get_default_storage_path()

        Path(self.app_settings.session_storage_path).mkdir(parents=True, exist_ok=True)

        # Set up auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        if self.app_settings.auto_save_enabled:
            self.auto_save_timer.start(self.app_settings.auto_save_interval * 1000)

    def _get_default_storage_path(self) -> str:
        """Get the default storage path for sessions."""
        data_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        return os.path.join(data_dir, "sessions")

    def _load_app_settings(self) -> ApplicationSettings:
        """Load application settings from QSettings."""
        settings_data = self.settings.value("app_settings", {})
        if isinstance(settings_data, dict):
            return ApplicationSettings.from_dict(settings_data)
        return ApplicationSettings()

    def save_app_settings(self):
        """Save application settings to QSettings."""
        self.settings.setValue("app_settings", self.app_settings.to_dict())
        self.settings_changed.emit()

        # Update auto-save timer if needed
        if self.app_settings.auto_save_enabled:
            self.auto_save_timer.start(self.app_settings.auto_save_interval * 1000)
        else:
            self.auto_save_timer.stop()

    def create_new_session(self, title: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session."""
        session = ConversationSession()
        if title:
            session.title = title
        else:
            session.title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Apply default settings
        if self.app_settings.default_model:
            session.model = self.app_settings.default_model
        if self.app_settings.default_system_prompt:
            session.system_prompt = self.app_settings.default_system_prompt
        session.tools_enabled = self.app_settings.default_tools.copy()

        self.current_session = session
        return session

    def save_session(self, session: Optional[ConversationSession] = None) -> bool:
        """Save a conversation session to disk."""
        if session is None:
            session = self.current_session

        if session is None:
            return False

        try:
            session_path = (
                Path(self.app_settings.session_storage_path) / f"{session.id}.json"
            )
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

            # Update recent sessions
            self._update_recent_sessions(session.id)

            self.session_saved.emit(session.id)
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load a conversation session from disk."""
        try:
            session_path = (
                Path(self.app_settings.session_storage_path) / f"{session_id}.json"
            )
            if not session_path.exists():
                return None

            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session = ConversationSession.from_dict(data)
            self.current_session = session

            # Update recent sessions
            self._update_recent_sessions(session_id)

            self.session_loaded.emit(session_id)
            return session
        except Exception as e:
            print(f"Error loading session: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session."""
        try:
            session_path = (
                Path(self.app_settings.session_storage_path) / f"{session_id}.json"
            )
            if session_path.exists():
                session_path.unlink()

            # Remove from recent sessions
            recent = self.get_recent_session_ids()
            if session_id in recent:
                recent.remove(session_id)
                self.settings.setValue("recent_sessions", recent)

            # Clear current session if it's the one being deleted
            if self.current_session and self.current_session.id == session_id:
                self.current_session = None

            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

    def list_sessions(self) -> List[SessionMetadata]:
        """List all available sessions with metadata."""
        sessions = []
        session_dir = Path(self.app_settings.session_storage_path)

        for session_file in session_dir.glob("*.json"):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Create metadata without loading full session
                metadata = SessionMetadata(
                    id=data["id"],
                    title=data["title"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    message_count=len(data.get("messages", [])),
                    total_tokens=data.get("total_tokens", 0),
                    total_cost=data.get("total_cost", 0.0),
                )
                sessions.append(metadata)
            except Exception as e:
                print(f"Error reading session {session_file}: {e}")

        # Sort by updated date, most recent first
        sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return sessions

    def get_recent_session_ids(self) -> List[str]:
        """Get list of recent session IDs."""
        recent = self.settings.value("recent_sessions", [])
        if isinstance(recent, list):
            return recent[: self.app_settings.max_recent_sessions]
        return []

    def get_recent_sessions(self) -> List[SessionMetadata]:
        """Get metadata for recent sessions."""
        recent_ids = self.get_recent_session_ids()
        all_sessions = {s.id: s for s in self.list_sessions()}

        recent_sessions = []
        for session_id in recent_ids:
            if session_id in all_sessions:
                recent_sessions.append(all_sessions[session_id])

        return recent_sessions

    def _update_recent_sessions(self, session_id: str):
        """Update the recent sessions list."""
        recent = self.get_recent_session_ids()

        # Remove if already in list
        if session_id in recent:
            recent.remove(session_id)

        # Add to front
        recent.insert(0, session_id)

        # Trim to max size
        recent = recent[: self.app_settings.max_recent_sessions]

        self.settings.setValue("recent_sessions", recent)

    def _auto_save(self):
        """Auto-save the current session."""
        if self.current_session:
            self.save_session()

    def cleanup_old_sessions(self):
        """Remove sessions older than retention period."""
        if self.app_settings.history_retention_days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(
            days=self.app_settings.history_retention_days
        )
        sessions = self.list_sessions()

        for session in sessions:
            if session.updated_at < cutoff_date:
                self.delete_session(session.id)

    def export_session(self, session_id: str, format: str, output_path: str) -> bool:
        """Export a session to various formats."""
        session = self.load_session(session_id)
        if not session:
            return False

        try:
            if format == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

            elif format == "markdown":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"# {session.title}\n\n")
                    f.write(
                        f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write(
                        f"Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )

                    for msg in session.messages:
                        role = msg.role.value.title()
                        f.write(f"## {role}\n\n")
                        f.write(f"{msg.content}\n\n")
                        f.write(f"*{msg.timestamp.strftime('%H:%M:%S')}*\n\n")
                        f.write("---\n\n")

            elif format == "html":
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>{session.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .message {{ margin: 20px 0; padding: 15px; border-radius: 10px; }}
        .user {{ background-color: #e3f2fd; }}
        .assistant {{ background-color: #f5f5f5; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{session.title}</h1>
    <p>Created: {session.created_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
    <p>Updated: {session.updated_at.strftime("%Y-%m-%d %H:%M:%S")}</p>
    <hr>
""")

                    for msg in session.messages:
                        css_class = msg.role.value
                        f.write(f"""    <div class="message {css_class}">
        <strong>{msg.role.value.title()}</strong>
        <p>{msg.content.replace(chr(10), "<br>")}</p>
        <span class="timestamp">{msg.timestamp.strftime("%H:%M:%S")}</span>
    </div>
""")

                    f.write("""</body>
</html>""")

            else:
                return False

            return True
        except Exception as e:
            print(f"Error exporting session: {e}")
            return False

    def search_sessions(self, query: str) -> List[SessionMetadata]:
        """Search through all sessions for a query string."""
        results = []
        query_lower = query.lower()

        for metadata in self.list_sessions():
            # Quick check in title
            if query_lower in metadata.title.lower():
                results.append(metadata)
                continue

            # Load full session for content search
            session = self.load_session(metadata.id)
            if session:
                for msg in session.messages:
                    if query_lower in msg.content.lower():
                        results.append(metadata)
                        break

        return results

    def get_current_session(self) -> Optional[ConversationSession]:
        """Get the current active session."""
        return self.current_session

    def set_current_session(self, session: ConversationSession):
        """Set the current active session."""
        self.current_session = session

