"""XML rules parser for Claude Code GUI."""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RuleType(Enum):
    """Types of rules that can be defined."""

    BEHAVIOR = "behavior"
    CONSTRAINT = "constraint"
    FORMAT = "format"
    INSTRUCTION = "instruction"


@dataclass
class Rule:
    """Represents a single rule."""

    name: str
    type: RuleType
    content: str
    enabled: bool = True
    priority: int = 0  # Higher priority rules are applied first

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "content": self.content,
            "enabled": self.enabled,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create rule from dictionary."""
        return cls(
            name=data["name"],
            type=RuleType(data["type"]),
            content=data["content"],
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
        )


class RulesParser:
    """Parser for XML rules."""

    DEFAULT_RULES_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<rules>
    <rule type="behavior" priority="10">
        <name>Professional Tone</name>
        <content>Maintain a professional and helpful tone in all responses</content>
    </rule>
    <rule type="constraint" priority="5">
        <name>Code Quality</name>
        <content>Always follow best practices and write clean, maintainable code</content>
    </rule>
    <rule type="format">
        <name>Response Format</name>
        <content>Use markdown formatting for code blocks and emphasis</content>
    </rule>
</rules>"""

    @staticmethod
    def parse_xml(xml_content: str) -> Tuple[List[Rule], Optional[str]]:
        """
        Parse XML rules content.

        Returns:
            Tuple of (rules list, error message if any)
        """
        rules = []
        try:
            root = ET.fromstring(xml_content)

            if root.tag != "rules":
                return [], "Root element must be <rules>"

            for rule_elem in root.findall("rule"):
                # Extract attributes
                rule_type = rule_elem.get("type")
                if not rule_type:
                    return [], "Rule missing 'type' attribute"

                try:
                    rule_type_enum = RuleType(rule_type)
                except ValueError:
                    valid_types = ", ".join([t.value for t in RuleType])
                    return (
                        [],
                        f"Invalid rule type: {rule_type}. Valid types: {valid_types}",
                    )

                priority = int(rule_elem.get("priority", "0"))
                enabled = rule_elem.get("enabled", "true").lower() == "true"

                # Extract child elements
                name_elem = rule_elem.find("name")
                content_elem = rule_elem.find("content")

                if name_elem is None:
                    return [], "Rule missing <name> element"
                if content_elem is None:
                    return [], "Rule missing <content> element"

                name = name_elem.text or ""
                content = content_elem.text or ""

                if not name.strip():
                    return [], "Rule name cannot be empty"
                if not content.strip():
                    return [], "Rule content cannot be empty"

                rule = Rule(
                    name=name.strip(),
                    type=rule_type_enum,
                    content=content.strip(),
                    enabled=enabled,
                    priority=priority,
                )
                rules.append(rule)

            # Sort by priority (highest first)
            rules.sort(key=lambda r: r.priority, reverse=True)

            return rules, None

        except ET.ParseError as e:
            return [], f"XML parsing error: {str(e)}"
        except Exception as e:
            return [], f"Unexpected error: {str(e)}"

    @staticmethod
    def rules_to_xml(rules: List[Rule]) -> str:
        """Convert rules list to XML string."""
        root = ET.Element("rules")

        for rule in rules:
            rule_elem = ET.SubElement(root, "rule")
            rule_elem.set("type", rule.type.value)
            rule_elem.set("priority", str(rule.priority))
            if not rule.enabled:
                rule_elem.set("enabled", "false")

            name_elem = ET.SubElement(rule_elem, "name")
            name_elem.text = rule.name

            content_elem = ET.SubElement(rule_elem, "content")
            content_elem.text = rule.content

        # Pretty print
        ET.indent(root, space="    ")
        return ET.tostring(root, encoding="unicode", method="xml")

    @staticmethod
    def rules_to_prompt(rules: List[Rule]) -> str:
        """
        Convert rules to a formatted prompt string for Claude.

        Only includes enabled rules.
        """
        if not rules:
            return ""

        enabled_rules = [r for r in rules if r.enabled]
        if not enabled_rules:
            return ""

        prompt_parts = ["<rules>"]

        # Group rules by type
        rules_by_type: Dict[RuleType, List[Rule]] = {}
        for rule in enabled_rules:
            if rule.type not in rules_by_type:
                rules_by_type[rule.type] = []
            rules_by_type[rule.type].append(rule)

        # Format each type
        for rule_type in RuleType:
            if rule_type not in rules_by_type:
                continue

            type_rules = rules_by_type[rule_type]
            if rule_type == RuleType.BEHAVIOR:
                prompt_parts.append("Behavioral Guidelines:")
            elif rule_type == RuleType.CONSTRAINT:
                prompt_parts.append("Constraints:")
            elif rule_type == RuleType.FORMAT:
                prompt_parts.append("Formatting Requirements:")
            elif rule_type == RuleType.INSTRUCTION:
                prompt_parts.append("Special Instructions:")

            for rule in type_rules:
                prompt_parts.append(f"- {rule.name}: {rule.content}")

            prompt_parts.append("")  # Empty line between sections

        prompt_parts.append("</rules>")

        return "\n".join(prompt_parts).strip()

    @staticmethod
    def validate_xml(xml_content: str) -> Optional[str]:
        """
        Validate XML rules content.

        Returns:
            Error message if invalid, None if valid
        """
        _, error = RulesParser.parse_xml(xml_content)
        return error
