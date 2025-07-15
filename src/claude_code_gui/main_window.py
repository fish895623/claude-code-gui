"""Main window for Claude Code GUI."""

from typing import Optional, Union
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QSplitter,
    QGroupBox,
    QLabel,
    QStatusBar,
    QMessageBox,
    QScrollArea,
    QMenuBar,
    QMenu,
    QFileDialog,
    QListWidget,
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QFont,
    QTextCursor,
    QTextCharFormat,
    QColor,
    QAction,
    QCloseEvent,
)

from .sdk_integration import ClaudeCodeSDKWrapper, QueryConfig
from .workers import ClaudeQueryWorker, ClaudeQueryThread
from .session_manager import SessionManager
from .models import MessageRole, ConversationSession


class MessageDisplay(QTextEdit):
    """Custom QTextEdit for displaying Claude messages with formatting."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))

    def append_user_message(self, content: str):
        """Append a user message with formatting."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # User label
        format = QTextCharFormat()
        format.setForeground(QColor(0, 100, 200))
        format.setFontWeight(QFont.Weight.Bold)
        cursor.insertText("User: ", format)

        # User content
        format = QTextCharFormat()
        cursor.insertText(content + "\n\n", format)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_assistant_message(self, content_blocks: list):
        """Append an assistant message with formatting."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Assistant label
        format = QTextCharFormat()
        format.setForeground(QColor(200, 100, 0))
        format.setFontWeight(QFont.Weight.Bold)
        cursor.insertText("Claude: ", format)

        # Process content blocks
        for block in content_blocks:
            if block["type"] == "text":
                format = QTextCharFormat()
                cursor.insertText(block["text"], format)
            elif block["type"] == "tool_use":
                format = QTextCharFormat()
                format.setForeground(QColor(100, 100, 100))
                format.setFontItalic(True)
                cursor.insertText(f"\n[Tool: {block['name']}]\n", format)
            elif block["type"] == "tool_result":
                format = QTextCharFormat()
                format.setForeground(
                    QColor(50, 150, 50)
                    if not block["is_error"]
                    else QColor(200, 50, 50)
                )
                cursor.insertText(
                    (
                        f"[Result: {block['output'][:200]}...]\n"
                        if len(block["output"]) > 200
                        else f"[Result: {block['output']}]\n"
                    ),
                    format,
                )

        cursor.insertText("\n\n")
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_system_message(self, subtype: str, data: dict):
        """Append a system message with formatting."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format = QTextCharFormat()
        format.setForeground(QColor(150, 150, 150))
        format.setFontItalic(True)
        cursor.insertText(f"[System: {subtype}]\n", format)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class ClaudeCodeMainWindow(QMainWindow):
    """Main window for Claude Code GUI application."""

    def __init__(self):
        super().__init__()
        self.sdk_wrapper = ClaudeCodeSDKWrapper()
        self.current_thread: Optional[ClaudeQueryThread] = None
        self.session_manager = SessionManager()
        self.init_ui()
        self.init_menu_bar()
        self.restore_window_state()

        # Start with a new session
        self.session_manager.create_new_session()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Claude Code GUI")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - Chat interface
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)

        # Message display
        self.message_display = MessageDisplay()
        chat_layout.addWidget(self.message_display)

        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter your prompt here...")
        self.input_field.returnPressed.connect(self.send_query)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_query)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_query)
        self.stop_button.setEnabled(False)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        input_layout.addWidget(self.stop_button)

        chat_layout.addLayout(input_layout)

        splitter.addWidget(chat_widget)

        # Right panel - Info and config
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)

        # Session info
        session_group = QGroupBox("Session Info")
        session_layout = QVBoxLayout()
        self.session_label = QLabel("No active session")
        self.cost_label = QLabel("Cost: $0.00")
        self.turns_label = QLabel("Turns: 0")
        session_layout.addWidget(self.session_label)
        session_layout.addWidget(self.cost_label)
        session_layout.addWidget(self.turns_label)
        session_group.setLayout(session_layout)
        info_layout.addWidget(session_group)

        # Tool status
        tools_group = QGroupBox("Tool Activity")
        tools_layout = QVBoxLayout()
        self.tools_display = QTextEdit()
        self.tools_display.setReadOnly(True)
        self.tools_display.setMaximumHeight(200)
        tools_layout.addWidget(self.tools_display)
        tools_group.setLayout(tools_layout)
        info_layout.addWidget(tools_group)

        info_layout.addStretch()

        splitter.addWidget(info_widget)
        splitter.setSizes([800, 400])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def init_menu_bar(self):
        """Initialize the menu bar."""
        menubar = self.menuBar()
        if not menubar:
            return

        # File menu
        file_menu = menubar.addMenu("File")
        if not file_menu:
            return

        # New Session
        new_session_action = QAction("New Session", self)
        new_session_action.setShortcut("Ctrl+N")
        new_session_action.triggered.connect(self.new_session)
        file_menu.addAction(new_session_action)

        # Open Session
        open_session_action = QAction("Open Session...", self)
        open_session_action.setShortcut("Ctrl+O")
        open_session_action.triggered.connect(self.open_session)
        file_menu.addAction(open_session_action)

        # Save Session
        save_session_action = QAction("Save Session", self)
        save_session_action.setShortcut("Ctrl+S")
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)

        file_menu.addSeparator()

        # Recent Sessions submenu
        self.recent_menu = file_menu.addMenu("Recent Sessions")
        self.update_recent_menu()

        file_menu.addSeparator()

        # Export Session
        export_action = QAction("Export Session...", self)
        export_action.triggered.connect(self.export_session)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        # Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        if not edit_menu:
            return

        # Search Sessions
        search_action = QAction("Search Sessions...", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.search_sessions)
        edit_menu.addAction(search_action)

        # Settings
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)

        # Session menu
        session_menu = menubar.addMenu("Session")
        if not session_menu:
            return

        # Clear Current Session
        clear_action = QAction("Clear Current Session", self)
        clear_action.triggered.connect(self.clear_session)
        session_menu.addAction(clear_action)

        # Delete Session
        delete_action = QAction("Delete Session...", self)
        delete_action.triggered.connect(self.delete_session)
        session_menu.addAction(delete_action)

    def send_query(self):
        """Send a query to Claude Code."""
        prompt = self.input_field.text().strip()
        if not prompt:
            return

        # Disable input while processing
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Display user message
        self.message_display.append_user_message(prompt)

        # Add to current session
        if self.session_manager.current_session:
            self.session_manager.current_session.add_message(MessageRole.USER, prompt)

        # Create worker and thread
        worker = ClaudeQueryWorker(self.sdk_wrapper)
        self.current_thread = ClaudeQueryThread(worker, prompt)

        # Connect signals
        worker.message_received.connect(self.handle_message)
        worker.query_started.connect(self.handle_query_started)
        worker.query_completed.connect(self.handle_query_completed)
        worker.error_occurred.connect(self.handle_error)

        # Start thread
        self.current_thread.start()
        self.status_bar.showMessage("Processing query...")

    def stop_query(self):
        """Stop the current query."""
        if self.current_thread:
            self.current_thread.stop()
            self.status_bar.showMessage("Query stopped")

    def handle_message(self, message_data: dict):
        """Handle incoming message from Claude."""
        msg_type = message_data["type"]

        if msg_type == "assistant":
            self.message_display.append_assistant_message(message_data["content"])

            # Add to current session
            if self.session_manager.current_session:
                # Extract text content from blocks
                text_content = ""
                for block in message_data["content"]:
                    if block["type"] == "text":
                        text_content += block["text"]

                self.session_manager.current_session.add_message(
                    MessageRole.ASSISTANT, text_content
                )

            # Update tool activity
            for block in message_data["content"]:
                if block["type"] == "tool_use":
                    self.tools_display.append(f"Using {block['name']}")
                elif block["type"] == "tool_result":
                    status = "✓" if not block["is_error"] else "✗"
                    self.tools_display.append(f"  {status} Result received")

        elif msg_type == "system":
            self.message_display.append_system_message(
                message_data["subtype"], message_data["data"]
            )

        elif msg_type == "result":
            # Update session info
            self.session_label.setText(f"Session: {message_data['session_id'][:8]}...")
            if message_data.get("total_cost_usd"):
                self.cost_label.setText(f"Cost: ${message_data['total_cost_usd']:.4f}")
                # Update session cost
                if self.session_manager.current_session:
                    self.session_manager.current_session.total_cost = message_data[
                        "total_cost_usd"
                    ]
            self.turns_label.setText(f"Turns: {message_data['num_turns']}")

            # Auto-save session
            if self.session_manager.app_settings.auto_save_enabled:
                self.session_manager.save_session()

    def handle_query_started(self):
        """Handle query started signal."""
        self.tools_display.clear()

    def handle_query_completed(self, result_data: dict):
        """Handle query completion."""
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        if result_data["is_error"]:
            self.status_bar.showMessage("Query completed with error")
        else:
            duration_s = result_data["duration_ms"] / 1000
            self.status_bar.showMessage(f"Query completed in {duration_s:.1f}s")

    def handle_error(self, error_msg: str):
        """Handle error during query."""
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_bar.showMessage("Error occurred")

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        """Handle window close event."""
        if self.current_thread and self.current_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Query in Progress",
                "A query is still running. Do you want to stop it and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.stop_query()
                self.current_thread.wait()
                if a0:
                    a0.accept()
            else:
                if a0:
                    a0.ignore()
        else:
            # Save window state
            self.save_window_state()
            if a0:
                a0.accept()

    def save_window_state(self):
        """Save window geometry and state."""
        self.session_manager.app_settings.window_geometry = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
        }
        state_bytes = self.saveState()
        self.session_manager.app_settings.window_state = (
            bytes(state_bytes.data()) if state_bytes else None
        )
        self.session_manager.save_app_settings()

    def restore_window_state(self):
        """Restore window geometry and state."""
        settings = self.session_manager.app_settings
        if settings.window_geometry:
            self.setGeometry(
                settings.window_geometry["x"],
                settings.window_geometry["y"],
                settings.window_geometry["width"],
                settings.window_geometry["height"],
            )
        if settings.window_state:
            self.restoreState(settings.window_state)

    def new_session(self):
        """Create a new session."""
        # Save current session if modified
        if (
            self.session_manager.current_session
            and self.session_manager.current_session.messages
        ):
            reply = QMessageBox.question(
                self,
                "Save Session?",
                "Do you want to save the current session?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                self.save_session()

        # Create new session
        self.session_manager.create_new_session()
        self.message_display.clear()
        self.tools_display.clear()
        self.update_session_info()
        self.status_bar.showMessage("New session created")

    def open_session(self):
        """Open an existing session."""
        dialog = SessionSelectionDialog(self.session_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_session_id = dialog.get_selected_session_id()
            if selected_session_id:
                self.load_session(selected_session_id)

    def load_session(self, session_id: str):
        """Load a specific session."""
        session = self.session_manager.load_session(session_id)
        if session:
            # Clear and reload display
            self.message_display.clear()

            # Display all messages
            for msg in session.messages:
                if msg.role == MessageRole.USER:
                    self.message_display.append_user_message(msg.content)
                elif msg.role == MessageRole.ASSISTANT:
                    self.message_display.append_assistant_message(
                        [{"type": "text", "text": msg.content}]
                    )

            self.update_session_info()
            self.update_recent_menu()
            self.status_bar.showMessage(f"Loaded session: {session.title}")

    def save_session(self):
        """Save the current session."""
        if self.session_manager.save_session():
            self.status_bar.showMessage("Session saved")
            self.update_recent_menu()
        else:
            self.status_bar.showMessage("Failed to save session")

    def update_recent_menu(self):
        """Update the recent sessions menu."""
        if self.recent_menu:
            self.recent_menu.clear()

        recent_sessions = self.session_manager.get_recent_sessions()
        for session_meta in recent_sessions[:10]:
            action = QAction(session_meta.title, self)
            action.triggered.connect(
                lambda checked, sid=session_meta.id: self.load_session(sid)
            )
            if self.recent_menu:
                self.recent_menu.addAction(action)

        if not recent_sessions:
            action = QAction("(No recent sessions)", self)
            action.setEnabled(False)
            if self.recent_menu:
                self.recent_menu.addAction(action)

    def export_session(self):
        """Export the current session."""
        if not self.session_manager.current_session:
            QMessageBox.information(self, "No Session", "No active session to export.")
            return

        format, _ = QFileDialog.getSaveFileName(
            self,
            "Export Session",
            f"{self.session_manager.current_session.title}.json",
            "JSON (*.json);;Markdown (*.md);;HTML (*.html)",
        )

        if format:
            ext = Path(format).suffix[1:]  # Remove the dot
            if self.session_manager.export_session(
                self.session_manager.current_session.id, ext, format
            ):
                self.status_bar.showMessage(f"Session exported to {format}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export session.")

    def search_sessions(self):
        """Search through all sessions."""
        # TODO: Implement search dialog
        QMessageBox.information(
            self, "Coming Soon", "Session search will be implemented soon."
        )

    def show_settings(self):
        """Show settings dialog."""
        # TODO: Implement settings dialog
        QMessageBox.information(
            self, "Coming Soon", "Settings dialog will be implemented soon."
        )

    def clear_session(self):
        """Clear the current session."""
        reply = QMessageBox.question(
            self,
            "Clear Session?",
            "This will clear all messages in the current session. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.session_manager.current_session:
                self.session_manager.current_session.messages.clear()
                self.message_display.clear()
                self.tools_display.clear()
                self.update_session_info()
                self.status_bar.showMessage("Session cleared")

    def delete_session(self):
        """Delete a session."""
        dialog = SessionSelectionDialog(
            self.session_manager, self, "Select session to delete"
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_session_id = dialog.get_selected_session_id()
            if selected_session_id:
                reply = QMessageBox.question(
                    self,
                    "Delete Session?",
                    "This will permanently delete the selected session. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    if self.session_manager.delete_session(selected_session_id):
                        self.status_bar.showMessage("Session deleted")
                        self.update_recent_menu()

                        # If deleted current session, create new one
                        if (
                            self.session_manager.current_session
                            and self.session_manager.current_session.id
                            == selected_session_id
                        ):
                            self.new_session()

    def update_session_info(self):
        """Update session info display."""
        if self.session_manager.current_session:
            session = self.session_manager.current_session
            self.session_label.setText(f"Session: {session.title}")
            self.cost_label.setText(f"Cost: ${session.total_cost:.4f}")
            self.turns_label.setText(f"Messages: {len(session.messages)}")
        else:
            self.session_label.setText("No active session")
            self.cost_label.setText("Cost: $0.00")
            self.turns_label.setText("Messages: 0")


class SessionSelectionDialog(QDialog):
    """Dialog for selecting a session."""

    def __init__(
        self, session_manager: SessionManager, parent=None, title="Select Session"
    ):
        super().__init__(parent)
        self.session_manager = session_manager
        self.selected_session_id = None

        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout()

        # Session list
        self.session_list = QListWidget()
        self.session_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.session_list)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        # Load sessions
        self.load_sessions()

    def load_sessions(self):
        """Load all sessions into the list."""
        sessions = self.session_manager.list_sessions()

        for session_meta in sessions:
            item = QListWidgetItem(
                f"{session_meta.title} - {session_meta.updated_at.strftime('%Y-%m-%d %H:%M')}"
            )
            item.setData(Qt.ItemDataRole.UserRole, session_meta.id)
            self.session_list.addItem(item)

    def get_selected_session_id(self) -> Optional[str]:
        """Get the selected session ID."""
        current_item = self.session_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
