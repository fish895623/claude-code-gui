# Mode System Rules

## Available Modes

### Accept Edits (Default)
- Color: Blue
- Permission: `acceptEdits`
- Tools: All tools allowed
- Behavior: Requires user confirmation for all edits
- Use case: Safe default for general use

### Auto-Accept
- Color: Orange
- Permission: `bypassPermissions`
- Tools: All tools allowed
- Behavior: Automatically accepts all edits without confirmation
- Use case: When user trusts the operations

### Plan Mode
- Color: Green
- Permission: `acceptEdits` + planning prompt
- Tools: All tools allowed
- Behavior: Creates and presents a plan before executing
- Use case: Complex tasks requiring thoughtful approach

### Dangerous-Skip
- Color: Red (bold)
- Permission: `bypassPermissions`
- Tools: All tools allowed
- Behavior: Bypasses ALL safety checks
- Use case: Emergency situations only, use with extreme caution

## Mode Switching
- Keyboard shortcuts:
  - `Ctrl+;` - Previous mode
  - `Ctrl+'` - Next mode
- Mode order: Accept Edits → Auto-Accept → Plan → Dangerous-Skip → (loop)
- Mode preference persists across sessions

## Implementation
- Store mode state in ApplicationSettings
- Update visual indicators when mode changes
- Show mode in status bar and session info panel