# UI/UX Rules

## Color Scheme
- Blue: Safe/default operations
- Orange: Caution required
- Green: Planning/thoughtful mode
- Red: Dangerous operations
- Use color consistently across all UI elements

## Scrollbars
- Hide scrollbars in text displays for cleaner appearance
- Use Qt.ScrollBarPolicy.ScrollBarAlwaysOff
- Content remains scrollable via mouse wheel/keyboard

## Tooltips
- Add descriptive tooltips to all interactive elements
- Include keyboard shortcuts in tooltips where applicable
- Keep tooltips concise but informative

## Keyboard Shortcuts
- Use Ctrl+key combinations for mode switching
- Document shortcuts in tooltips and menus
- Ensure shortcuts don't conflict with system defaults

## Visual Feedback
- Update status bar for user actions
- Use QMessageBox for important notifications
- Show current mode prominently in UI
- Apply consistent styling with setStyleSheet()