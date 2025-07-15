# PyQt6 Conventions

## Widget Naming
- Use descriptive names with underscores: `message_display`, `tools_display`
- Suffix widgets with their type: `_button`, `_label`, `_radio`
- Group related widgets: `mode_group` for QButtonGroup

## Layout Management
- Use QVBoxLayout for vertical arrangements
- Use QHBoxLayout for horizontal arrangements
- Use QSplitter for resizable panels
- Always check if widgets exist before accessing methods

## Signal/Slot Connections
- Connect signals in `__init__` or dedicated init methods
- Use descriptive slot names: `on_mode_changed`, `handle_error`
- Disconnect signals when cleaning up

## Threading
- Use QThread with worker pattern for long operations
- Never update UI from worker threads directly
- Use signals to communicate from workers to main thread

## Error Handling
- Check for None before calling widget methods
- Show user errors with QMessageBox
- Handle thread exceptions gracefully