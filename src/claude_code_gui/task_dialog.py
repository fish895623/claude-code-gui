"""Task creation dialog for Claude Code GUI."""

from typing import Optional, List, Dict
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QGroupBox,
    QDialogButtonBox,
    QFileDialog,
    QRadioButton,
    QButtonGroup,
    QTabWidget,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from .models import Task, TaskTemplate
from .rules_editor import RulesEditorDialog


class TaskCreationDialog(QDialog):
    """Dialog for creating a new task."""

    # Signals
    task_created = pyqtSignal(Task)

    def __init__(self, parent=None, templates: Optional[List[TaskTemplate]] = None):
        super().__init__(parent)
        self.templates = templates or self._get_builtin_templates()
        self.current_task = Task()
        self.init_ui()

    def _get_builtin_templates(self) -> List[TaskTemplate]:
        """Get built-in task templates."""
        return [
            TaskTemplate(
                name="Code Review",
                description="Review code for quality and best practices",
                prompt_template="Review the code in {file_or_directory} and provide feedback on:\n- Code quality\n- Best practices\n- Potential bugs\n- Performance improvements",
                is_builtin=True,
            ),
            TaskTemplate(
                name="Bug Fix",
                description="Fix a specific bug in the codebase",
                prompt_template="Fix the following bug: {bug_description}\n\nSteps to reproduce:\n{reproduction_steps}\n\nExpected behavior:\n{expected_behavior}",
                is_builtin=True,
            ),
            TaskTemplate(
                name="Feature Implementation",
                description="Implement a new feature",
                prompt_template="Implement the following feature: {feature_description}\n\nRequirements:\n{requirements}\n\nAcceptance criteria:\n{criteria}",
                is_builtin=True,
            ),
            TaskTemplate(
                name="Refactoring",
                description="Refactor code for better structure",
                prompt_template="Refactor {code_area} to:\n- Improve readability\n- Reduce complexity\n- Follow best practices\n- Maintain functionality",
                is_builtin=True,
            ),
            TaskTemplate(
                name="Documentation",
                description="Create or update documentation",
                prompt_template="Create/update documentation for {component}:\n- Add docstrings\n- Update README\n- Create usage examples\n- Document API",
                is_builtin=True,
            ),
            TaskTemplate(
                name="Test Creation",
                description="Create tests for code",
                prompt_template="Create comprehensive tests for {component}:\n- Unit tests\n- Integration tests\n- Edge cases\n- Test documentation",
                is_builtin=True,
            ),
        ]

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Create New Task")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Create tab widget
        tabs = QTabWidget()
        tabs.addTab(self.create_task_tab(), "Task Details")
        tabs.addTab(self.create_template_tab(), "Templates")
        layout.addWidget(tabs)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def create_task_tab(self) -> QWidget:
        """Create the task details tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Task title
        layout.addWidget(QLabel("Task Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter a descriptive title for the task")
        self.title_input.textChanged.connect(self.update_task_title)
        layout.addWidget(self.title_input)

        # Task prompt
        layout.addWidget(QLabel("Task Description/Prompt:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Describe what you want Claude to do...")
        self.prompt_input.setMinimumHeight(150)
        layout.addWidget(self.prompt_input)

        # Working directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Working Directory:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Optional: Set working directory")
        dir_layout.addWidget(self.dir_input)

        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_button)
        layout.addLayout(dir_layout)

        # Permission mode
        mode_group = QGroupBox("Permission Mode")
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()

        self.accept_edits_radio = QRadioButton("Accept Edits (Safe)")
        self.accept_edits_radio.setChecked(True)
        self.mode_group.addButton(self.accept_edits_radio)
        mode_layout.addWidget(self.accept_edits_radio)

        self.auto_accept_radio = QRadioButton("Auto-Accept")
        self.mode_group.addButton(self.auto_accept_radio)
        mode_layout.addWidget(self.auto_accept_radio)

        self.plan_radio = QRadioButton("Plan Mode")
        self.mode_group.addButton(self.plan_radio)
        mode_layout.addWidget(self.plan_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout()

        # System prompt
        advanced_layout.addWidget(QLabel("System Prompt (Optional):"))
        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setMaximumHeight(80)
        self.system_prompt_input.setPlaceholderText(
            "Additional instructions for Claude..."
        )
        advanced_layout.addWidget(self.system_prompt_input)

        # Custom rules button
        self.rules_button = QPushButton("Edit Custom Rules...")
        self.rules_button.clicked.connect(self.edit_rules)
        advanced_layout.addWidget(self.rules_button)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_template_tab(self) -> QWidget:
        """Create the templates tab."""
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Select a template to start with:"))

        # Template list
        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(self.apply_template)

        for template in self.templates:
            item = QListWidgetItem(f"{template.name} - {template.description}")
            item.setData(Qt.ItemDataRole.UserRole, template)
            self.template_list.addItem(item)

        layout.addWidget(self.template_list)

        # Apply template button
        self.apply_template_button = QPushButton("Apply Selected Template")
        self.apply_template_button.clicked.connect(self.apply_selected_template)
        layout.addWidget(self.apply_template_button)

        widget.setLayout(layout)
        return widget

    def browse_directory(self):
        """Browse for working directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Working Directory", str(Path.cwd())
        )
        if directory:
            self.dir_input.setText(directory)

    def update_task_title(self, text: str):
        """Update task title as user types."""
        self.current_task.title = text

    def edit_rules(self):
        """Open rules editor dialog."""
        current_rules = self.current_task.custom_rules or ""
        dialog = RulesEditorDialog(current_rules, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # RulesEditorDialog saves via signal, but we need to get the XML
            self.current_task.custom_rules = dialog.get_xml_content()
            self.rules_button.setText("Edit Custom Rules... (Active)")

    def apply_template(self, item: QListWidgetItem):
        """Apply the double-clicked template."""
        template = item.data(Qt.ItemDataRole.UserRole)
        if template:
            self._apply_template(template)

    def apply_selected_template(self):
        """Apply the selected template."""
        current_item = self.template_list.currentItem()
        if current_item:
            self.apply_template(current_item)

    def _apply_template(self, template: TaskTemplate):
        """Apply a template to the current task."""
        # Switch to task details tab
        parent_tabs = self.findChild(QTabWidget)
        if parent_tabs:
            parent_tabs.setCurrentIndex(0)

        # Apply template values
        self.title_input.setText(template.name)
        self.prompt_input.setPlainText(template.prompt_template)

        if template.working_directory:
            self.dir_input.setText(template.working_directory)

        if template.system_prompt:
            self.system_prompt_input.setPlainText(template.system_prompt)

        if template.custom_rules:
            self.current_task.custom_rules = template.custom_rules
            self.rules_button.setText("Edit Custom Rules... (Active)")

        # Set permission mode
        if template.permission_mode == "bypassPermissions":
            self.auto_accept_radio.setChecked(True)
        elif template.permission_mode == "plan":
            self.plan_radio.setChecked(True)
        else:
            self.accept_edits_radio.setChecked(True)

        self.current_task.template_id = template.id

    def accept(self):
        """Validate and accept the dialog."""
        # Get task details
        self.current_task.title = self.title_input.text().strip()
        self.current_task.prompt = self.prompt_input.toPlainText().strip()

        if not self.current_task.title:
            QMessageBox.warning(self, "Missing Title", "Please enter a task title.")
            return

        if not self.current_task.prompt:
            QMessageBox.warning(
                self, "Missing Prompt", "Please enter a task description or prompt."
            )
            return

        # Get working directory
        working_dir = self.dir_input.text().strip()
        if working_dir:
            self.current_task.working_directory = working_dir

        # Get permission mode
        if self.auto_accept_radio.isChecked():
            self.current_task.permission_mode = "bypassPermissions"
        elif self.plan_radio.isChecked():
            self.current_task.permission_mode = "plan"
        else:
            self.current_task.permission_mode = "acceptEdits"

        # Get system prompt
        system_prompt = self.system_prompt_input.toPlainText().strip()
        if system_prompt:
            self.current_task.system_prompt = system_prompt

        # Emit signal with the created task
        self.task_created.emit(self.current_task)

        super().accept()

    def get_task(self) -> Task:
        """Get the created task."""
        return self.current_task
