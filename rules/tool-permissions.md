# Tool Permissions

## Overview
As of the latest update, all modes in Claude Code GUI grant full access to all tools. This change ensures Claude has complete functionality regardless of the selected mode.

## Implementation Details
- All modes set `disallowed_tools = []` (empty list)
- This allows Claude to use any available tool without restrictions
- The change applies to:
  - Accept Edits mode
  - Auto-Accept mode
  - Plan mode
  - Dangerous-Skip mode

## Technical Details
The tool permission configuration is set in `main_window.py` in the `send_query` method:
```python
# Allow all tools for all modes
query_config.disallowed_tools = []  # Allow all tools
```

## Rationale
This change was made to ensure users have full access to Claude's capabilities regardless of which mode they choose. The different modes now only affect:
- Whether edits require confirmation (Accept Edits vs Auto-Accept)
- Whether a plan is generated first (Plan mode)
- Warning messages (Dangerous-Skip mode)

Tool access is no longer restricted by mode selection.