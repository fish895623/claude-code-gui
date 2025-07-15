"""Rules editor dialog for Claude Code GUI."""

from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QGroupBox,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QFileDialog,
    QDialogButtonBox,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QFont,
    QTextCharFormat,
    QColor,
    QSyntaxHighlighter,
    QTextDocument,
)

from .rules_parser import RulesParser, Rule, RuleType


class XMLSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for XML."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.highlighting_rules = []

        # XML tag format
        xml_tag_format = QTextCharFormat()
        xml_tag_format.setForeground(QColor("#0066cc"))
        xml_tag_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r"</?[^>]+>", xml_tag_format))

        # XML attribute name format
        xml_attr_name_format = QTextCharFormat()
        xml_attr_name_format.setForeground(QColor("#009900"))
        self.highlighting_rules.append((r"\b\w+(?=\s*=)", xml_attr_name_format))

        # XML attribute value format
        xml_attr_value_format = QTextCharFormat()
        xml_attr_value_format.setForeground(QColor("#cc0000"))
        self.highlighting_rules.append((r'"[^"]*"', xml_attr_value_format))

        # XML comment format
        xml_comment_format = QTextCharFormat()
        xml_comment_format.setForeground(QColor("#808080"))
        xml_comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"<!--.*?-->", xml_comment_format))

    def highlightBlock(self, text: Optional[str]):
        """Apply syntax highlighting to a block of text."""
        if text is None:
            return

        import re

        for pattern, format in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)


