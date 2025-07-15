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
    QToolBar,
    QRadioButton,
    QButtonGroup,
    QComboBox,
    QCheckBox,
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
from .models import MessageRole, ConversationSession, Subtask
from .rules_editor import RulesEditorDialog


class MessageDisplay(QTextEdit):
    """Custom QTextEdit for displaying Claude messages with formatting."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        # Hide scrollbars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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
        self.init_mode_toolbar()
        self.restore_window_state()

        # Load the most recent session or create a new one
        self.load_or_create_session()

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
        self.rules_label = QLabel("Rules: None")
        self.mode_label = QLabel("Mode: Default")
        session_layout.addWidget(self.session_label)
        session_layout.addWidget(self.cost_label)
        session_layout.addWidget(self.turns_label)
        session_layout.addWidget(self.rules_label)
        session_layout.addWidget(self.mode_label)
        session_group.setLayout(session_layout)
        info_layout.addWidget(session_group)

        # Tool status
        tools_group = QGroupBox("Tool Activity")
        tools_layout = QVBoxLayout()
        self.tools_display = QTextEdit()
        self.tools_display.setReadOnly(True)
        self.tools_display.setMaximumHeight(200)
        # Hide scrollbars
        self.tools_display.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tools_display.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        tools_layout.addWidget(self.tools_display)
        tools_group.setLayout(tools_layout)
        info_layout.addWidget(tools_group)

        # TODO list
        todo_group = QGroupBox("Task Breakdown")
        todo_layout = QVBoxLayout()

        # Generate subtasks button
        self.generate_subtasks_button = QPushButton("Generate Subtasks")
        self.generate_subtasks_button.clicked.connect(self.generate_subtasks)
        todo_layout.addWidget(self.generate_subtasks_button)

        # TODO list widget
        self.todo_list = QListWidget()
        self.todo_list.setMaximumHeight(300)
        todo_layout.addWidget(self.todo_list)

        todo_group.setLayout(todo_layout)
        info_layout.addWidget(todo_group)

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

        session_menu.addSeparator()

        # Edit Rules
        edit_rules_action = QAction("Edit Rules...", self)
        edit_rules_action.setShortcut("Ctrl+R")
        edit_rules_action.triggered.connect(self.edit_rules)
        session_menu.addAction(edit_rules_action)

    def init_mode_toolbar(self):
        """Initialize the mode toolbar."""
        mode_toolbar = self.addToolBar("Mode")
        if not mode_toolbar:
            return

        # Mode radio buttons
        self.mode_group = QButtonGroup()
        self.modes = []

        # Accept Edits mode (default)
        self.accept_edits_radio = QRadioButton("Accept Edits")
        self.accept_edits_radio.setToolTip("Requires confirmation for edits")
        self.accept_edits_radio.setStyleSheet("QRadioButton { color: blue; }")
        self.mode_group.addButton(self.accept_edits_radio, 0)
        self.modes.append(("acceptEdits", self.accept_edits_radio))
        mode_toolbar.addWidget(self.accept_edits_radio)

        # Auto-Accept mode
        self.auto_accept_radio = QRadioButton("Auto-Accept")
        self.auto_accept_radio.setToolTip("Automatically accepts edits")
        self.auto_accept_radio.setStyleSheet("QRadioButton { color: orange; }")
        self.mode_group.addButton(self.auto_accept_radio, 1)
        self.modes.append(("bypassPermissions", self.auto_accept_radio))
        mode_toolbar.addWidget(self.auto_accept_radio)

        # Plan mode
        self.plan_mode_radio = QRadioButton("Plan")
        self.plan_mode_radio.setToolTip("Plans before executing")
        self.plan_mode_radio.setStyleSheet("QRadioButton { color: green; }")
        self.mode_group.addButton(self.plan_mode_radio, 2)
        self.modes.append(("plan", self.plan_mode_radio))
        mode_toolbar.addWidget(self.plan_mode_radio)

        # Dangerous-Skip mode
        self.dangerous_skip_radio = QRadioButton("Dangerous-Skip")
        self.dangerous_skip_radio.setToolTip("DANGER: Bypasses all safety checks")
        self.dangerous_skip_radio.setStyleSheet(
            "QRadioButton { color: red; font-weight: bold; }"
        )
        self.mode_group.addButton(self.dangerous_skip_radio, 3)
        self.modes.append(("dangerous", self.dangerous_skip_radio))
        mode_toolbar.addWidget(self.dangerous_skip_radio)

        # Connect mode change signal
        self.mode_group.buttonClicked.connect(self.on_mode_changed)

        mode_toolbar.addSeparator()

        # Previous/Next buttons
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.setToolTip("Previous mode (Ctrl+;)")
        self.prev_button.clicked.connect(self.prev_mode)
        mode_toolbar.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ▶")
        self.next_button.setToolTip("Next mode (Ctrl+')")
        self.next_button.clicked.connect(self.next_mode)
        mode_toolbar.addWidget(self.next_button)

        # Load saved settings and set default
        saved_mode = self.session_manager.app_settings.default_permission_mode
        if saved_mode == "bypassPermissions":
            self.auto_accept_radio.setChecked(True)
        elif self.session_manager.app_settings.enable_plan_mode:
            self.plan_mode_radio.setChecked(True)
        elif self.session_manager.app_settings.enable_dangerous_skip:
            self.dangerous_skip_radio.setChecked(True)
        else:
            self.accept_edits_radio.setChecked(True)  # Default

        # Add keyboard shortcuts
        self.add_mode_shortcuts()

        # Update mode display
        self.update_mode_display()

        mode_toolbar.addSeparator()

        # Session switcher
        mode_toolbar.addWidget(QLabel(" Session: "))
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(200)
        self.session_combo.currentTextChanged.connect(self.on_session_switched)
        mode_toolbar.addWidget(self.session_combo)

        # Quick new session button
        self.quick_new_button = QPushButton("➕")
        self.quick_new_button.setToolTip("Quick new session (Ctrl+Shift+N)")
        self.quick_new_button.clicked.connect(self.quick_new_session)
        self.quick_new_button.setMaximumWidth(30)
        mode_toolbar.addWidget(self.quick_new_button)

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

        # Create query config with current session rules and modes
        query_config = QueryConfig()

        # Set permission mode based on selected radio button
        checked_id = self.mode_group.checkedId()
        if checked_id >= 0 and checked_id < len(self.modes):
            mode_key = self.modes[checked_id][0]

            if mode_key == "acceptEdits":
                query_config.permission_mode = "acceptEdits"
            elif mode_key == "bypassPermissions" or mode_key == "dangerous":
                query_config.permission_mode = "bypassPermissions"
            elif mode_key == "plan":
                query_config.permission_mode = (
                    "acceptEdits"  # Plan mode still uses acceptEdits
                )
                # Add plan instruction
                plan_instruction = "\n\nIMPORTANT: Before executing any tasks, first create and present a detailed plan of what you will do. Only proceed with implementation after the user approves the plan."
                query_config.system_prompt = plan_instruction

            # For dangerous mode, disable all safety tools
            if mode_key == "dangerous":
                query_config.disallowed_tools = []  # Allow all tools
                # Add warning to system prompt
                danger_warning = "\n\nWARNING: Dangerous-Skip mode is active. All safety checks are bypassed."
                if query_config.system_prompt:
                    query_config.system_prompt += danger_warning
                else:
                    query_config.system_prompt = danger_warning

        # Apply custom rules
        if (
            self.session_manager.current_session
            and self.session_manager.current_session.custom_rules
        ):
            query_config.custom_rules_xml = (
                self.session_manager.current_session.custom_rules
            )

        # Create worker and thread
        worker = ClaudeQueryWorker(self.sdk_wrapper)
        self.current_thread = ClaudeQueryThread(worker, prompt, query_config)

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

                # Check if we're generating subtasks
                if hasattr(self, "generating_subtasks") and self.generating_subtasks:
                    # Parse subtasks from the response
                    subtasks = self.parse_subtasks_from_response(text_content)
                    if subtasks:
                        # Add subtasks to the session
                        self.session_manager.current_session.subtasks.extend(subtasks)
                        # Update the TODO list
                        self.update_todo_list()
                        self.status_bar.showMessage(
                            f"Generated {len(subtasks)} subtasks"
                        )
                    self.generating_subtasks = False

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

            # Save SDK session ID for resuming
            if self.session_manager.current_session:
                self.session_manager.current_session.sdk_session_id = message_data[
                    "session_id"
                ]

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

    def load_or_create_session(self):
        """Load the most recent session or create a new one."""
        # Check if we should restore the last session
        if self.session_manager.app_settings.restore_last_session:
            recent_sessions = self.session_manager.get_recent_sessions()
            if recent_sessions:
                # Load the most recent session
                most_recent = recent_sessions[0]
                self.load_session(most_recent.id)
                return

        # Otherwise, create a new session
        self.session_manager.create_new_session()
        self.update_session_info()

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
        self.todo_list.clear()
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
            self.update_todo_list()  # Update TODO list
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

            # Update rules indicator
            if session.custom_rules:
                self.rules_label.setText("Rules: Active")
                self.rules_label.setStyleSheet("QLabel { color: green; }")
            else:
                self.rules_label.setText("Rules: None")
                self.rules_label.setStyleSheet("")
        else:
            self.session_label.setText("No active session")
            self.cost_label.setText("Cost: $0.00")
            self.turns_label.setText("Messages: 0")
            self.rules_label.setText("Rules: None")
            self.rules_label.setStyleSheet("")

        # Update session combo
        self.update_session_combo()

    def edit_rules(self):
        """Edit custom rules for the current session."""
        if not self.session_manager.current_session:
            QMessageBox.information(
                self, "No Session", "Please create or load a session first."
            )
            return

        # Get current rules or use default
        current_rules = self.session_manager.current_session.custom_rules
        if not current_rules and self.session_manager.app_settings.default_rules:
            current_rules = self.session_manager.app_settings.default_rules

        # Show rules editor
        dialog = RulesEditorDialog(current_rules, self)
        dialog.rules_saved.connect(self.on_rules_saved)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Rules are saved via the signal
            pass

    def on_rules_saved(self, xml_content: str):
        """Handle rules saved from the editor."""
        if self.session_manager.current_session:
            self.session_manager.current_session.custom_rules = xml_content
            # Auto-save if enabled
            if self.session_manager.app_settings.auto_save_enabled:
                self.session_manager.save_session()
            self.update_session_info()
            self.status_bar.showMessage("Rules updated")

    def on_mode_changed(self, button: QRadioButton):
        """Handle mode change."""
        checked_id = self.mode_group.checkedId()
        if checked_id >= 0 and checked_id < len(self.modes):
            mode_key = self.modes[checked_id][0]

            # Save to settings
            if mode_key == "acceptEdits":
                self.session_manager.app_settings.default_permission_mode = (
                    "acceptEdits"
                )
                self.session_manager.app_settings.enable_plan_mode = False
                self.session_manager.app_settings.enable_dangerous_skip = False
            elif mode_key == "bypassPermissions":
                self.session_manager.app_settings.default_permission_mode = (
                    "bypassPermissions"
                )
                self.session_manager.app_settings.enable_plan_mode = False
                self.session_manager.app_settings.enable_dangerous_skip = False
            elif mode_key == "plan":
                self.session_manager.app_settings.default_permission_mode = (
                    "acceptEdits"
                )
                self.session_manager.app_settings.enable_plan_mode = True
                self.session_manager.app_settings.enable_dangerous_skip = False
            elif mode_key == "dangerous":
                self.session_manager.app_settings.default_permission_mode = (
                    "bypassPermissions"
                )
                self.session_manager.app_settings.enable_plan_mode = False
                self.session_manager.app_settings.enable_dangerous_skip = True

            self.session_manager.save_app_settings()

            # Update display
            self.update_mode_display()
            self.status_bar.showMessage(f"Mode changed to: {button.text()}")

    def prev_mode(self):
        """Switch to previous mode."""
        current_id = self.mode_group.checkedId()
        if current_id > 0:
            self.modes[current_id - 1][1].setChecked(True)
        else:
            # Wrap around to last mode
            self.modes[-1][1].setChecked(True)

    def next_mode(self):
        """Switch to next mode."""
        current_id = self.mode_group.checkedId()
        if current_id < len(self.modes) - 1:
            self.modes[current_id + 1][1].setChecked(True)
        else:
            # Wrap around to first mode
            self.modes[0][1].setChecked(True)

    def add_mode_shortcuts(self):
        """Add keyboard shortcuts for mode switching."""
        # Previous mode shortcut (Ctrl+;)
        prev_action = QAction(self)
        prev_action.setShortcut("Ctrl+;")
        prev_action.triggered.connect(self.prev_mode)
        self.addAction(prev_action)

        # Next mode shortcut (Ctrl+')
        next_action = QAction(self)
        next_action.setShortcut("Ctrl+'")
        next_action.triggered.connect(self.next_mode)
        self.addAction(next_action)

    def update_mode_display(self):
        """Update the mode display in the session info."""
        checked_button = self.mode_group.checkedButton()
        if checked_button:
            mode_text = checked_button.text()
            self.mode_label.setText(f"Mode: {mode_text}")

            # Update label color based on mode
            if mode_text == "Dangerous-Skip":
                self.mode_label.setStyleSheet(
                    "QLabel { color: red; font-weight: bold; }"
                )
            elif mode_text == "Auto-Accept":
                self.mode_label.setStyleSheet("QLabel { color: orange; }")
            elif mode_text == "Accept Edits":
                self.mode_label.setStyleSheet("QLabel { color: blue; }")
            elif mode_text == "Plan":
                self.mode_label.setStyleSheet("QLabel { color: green; }")
            else:
                self.mode_label.setStyleSheet("")

    def generate_subtasks(self):
        """Generate subtasks for the current conversation."""
        # Get the last user message
        if (
            not self.session_manager.current_session
            or not self.session_manager.current_session.messages
        ):
            QMessageBox.information(
                self, "No Task", "Please enter a task or prompt first."
            )
            return

        # Find the last user message
        last_user_message = None
        for msg in reversed(self.session_manager.current_session.messages):
            if msg.role == MessageRole.USER:
                last_user_message = msg.content
                break

        if not last_user_message:
            QMessageBox.information(
                self, "No Task", "No user message found to analyze."
            )
            return

        # Create the subtask generation prompt
        subtask_prompt = f"""Please analyze this task and break it down into subtasks:

