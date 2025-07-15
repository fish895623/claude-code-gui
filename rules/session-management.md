# Session Management Rules

## Session Storage
- Store sessions as JSON files in user data directory
- Include all messages, settings, and metadata
- Use UUIDs for unique session identification

## Auto-Save
- Respect auto_save_enabled setting
- Save after each query completion
- Save when settings change

## Session Metadata
- Track creation and update timestamps
- Record total cost and token usage
- Count messages for quick reference
- Store SDK session ID for resuming

## Data Models
- Use dataclasses for Session and Message models
- Implement to_dict/from_dict for serialization
- Validate data on load to handle corruption

## Session UI
- Show recent sessions in menu
- Display session info in side panel
- Support session search and filtering
- Allow export in multiple formats (JSON, Markdown, HTML)