# Claude Code GUI

A PyQt6-based graphical interface for the Claude Code SDK, providing an easy way to interact with Claude Code through a desktop application.

## Features

- **Interactive Chat Interface**: Send prompts and receive responses from Claude Code
- **Real-time Message Display**: See Claude's responses, tool usage, and results as they happen
- **Session Information**: Track session ID, cost, and number of turns
- **Tool Activity Monitor**: View which tools Claude is using in real-time
- **Async Operation Support**: Non-blocking UI with proper threading

## Installation

This project uses `uv` for Python package management:

```bash
# Install dependencies
uv pip install -e .

# For development dependencies
uv pip install -e ".[dev]"
```

## Usage

### Running the GUI

```bash
claude-code-gui
```

Or via Python:

```bash
python -m claude_code_gui
```

### Programmatic Usage

You can also use the SDK wrapper directly in your Python code:

```python
import asyncio
from claude_code_gui.sdk_integration import ClaudeCodeSDKWrapper, QueryConfig

async def main():
    wrapper = ClaudeCodeSDKWrapper()
    async for message in wrapper.send_query("Hello, Claude!"):
        parsed = wrapper.parse_message(message)
        print(parsed)

asyncio.run(main())
```

## Architecture

- **`sdk_integration.py`**: Wrapper around the claude-code-sdk with message parsing
- **`workers.py`**: Qt worker threads for handling async operations
- **`main_window.py`**: Main PyQt6 window with chat interface
- **`__init__.py`**: Entry point for the application

## Requirements

- Python 3.10+
- PyQt6
- claude-code-sdk >= 0.0.14
- Node.js (required by claude-code-sdk)

## Development

Format code with black:

```bash
black src/
```

Check code style:

```bash
pydocstyle src/
```