Task: {last_user_message}

Generate a numbered list of subtasks that would help complete this task. For each subtask:
- Keep the title concise (under 50 characters)
- Add a brief description if needed
- Mark priority as [HIGH], [NORMAL], or [LOW]

Format each subtask as:
1. [PRIORITY] Title - Description (if needed)

Focus on actionable, concrete steps."""

        # Save the subtask prompt
        self.subtask_generation_prompt = subtask_prompt

        # Send the query with a special marker
        self.generating_subtasks = True
        self.input_field.setText(subtask_prompt)
        self.send_query()

        self.status_bar.showMessage("Generating subtasks...")

    def parse_subtasks_from_response(self, text: str):
        """Parse subtasks from Claude's response."""
        import re

        subtasks = []
        # Match numbered items with optional priority and description
        pattern = r"^\s*\d+\.\s*(?:\[(HIGH|NORMAL|LOW)\])?\s*(.+?)(?:\s*-\s*(.+))?$"

        for line in text.split("\n"):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                priority_text = match.group(1) or "NORMAL"
                title = match.group(2).strip()
                description = match.group(3).strip() if match.group(3) else ""

                # Map priority
                priority = 0  # Normal
                if priority_text.upper() == "HIGH":
                    priority = 1
                elif priority_text.upper() == "LOW":
                    priority = -1

                subtask = Subtask(
                    title=title[:100],  # Limit title length
                    description=description,
                    priority=priority,
                )
                subtasks.append(subtask)

        return subtasks

    def update_todo_list(self):
        """Update the TODO list widget with current subtasks."""
        self.todo_list.clear()

        if not self.session_manager.current_session:
            return

        # Sort subtasks by priority and completion status
        subtasks = sorted(
            self.session_manager.current_session.subtasks,
            key=lambda x: (x.is_completed, -x.priority, x.created_at),
        )

        for subtask in subtasks:
            # Create a custom widget for each subtask
            item_widget = QWidget()
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(5, 2, 5, 2)

            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(subtask.is_completed)
            checkbox.toggled.connect(
                lambda checked, task=subtask: self.toggle_subtask(task, checked)
            )
            item_layout.addWidget(checkbox)

            # Title and description
            text = subtask.title
            if subtask.description:
                text += f" - {subtask.description}"

            label = QLabel(text)
            if subtask.is_completed:
                label.setStyleSheet(
                    "QLabel { color: gray; text-decoration: line-through; }"
                )
            elif subtask.priority == 1:
                label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
            elif subtask.priority == -1:
                label.setStyleSheet("QLabel { color: gray; }")

            item_layout.addWidget(label)
            item_layout.addStretch()

            item_widget.setLayout(item_layout)

            # Add to list
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.todo_list.addItem(item)
            self.todo_list.setItemWidget(item, item_widget)

    def toggle_subtask(self, subtask: Subtask, checked: bool):
        """Toggle subtask completion status."""
        from datetime import datetime

        subtask.is_completed = checked
        subtask.completed_at = datetime.now() if checked else None

        # Save session
        if self.session_manager.app_settings.auto_save_enabled:
            self.session_manager.save_session()

        # Update display
        self.update_todo_list()

    def quick_new_session(self):
        """Quickly create a new session without dialog."""
        # Save current session if needed
        if (
            self.session_manager.current_session
            and self.session_manager.current_session.messages
        ):
            if self.session_manager.app_settings.auto_save_enabled:
                self.session_manager.save_session()

        # Create new session
        self.session_manager.create_new_session()
        self.message_display.clear()
        self.tools_display.clear()
        self.update_session_info()
        self.update_session_combo()
        self.status_bar.showMessage("New session created")

    def on_session_switched(self, text: str):
        """Handle session switching from combo box."""
        if not text or self.session_combo.currentData() is None:
            return

        session_id = self.session_combo.currentData()
        if session_id and session_id != getattr(
            self.session_manager.current_session, "id", None
        ):
            self.load_session(session_id)

    def update_session_combo(self):
        """Update the session combo box with recent sessions."""
        # Block signals to prevent triggering session switch
        self.session_combo.blockSignals(True)

        self.session_combo.clear()

        # Add current session
        if self.session_manager.current_session:
            self.session_combo.addItem(
                self.session_manager.current_session.title,
                self.session_manager.current_session.id,
            )

        # Add recent sessions
        recent_sessions = self.session_manager.get_recent_sessions()[:5]
        for session_meta in recent_sessions:
            if (
                self.session_manager.current_session
                and session_meta.id == self.session_manager.current_session.id
            ):
                continue  # Skip current session, already added
            self.session_combo.addItem(session_meta.title, session_meta.id)

        # Re-enable signals
        self.session_combo.blockSignals(False)


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
