# Feature Documentation

## Boomerang Feature (Task Creation)

### Overview
The boomerang feature allows users to quickly create new Claude Code sessions for specific tasks, similar to Roo Code's implementation.

### Components

#### Task Creation Dialog
- **Title**: Descriptive name for the task
- **Prompt**: Detailed description of what Claude should do
- **Working Directory**: Optional directory to execute the task in
- **Permission Mode**: Choose between Accept Edits, Auto-Accept, or Plan mode
- **System Prompt**: Additional instructions for Claude
- **Custom Rules**: Task-specific rules

#### Built-in Templates
1. **Code Review** - Review code for quality and best practices
2. **Bug Fix** - Fix specific bugs with reproduction steps
3. **Feature Implementation** - Implement new features with requirements
4. **Refactoring** - Improve code structure and readability
5. **Documentation** - Create or update documentation
6. **Test Creation** - Write comprehensive tests

### Usage
1. Click the 🪃 button or press Ctrl+B
2. Fill in task details or select a template
3. Click OK to create a new session and execute the task

### Session Management
- **Session Switcher**: Dropdown in toolbar shows current and recent sessions
- **Quick New Session**: ➕ button creates a new blank session
- **Auto-save**: Current session is saved before switching

### Keyboard Shortcuts
- `Ctrl+B` - Open task creation dialog
- `Ctrl+Shift+N` - Quick new session (future enhancement)