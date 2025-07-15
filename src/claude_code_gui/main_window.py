"""Main window for Claude Code GUI."""

from typing import Optional

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
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

from .sdk_integration import ClaudeCodeSDKWrapper, QueryConfig
from .workers import ClaudeQueryWorker, ClaudeQueryThread


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
        self.init_ui()

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
            self.turns_label.setText(f"Turns: {message_data['num_turns']}")

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

    def closeEvent(self, event):
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
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
