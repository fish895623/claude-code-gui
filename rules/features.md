# Feature Documentation

## Subtask Generation and TODO Management

### Overview
The subtask generation feature allows Claude to analyze user prompts and break them down into actionable subtasks displayed in a TODO widget.

### Components

#### TODO Widget
- Located in the right panel under "Task Breakdown"
- Shows generated subtasks with checkboxes
- Supports marking tasks as complete
- Color-coded by priority

#### Generate Subtasks Button
- Analyzes the last user prompt
- Sends it to Claude for task breakdown
- Parses the response into structured subtasks
- Updates the TODO list automatically

### Subtask Format
Claude generates subtasks in this format:
```
1. [HIGH] Task title - Optional description
2. [NORMAL] Another task
3. [LOW] Low priority task - With details
```

### Priority Levels
- **HIGH**: Red text, bold
- **NORMAL**: Default black text
- **LOW**: Gray text

### Features
- Subtasks persist with sessions
- Check/uncheck to mark complete
- Completed tasks show strikethrough
- Auto-save when toggling completion
- Sorted by: completion status, priority, creation time

### Usage
1. Enter a task or prompt in the main input
2. Click "Generate Subtasks" button
3. Claude analyzes and creates subtask breakdown
4. Check off subtasks as you complete them

### Session Management
- **Session Switcher**: Dropdown in toolbar shows current and recent sessions
- **Quick New Session**: ➕ button creates a new blank session
- Subtasks are saved with each session