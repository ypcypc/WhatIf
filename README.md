# WhatIf - AI-Powered Interactive Galgame

An innovative visual novel adaptation system that transforms light novels into interactive galgame experiences using advanced AI technology.

## 🎯 Project Overview

WhatIf is a full-stack application that converts traditional light novel text into interactive, choice-driven gameplay. The system uses AI to structure original novel content into playable script format while preserving text fidelity based on configurable deviation levels.

### Core Concept
- **Text Preservation**: Maintain original novel content with AI-controlled adaptation levels
- **Interactive Adaptation**: Transform linear text into branching, choice-driven experiences  
- **Memory Management**: Advanced context tracking using modern LangGraph patterns
- **Anchor-Based Navigation**: Precise text segmentation for seamless story progression

## 🏗️ Technical Architecture

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with custom glass morphism effects
- **Animations**: Framer Motion for smooth UI transitions
- **Build Tool**: Vite for fast development and optimized builds
- **State Management**: React Context for session and game state

#### Key Frontend Components
- `MainMenu.tsx` - Game entry point and settings
- `GameScreen.tsx` - Main gameplay interface with typewriter effects
- `DialogueBox.tsx` - Interactive dialogue and choice presentation
- `Toolbar.tsx` - Game controls and status indicators

### Backend Services (FastAPI + Python)

#### Core Services Architecture
```
FastAPI Main Application
├── dict_service      # Dictionary and text retrieval
├── llm_service       # AI generation and memory management  
├── save_service      # Game state persistence
├── anchor_service    # Text segmentation and retrieval
└── game_router       # Unified game flow coordination
```

#### Service Details

**1. LLM Service** (`/api/v1/llm/`)
- **Purpose**: AI-powered text adaptation and script generation
- **Key Features**:
  - OpenAI GPT-4o-mini integration with structured outputs
  - Modern LangGraph memory management
  - Deviation-based text preservation control
  - Automatic content balancing (narration/dialogue/interaction)

**2. Anchor Service** (`/api/v1/anchor/`)
- **Purpose**: Precise text segmentation and context assembly
- **Key Features**:
  - Chapter-based text anchoring system
  - Context window optimization
  - Seamless story progression tracking

**3. Save Service** (`/api/v1/save/`)
- **Purpose**: Game state persistence and session management
- **Key Features**:
  - JSONL event streaming for complete audit trails
  - JSON snapshot storage for quick state recovery
  - Session-based save/load functionality

**4. Dict Service** (`/api/v1/dict/`)
- **Purpose**: Text retrieval and dictionary management
- **Key Features**:
  - Efficient text lookup and caching
  - Multi-format text processing support

## 🔄 Frontend-Backend Interaction Flow

### Complete Interaction Cycle
```
Player Input → Frontend UI (React)
    ↓
Frontend calls Game Router (/api/game/continue)
    ↓
Game Router orchestrates:
    ├── Anchor Service (get text context)
    ├── LLM Service (generate script)
    └── Save Service (persist state)
    ↓
JSON Response with structured script
    ↓
Frontend renders with typewriter animation
    ↓
Player makes choice → Cycle repeats
```

### API Endpoints

#### Game Flow
- `POST /api/game/start` - Initialize new game session
- `POST /api/game/continue` - Process player choice and generate next script
- `GET /api/game/status/{session_id}` - Get current game state

#### Service-Specific
- `POST /api/v1/llm/generate` - Direct LLM script generation
- `GET /api/v1/anchor/context/{chapter_id}/{anchor_index}` - Get text context
- `POST /api/v1/save/snapshot` - Save game state
- `GET /api/v1/save/snapshot/{session_id}` - Load game state