class RuleEditorWidget(QWidget):
    """Widget for editing a single rule."""

    rule_changed = pyqtSignal()

    def __init__(self, rule: Optional[Rule] = None, parent=None):
        super().__init__(parent)
        self.rule = rule
        self.init_ui()
        if rule:
            self.load_rule(rule)

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Rule name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_changed)
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)

        # Rule type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([t.value for t in RuleType])
        self.type_combo.currentTextChanged.connect(self.on_changed)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # Priority
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 100)
        self.priority_spin.valueChanged.connect(self.on_changed)
        priority_layout.addWidget(self.priority_spin)
        priority_layout.addStretch()
        layout.addLayout(priority_layout)

        # Enabled
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        self.enabled_check.toggled.connect(self.on_changed)
        layout.addWidget(self.enabled_check)

        # Content
        layout.addWidget(QLabel("Content:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText("")
        self.content_edit.textChanged.connect(self.on_changed)
        layout.addWidget(self.content_edit)

        self.setLayout(layout)

    def load_rule(self, rule: Rule):
        """Load a rule into the editor."""
        self.rule = rule
        self.name_edit.setText(rule.name)
        self.type_combo.setCurrentText(rule.type.value)
        self.priority_spin.setValue(rule.priority)
        self.enabled_check.setChecked(rule.enabled)
        self.content_edit.setPlainText(rule.content)

    def get_rule(self) -> Optional[Rule]:
        """Get the current rule from the editor."""
        name = self.name_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not name or not content:
            return None

        return Rule(
            name=name,
            type=RuleType(self.type_combo.currentText()),
            content=content,
            enabled=self.enabled_check.isChecked(),
            priority=self.priority_spin.value(),
        )

    def on_changed(self):
        """Handle changes to the rule."""
        self.rule_changed.emit()


class RulesEditorDialog(QDialog):
    """Dialog for editing XML rules."""

    rules_saved = pyqtSignal(str)  # Emits the XML content

    def __init__(self, initial_xml: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rules Editor")
        self.setModal(True)
        self.resize(800, 600)
        self.current_rules: List[Rule] = []
        self.init_ui()

        if initial_xml:
            self.load_xml(initial_xml)
        else:
            self.load_xml(RulesParser.DEFAULT_RULES_TEMPLATE)

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Toolbar
        toolbar_layout = QHBoxLayout()

        self.new_rule_button = QPushButton("New Rule")
        self.new_rule_button.clicked.connect(self.new_rule)
        toolbar_layout.addWidget(self.new_rule_button)

        self.delete_rule_button = QPushButton("Delete Rule")
        self.delete_rule_button.clicked.connect(self.delete_rule)
        self.delete_rule_button.setEnabled(False)
        toolbar_layout.addWidget(self.delete_rule_button)

        toolbar_layout.addStretch()

        self.import_button = QPushButton("Import...")
        self.import_button.clicked.connect(self.import_rules)
        toolbar_layout.addWidget(self.import_button)

        self.export_button = QPushButton("Export...")
        self.export_button.clicked.connect(self.export_rules)
        toolbar_layout.addWidget(self.export_button)

        layout.addLayout(toolbar_layout)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Rule list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("Rules:"))
        self.rules_list = QListWidget()
        self.rules_list.currentItemChanged.connect(self.on_rule_selected)
        left_layout.addWidget(self.rules_list)

        splitter.addWidget(left_panel)

        # Right panel - Editor tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # View mode selector
        view_layout = QHBoxLayout()
        view_layout.addWidget(QLabel("View:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Visual Editor", "XML Editor", "Preview"])
        self.view_combo.currentTextChanged.connect(self.on_view_changed)
        view_layout.addWidget(self.view_combo)
        view_layout.addStretch()
        right_layout.addLayout(view_layout)

        # Stacked widget for different views
        from PyQt6.QtWidgets import QStackedWidget

        self.view_stack = QStackedWidget()

        # Visual editor
        self.rule_editor = RuleEditorWidget()
        self.rule_editor.rule_changed.connect(self.on_rule_edited)
        self.view_stack.addWidget(self.rule_editor)

        # XML editor
        self.xml_editor = QTextEdit()
        self.xml_editor.setFont(QFont("Consolas", 10))
        doc = self.xml_editor.document()
        if doc:
            self.xml_highlighter = XMLSyntaxHighlighter(doc)
        self.xml_editor.textChanged.connect(self.on_xml_changed)
        self.view_stack.addWidget(self.xml_editor)

        # Preview
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        self.view_stack.addWidget(self.preview_text)

        right_layout.addWidget(self.view_stack)

        # Error display
        self.error_label = QLabel()
        self.error_label.setStyleSheet("QLabel { color: red; }")
        self.error_label.setWordWrap(True)
        right_layout.addWidget(self.error_label)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 550])

        layout.addWidget(splitter)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def load_xml(self, xml_content: str):
        """Load XML content into the editor."""
        self.xml_editor.setPlainText(xml_content)
        rules, error = RulesParser.parse_xml(xml_content)

        if error:
            self.error_label.setText(f"Error: {error}")
            self.current_rules = []
        else:
            self.error_label.clear()
            self.current_rules = rules

        self.refresh_rules_list()
        self.update_preview()

    def refresh_rules_list(self):
        """Refresh the rules list widget."""
        self.rules_list.clear()

        for rule in self.current_rules:
            item_text = f"{rule.name} ({rule.type.value})"
            if not rule.enabled:
                item_text += " [Disabled]"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, rule)
            self.rules_list.addItem(item)

    def on_rule_selected(self, current, previous):
        """Handle rule selection."""
        if not current:
            self.delete_rule_button.setEnabled(False)
            self.rule_editor.setEnabled(False)
            return

        self.delete_rule_button.setEnabled(True)
        self.rule_editor.setEnabled(True)

        rule = current.data(Qt.ItemDataRole.UserRole)
        if rule:
            self.rule_editor.load_rule(rule)

    def on_rule_edited(self):
        """Handle changes to the current rule."""
        current_item = self.rules_list.currentItem()
        if not current_item:
            return

        new_rule = self.rule_editor.get_rule()
        if not new_rule:
            return

        # Update the rule in the list
        index = self.rules_list.row(current_item)
        self.current_rules[index] = new_rule

        # Update the list item
        item_text = f"{new_rule.name} ({new_rule.type.value})"
        if not new_rule.enabled:
            item_text += " [Disabled]"
        current_item.setText(item_text)
        current_item.setData(Qt.ItemDataRole.UserRole, new_rule)

        # Update XML
        self.sync_to_xml()

    def on_xml_changed(self):
        """Handle changes to the XML editor."""
        if self.view_combo.currentText() != "XML Editor":
            return

        xml_content = self.xml_editor.toPlainText()
        rules, error = RulesParser.parse_xml(xml_content)

        if error:
            self.error_label.setText(f"Error: {error}")
        else:
            self.error_label.clear()
            self.current_rules = rules
            self.refresh_rules_list()
            self.update_preview()

    def on_view_changed(self, view_name: str):
        """Handle view mode changes."""
        if view_name == "Visual Editor":
            self.view_stack.setCurrentIndex(0)
        elif view_name == "XML Editor":
            self.view_stack.setCurrentIndex(1)
            self.sync_to_xml()
        elif view_name == "Preview":
            self.view_stack.setCurrentIndex(2)
            self.update_preview()

    def sync_to_xml(self):
        """Sync current rules to XML editor."""
        xml_content = RulesParser.rules_to_xml(self.current_rules)
        self.xml_editor.setPlainText(xml_content)

    def update_preview(self):
        """Update the preview text."""
        prompt = RulesParser.rules_to_prompt(self.current_rules)
        if prompt:
            self.preview_text.setPlainText(
                "This is how your rules will be formatted for Claude:\n\n" + prompt
            )
        else:
            self.preview_text.setPlainText("No enabled rules to preview.")

    def new_rule(self):
        """Create a new rule."""
        new_rule = Rule(
            name="New Rule",
            type=RuleType.BEHAVIOR,
            content="Enter rule content here",
            priority=0,
        )
        self.current_rules.append(new_rule)
        self.refresh_rules_list()
        self.sync_to_xml()

        # Select the new rule
        self.rules_list.setCurrentRow(len(self.current_rules) - 1)

    def delete_rule(self):
        """Delete the selected rule."""
        current_item = self.rules_list.currentItem()
        if not current_item:
            return

        reply = QMessageBox.question(
            self,
            "Delete Rule",
            "Are you sure you want to delete this rule?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            index = self.rules_list.row(current_item)
            del self.current_rules[index]
            self.refresh_rules_list()
            self.sync_to_xml()

    def import_rules(self):
        """Import rules from file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Rules", "", "XML Files (*.xml);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    xml_content = f.read()
                self.load_xml(xml_content)
            except Exception as e:
                QMessageBox.critical(
                    self, "Import Error", f"Failed to import rules: {str(e)}"
                )

    def export_rules(self):
        """Export rules to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Rules", "rules.xml", "XML Files (*.xml);;All Files (*)"
        )

        if filename:
            try:
                xml_content = RulesParser.rules_to_xml(self.current_rules)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                QMessageBox.information(
                    self, "Export Success", "Rules exported successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Error", f"Failed to export rules: {str(e)}"
                )

    def get_xml_content(self) -> str:
        """Get the current XML content."""
        return self.xml_editor.toPlainText()

    def accept(self):
        """Accept the dialog."""
        # Validate XML
        xml_content = self.get_xml_content()
        error = RulesParser.validate_xml(xml_content)

        if error:
            QMessageBox.warning(
                self,
                "Invalid Rules",
                f"Cannot save invalid rules:\n{error}",
            )
            return

        self.rules_saved.emit(xml_content)
        super().accept()


# Add missing import at the top
from PyQt6.QtWidgets import QLineEdit
