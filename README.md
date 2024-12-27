# Llamalog: AI Chat Application with Llama.cpp

A full-stack chat application featuring a modern web interface built with Svelte and a Python backend that integrates with llama.cpp for AI model inference. The application supports continuous conversations, markdown rendering, code highlighting, and math equations.

![1735332986999](image/README/1735332986999.png)

## Features

- 🚀 Real-time streaming responses
- 💬 Continuous conversation with context memory
- 📝 Markdown support with syntax highlighting
- ➗ LaTeX math equation rendering
- 📋 Code block copying
- 🗂️ Chat session management
- 💾 SQLite database for conversation history
- 🎨 Clean, responsive UI

## Architecture

- Frontend: Svelte + Vite
- Backend: FastAPI
- AI Model: llama.cpp
- Database: SQLite

## Prerequisites

- Python 3.12+
- Node.js 18+
- llama.cpp server running locally
- A compatible LLM model for llama.cpp

## Installation

### Clone and Setup

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/Qervas/Llamalog.git
cd Llamalog

# Run the setup script
# For Unix/MacOS:
chmod +x setup.sh
./setup.sh

# For Windows:
.\setup.bat
```

## Configuration

### Backend Configuration

The backend server configuration can be modified in `main.py`:

```python
# Database configuration
DATABASE_URL = "sqlite:///./chat_history.db"

# Model configuration
LLAMA_CPP_SERVER = "http://127.0.0.1:8080"
MAX_TOKENS = 2048
TEMPERATURE = 0.7
```

### Frontend Configuration

The frontend configuration can be modified in `my-chat-app/src/App.svelte`:

```javascript
// API endpoint configuration
const API_BASE_URL = "http://localhost:8000";
```

### Start the Application

After the setup is complete, you can start all servers with a single command:

```bash
# For Unix/MacOS:
./start.sh

# For Windows:
.\start.bat
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Llama.cpp Server: http://localhost:8080

## Usage

1. Start the llama.cpp server with your chosen model
2. Start the Python backend server
3. Start the frontend development server
4. Open your browser and navigate to `http://localhost:5173`

### Basic Operations

- **New Chat**: Click the "New Chat" button to start a new conversation
- **Send Message**: Type your message and press Enter or click the send button
- **Browse History**: Use the sidebar to navigate between different chat sessions
- **Rename Chats**: Double-click on a chat title to rename it
- **Delete Chats**: Click the delete icon next to a chat session

### Keyboard Shortcuts

- `Enter` - Send message
- `Shift + Enter` - New line in message
- `Esc` - Cancel chat title editing

## Development

### Project Structure

```
├── llama.cpp/            # llama.cpp submodule
│   └── models/          # Model storage directory
├── my-chat-app/         # Frontend application
│   ├── src/
│   │   ├── App.svelte   # Main application component
│   │   ├── lib/         # Shared components
│   │   └── main.js      # Application entry point
│   ├── public/          # Static assets
│   └── package.json     # Frontend dependencies
├── backend/             # Backend application
│   ├── main.py         # Backend server
│   ├── db_models.py    # Database models
│   └── requirements.txt # Python dependencies
├── setup.sh            # Unix setup script
├── setup.bat           # Windows setup script
├── start.sh            # Unix start script
└── start.bat          # Windows start script
```

### Customization

- **Styling**: Modify the CSS in `App.svelte` and `Markdown.svelte`
- **Markdown**: Customize markdown rendering in `lib/Markdown.svelte`
- **Model Parameters**: Adjust the model parameters in `main.py`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)

## Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [Svelte](https://svelte.dev)
- [FastAPI](https://fastapi.tiangolo.com)