### Data Flow Example
```json
// Frontend Request
POST /api/game/continue
{
  "session_id": "player_123",
  "player_choice": "选择相信她的话",
  "chapter_id": "chapter_1", 
  "anchor_index": 5
}

// Backend Response  
{
  "script": [
    {
      "type": "narration",
      "content": "你决定相信她，尽管心中仍有疑虑..."
    },
    {
      "type": "dialogue", 
      "content": "我选择相信你。",
      "speaker": "主角"
    },
    {
      "type": "interaction",
      "content": "接下来你想要...",
      "choice_id": "ch1_choice_6",
      "default_reply": "继续对话"
    }
  ],
  "globals": {
    "deviation": 0.15,
    "affinity": {"female_lead": 75},
    "flags": {"trust_established": true}
  }
}
```

## 🧠 Advanced AI Features

### Modern Memory Management (LangGraph)
- **Short-term Memory**: Thread-scoped conversation history (last 20 events)
- **Long-term Memory**: Cross-session persistent story state
- **Semantic Search**: FAISS vector store with OpenAI embeddings
- **Background Processing**: Automated memory extraction and summarization

### Deviation Control System
- **Level 0.00**: Perfect text preservation, structural formatting only
- **Level ≤ 0.05**: Minor language optimization, meaning preserved  
- **Level ≤ 0.30**: Moderate adaptation allowed, core story maintained
- **Level > 0.30**: Significant changes permitted, guided back to original

### Content Balancing
- Dynamic narration/dialogue ratio control
- Automatic interaction point generation
- Temperature adjustment based on content balance
- Structured JSON output with validation

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.9+
- **AI Integration**: OpenAI GPT-4o-mini with function calling
- **Memory Management**: LangChain + LangGraph patterns
- **Vector Storage**: FAISS with OpenAI embeddings
- **Data Storage**: JSON + JSONL file-based persistence
- **Async Processing**: AsyncIO with tenacity retry logic

### Frontend  
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Build**: Vite
- **HTTP Client**: Fetch API with error handling

### Development Tools
- **API Documentation**: FastAPI automatic OpenAPI/Swagger docs
- **Type Safety**: TypeScript + Pydantic models
- **Code Quality**: ESLint, Prettier
- **Environment**: Docker support planned

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Python 3.9+
- OpenAI API key

### Backend Setup
```bash
cd backend_services
pip install -r requirements.txt

# Configure API keys
cp api_keys.env.example api_keys.env
# Edit api_keys.env with your OpenAI API key

# Start backend services
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup  
```bash
cd frontend
npm install
npm run dev
```

### Environment Configuration
```bash
# backend_services/api_keys.env
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_ORG_ID="your-org-id"  # optional
```

## 📁 Project Structure

```
whatif/
├── backend_services/           # FastAPI backend
│   ├── app/
│   │   ├── services/
│   │   │   ├── llm_service/    # AI generation & memory
│   │   │   ├── anchor_service/ # Text segmentation  
│   │   │   ├── save_service/   # State persistence
│   │   │   └── dict_service/   # Text retrieval
│   │   ├── core/               # Config & middleware
│   │   └── main.py            # FastAPI application
│   ├── data/                   # Game data & saves
│   ├── api_keys.env           # API key configuration
│   └── requirements.txt       # Python dependencies
├── src/                        # React frontend
│   ├── components/            # React components
│   ├── hooks/                # Custom React hooks
│   └── types/                # TypeScript definitions  
├── package.json              # Node dependencies
├── tailwind.config.js        # Styling configuration
├── CLAUDE.md                 # Development guidelines
└── README.md                 # This file
```

## 🎮 Gameplay Features

- **Adaptive Storytelling**: AI adjusts content based on player choices
- **Visual Novel Style**: Classic galgame UI with modern enhancements
- **Glass Morphism UI**: Beautiful translucent interface effects
- **Typewriter Effects**: Smooth text animation for immersive reading
- **Choice Persistence**: All decisions tracked and influence future content
- **Session Management**: Save/load functionality with full state recovery

## 🔧 Development Guidelines

See [CLAUDE.md](./CLAUDE.md) for detailed development instructions, including:
- Service interaction patterns
- Memory management strategies  
- Prompt engineering guidelines
- Deviation control implementation
- API integration standards

## 📄 License

This project is proprietary software. All rights reserved.

## 🤝 Contributing

This is a private development project. For questions or collaboration inquiries, please contact the development team.