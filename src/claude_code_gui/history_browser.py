"""History browser widget for claude-code-gui."""

from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QSplitter,
    QListWidgetItem,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .session_manager import SessionManager
from .models import ConversationSession, SessionMetadata, MessageRole


class HistoryBrowserWidget(QWidget):
    """Widget for browsing conversation history."""

    # Signals
    session_selected = pyqtSignal(str)  # session_id
    session_opened = pyqtSignal(str)  # session_id

    def __init__(self, session_manager: SessionManager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.current_session_id: Optional[str] = None
        self.init_ui()
        self.refresh_sessions()

        # Connect to session manager signals
        self.session_manager.session_saved.connect(self.refresh_sessions)
        self.session_manager.session_loaded.connect(self.refresh_sessions)

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Search bar
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search sessions...")
        self.search_input.textChanged.connect(self.filter_sessions)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_sessions)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        layout.addLayout(search_layout)

        # Filter bar
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Last Updated", "Created", "Title", "Message Count"])
        self.sort_combo.currentTextChanged.connect(self.sort_sessions)
        filter_layout.addWidget(self.sort_combo)

        filter_layout.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_sessions)
        filter_layout.addWidget(self.refresh_button)

        layout.addLayout(filter_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Session list
        self.session_list = QListWidget()
        self.session_list.currentItemChanged.connect(self.on_session_selected)
        self.session_list.itemDoubleClicked.connect(self.on_session_double_clicked)
        splitter.addWidget(self.session_list)

        # Session preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        self.preview_title = QLabel("Select a session to preview")
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        preview_layout.addWidget(self.preview_title)

        self.preview_info = QLabel("")
        preview_layout.addWidget(self.preview_info)

        self.preview_content = QTextEdit()
        self.preview_content.setReadOnly(True)
        preview_layout.addWidget(self.preview_content)

        # Preview actions
        preview_actions = QHBoxLayout()

        self.open_button = QPushButton("Open Session")
        self.open_button.clicked.connect(self.open_current_session)
        self.open_button.setEnabled(False)
        preview_actions.addWidget(self.open_button)

        self.export_button = QPushButton("Export...")
        self.export_button.clicked.connect(self.export_current_session)
        self.export_button.setEnabled(False)
        preview_actions.addWidget(self.export_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_current_session)
        self.delete_button.setEnabled(False)
        preview_actions.addWidget(self.delete_button)

        preview_actions.addStretch()
        preview_layout.addLayout(preview_actions)

        splitter.addWidget(preview_widget)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

        self.setLayout(layout)

    def refresh_sessions(self):
        """Refresh the session list."""
        self.session_list.clear()
        self.all_sessions = self.session_manager.list_sessions()
        self.display_sessions(self.all_sessions)

    def display_sessions(self, sessions: list[SessionMetadata]):
        """Display sessions in the list."""
        self.session_list.clear()

        for session_meta in sessions:
            # Create list item
            item_text = f"{session_meta.title}\n"
            item_text += (
                f"Updated: {session_meta.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
            )
            item_text += f"{session_meta.message_count} messages"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, session_meta.id)

            self.session_list.addItem(item)

    def filter_sessions(self, text: str):
        """Filter sessions by search text."""
        if not text:
            self.display_sessions(self.all_sessions)
            return

        filtered = []
        text_lower = text.lower()

        for session in self.all_sessions:
            if text_lower in session.title.lower():
                filtered.append(session)

        self.display_sessions(filtered)

    def search_sessions(self):
        """Perform full content search."""
        query = self.search_input.text().strip()
        if not query:
            self.refresh_sessions()
            return

        results = self.session_manager.search_sessions(query)
        self.display_sessions(results)

    def sort_sessions(self, sort_by: str):
        """Sort sessions by selected criteria."""
        if sort_by == "Last Updated":
            self.all_sessions.sort(key=lambda x: x.updated_at, reverse=True)
        elif sort_by == "Created":
            self.all_sessions.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "Title":
            self.all_sessions.sort(key=lambda x: x.title.lower())
        elif sort_by == "Message Count":
            self.all_sessions.sort(key=lambda x: x.message_count, reverse=True)

        # Reapply filter if active
        filter_text = self.search_input.text()
        if filter_text:
            self.filter_sessions(filter_text)
        else:
            self.display_sessions(self.all_sessions)

    def on_session_selected(self, current, previous):
        """Handle session selection."""
        if not current:
            self.clear_preview()
            return

        session_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_session_id = session_id
        self.load_preview(session_id)

        # Enable action buttons
        self.open_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.delete_button.setEnabled(True)

        # Emit signal
        self.session_selected.emit(session_id)

    def on_session_double_clicked(self, item):
        """Handle session double-click."""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self.session_opened.emit(session_id)

    def load_preview(self, session_id: str):
        """Load session preview."""
        session = self.session_manager.load_session(session_id)
        if not session:
            return

        # Update title and info
        self.preview_title.setText(session.title)

        info_text = f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        info_text += f"Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        info_text += f"Messages: {len(session.messages)}\n"
        info_text += f"Cost: ${session.total_cost:.4f}"
        if session.model:
            info_text += f"\nModel: {session.model}"

        self.preview_info.setText(info_text)

        # Update content preview
        self.preview_content.clear()

        # Show last few messages
        messages_to_show = session.messages[-10:]  # Last 10 messages

        for msg in messages_to_show:
            if msg.role == MessageRole.USER:
                self.preview_content.append(f"User: {msg.content[:200]}...")
            elif msg.role == MessageRole.ASSISTANT:
                self.preview_content.append(f"Claude: {msg.content[:200]}...")
            self.preview_content.append("")

    def clear_preview(self):
        """Clear the preview pane."""
        self.preview_title.setText("Select a session to preview")
        self.preview_info.setText("")
        self.preview_content.clear()
        self.current_session_id = None

        # Disable action buttons
        self.open_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def open_current_session(self):
        """Open the currently selected session."""
        if self.current_session_id:
            self.session_opened.emit(self.current_session_id)

    def export_current_session(self):
        """Export the currently selected session."""
        # This would typically open a file dialog
        # For now, just emit a signal or call parent method
        pass

    def delete_current_session(self):
        """Delete the currently selected session."""
        if self.current_session_id:
            # This would typically show a confirmation dialog
            # For now, just delete and refresh
            if self.session_manager.delete_session(self.current_session_id):
                self.refresh_sessions()
                self.clear_preview()
