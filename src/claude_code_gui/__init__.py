"""Claude Code GUI - A PyQt6 interface for Claude Code SDK."""

import sys
from PyQt6.QtWidgets import QApplication
from .main_window import ClaudeCodeMainWindow


def main() -> None:
    """Main entry point for Claude Code GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("Claude Code GUI")
    app.setOrganizationName("ClaudeCodeGUI")

    # Create and show main window
    window = ClaudeCodeMainWindow()
    window.show()

    # Run the application
    sys.exit(app.exec())
