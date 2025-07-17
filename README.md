# WhatIf AI Interactive Game Reader

An AI-powered interactive visual novel game system that provides immersive reading experiences with intelligent context understanding.

## 🌟 Features

- **Interactive Game Reading**: Immersive visual novel experience with AI-enhanced storytelling
- **Anchor Context System**: Smart context tracking and reference system for complex narratives
- **Multi-Service Architecture**: Modular backend with dedicated services for different functionalities
- **Real-time AI Integration**: OpenAI GPT-4 powered responses and story generation
- **Cross-Platform**: Web application with Electron desktop wrapper
- **Session Management**: Persistent game state and progress tracking

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.13+ and Poetry
- OpenAI API key

### Backend Setup

```bash
# Install Python dependencies
poetry install

# Copy and configure environment
cp config.example config
# Edit config file with your OpenAI API key

# Start backend services
./start_backend.sh
# or manually: poetry run python start_backend.py
```

### Frontend Setup

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev
```

### Desktop App (Optional)

```bash
cd apps/desktop
pnpm install
pnpm dev
```

## 🏗️ Architecture

### Backend Services

- **LLM Service**: AI text generation and processing
- **Anchor Service**: Context tracking and reference management
- **Dictionary Service**: Term definitions and explanations
- **Save Service**: Game state persistence
- **Game Router**: Main game logic coordination

### Frontend Components

- **GameReader**: Main reading interface
- **AnchorContextDemo**: Context visualization
- **InteractiveGameReader**: Enhanced interactive features

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.13
- **AI**: OpenAI GPT-4 mini
- **Data**: JSON-based storage with event streaming

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React hooks

### Desktop
- **Framework**: Electron
- **Integration**: Vite + React

## 🌐 Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Desktop App**: Run via Electron

## 📁 Project Structure

```
whatif/
├── src/                    # Frontend React application
├── backend_services/       # Python FastAPI services
├── apps/desktop/          # Electron desktop app
├── docs/                  # Documentation
├── data/                  # Game data and sessions
└── public/               # Static assets
```

## 📚 Documentation

Comprehensive documentation is available in the [docs](./docs/) directory:

- [API Reference](./docs/api-reference.md)
- [Frontend Guide](./docs/frontend.md)
- [LLM Service](./docs/llm-service.md)
- [Anchor Service](./docs/anchor-service.md)

## 🔧 Configuration

1. Copy `config.example` to `config`
2. Add your OpenAI API key
3. Adjust service ports if needed
4. Configure CORS settings for your domain

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source. Please check the license file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- FastAPI and React communities
- All contributors and testers

---

**Note**: This is an AI-powered interactive fiction system. Ensure you have proper API keys and follow OpenAI's usage guidelines.
