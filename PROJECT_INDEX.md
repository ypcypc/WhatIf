# WhatIf Project Index

> AI-Powered Interactive Galgame System  
> Version: 0.1.0  
> Last Updated: 2025-07-30

## 📚 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Frontend Structure](#frontend-structure)
4. [Backend Services](#backend-services)
5. [Data Models](#data-models)
6. [API Reference](#api-reference)
7. [Key Components](#key-components)
8. [Configuration](#configuration)
9. [Development Guide](#development-guide)

## 🎯 Project Overview

WhatIf is an innovative visual novel adaptation system that transforms light novels into interactive galgame experiences using advanced AI technology. The system preserves original text fidelity while creating branching, choice-driven gameplay.

### Core Features
- **Text Preservation**: AI-controlled adaptation with configurable deviation levels
- **Interactive Adaptation**: Transform linear text into branching narratives
- **Memory Management**: Advanced context tracking using LangGraph patterns
- **Anchor-Based Navigation**: Precise text segmentation for story progression
- **Glass Morphism UI**: Modern translucent interface with smooth animations

## 🏗️ Architecture

### Technology Stack

#### Frontend
- **Framework**: React 19.1.0 + TypeScript 5.8.3
- **Build Tool**: Vite 7.0.4
- **Styling**: Tailwind CSS 3.4.17
- **UI Components**: liquid-glass-react 1.1.1
- **Animations**: Framer Motion 12.23.6
- **Icons**: Lucide React 0.263.1

#### Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.9+
- **AI Integration**: OpenAI GPT-4o-mini
- **Memory**: LangChain + LangGraph
- **Vector DB**: FAISS
- **Storage**: JSON/JSONL file-based

### System Flow
```
User Input → React Frontend → Game Router API
    ↓
Anchor Service (Context) → LLM Service (Generation)
    ↓
Structured Script Response → Frontend Rendering
```

## 📁 Frontend Structure

### `/src` Directory

#### Core Application Files
- `main.tsx` - Application entry point
- `App.tsx` - Main application component with screen routing
- `index.css` - Global styles and Tailwind imports
- `App.css` - Application-specific styles

#### `/components` - React Components

##### UI Components (`/components/ui`)
- `GlassCard.tsx` - Glass morphism card component
- `GlassButton.tsx` - Glass morphism button component  
- `SimpleGlass.tsx` - Basic glass effect component
- `AdvancedGlass.tsx` - Enhanced glass effect with animations

##### Game Components
- `GlassMainMenu.tsx` - Main menu with game options
- `GlassGameScreen.tsx` - Main game interface container
- `GlassDialogueBox.tsx` - Dialogue display with typewriter effect
- `InteractiveGameReader.tsx` - Core game reader logic
- `GameInitializer.tsx` - Game session initialization
- `GameDisplay.tsx` - Game content display logic
- `GameReader.tsx` - Basic game reading functionality

##### Demo/Test Components
- `AnchorServiceTest.tsx` - API connectivity testing
- `AnchorContextDemo.tsx` - Anchor system demonstration

#### `/services` - API Services
- `gameService.ts` - Game API client service
- `anchorService.ts` - Anchor service API client

#### `/stores` - State Management
- `gameStore.ts` - Zustand store for game state

#### `/hooks` - Custom React Hooks
- `useGameStore.ts` - Game store hook wrapper

#### `/utils` - Utility Functions
- `cn.ts` - Class name utility for Tailwind

### `/types` - TypeScript Definitions
- Game interfaces and type definitions
- API response types
- Component prop types

## 🔧 Backend Services

### Core Structure

#### `/backend_services/app` - Main Application

##### `/core` - Core Configuration
- `config.py` - Application settings and environment
- `middleware.py` - CORS, logging, error handling
- `utils.py` - Shared utility functions

##### `/main.py` - FastAPI Application Entry
- Service router registration
- Health check endpoints
- Middleware setup

### Microservices Architecture

#### 1. Game Router Service (`/services/game_router.py`)
Main orchestration service coordinating all game interactions.

**Endpoints**:
- `POST /api/v1/game/start` - Initialize new game session
- `POST /api/v1/game/turn` - Process player turn
- `GET /api/v1/game/sessions/{session_id}/status` - Get session status
- `GET /api/v1/game/health` - Service health check

**Key Functions**:
- `start_game()` - Initialize game with first anchor
- `process_turn()` - Handle player choice and generate response
- `get_next_anchor_index()` - Navigate storyline progression
- `get_anchor_info()` - Retrieve anchor metadata

#### 2. LLM Service (`/services/llm_service/`)
AI generation and memory management service.

**Components**:
- `services.py` - Business logic for generation
- `repositories.py` - LLM API integration and storage
- `models.py` - Data models and schemas
- `memory_manager.py` - LangGraph memory integration
- `llm_settings.py` - AI configuration settings
- `routers.py` - API endpoints

**Key Features**:
- OpenAI GPT-4o-mini integration
- Structured output generation
- Memory persistence and retrieval
- Deviation control system
- Content balancing

#### 3. Anchor Service (`/services/anchor_service/`)
Text segmentation and context management.

**Components**:
- `services.py` - Context building logic
- `repositories.py` - Text chunk retrieval
- `models.py` - Anchor data models
- `routers.py` - API endpoints

**Key Features**:
- Chapter-based text anchoring
- Context window optimization
- Cross-chapter navigation
- Text chunk assembly

#### 4. Save Service (`/services/save_service/`)
Game state persistence and recovery.

**Components**:
- `services.py` - Save/load logic
- `repositories.py` - File system operations
- `schemas.py` - Save data schemas
- `routers.py` - API endpoints

**Storage Format**:
- `events.jsonl` - Complete event stream
- `snapshot.json` - Current state snapshot

#### 5. Dict Service (`/services/dict_service/`)
Text dictionary and retrieval service.

**Components**:
- `services.py` - Dictionary operations
- `repositories.py` - Text data access
- `schemas.py` - Data schemas
- `routers.py` - API endpoints

## 📊 Data Models

### Frontend Models

#### Game State
```typescript
interface GameState {
  sessionId: string
  currentChapter: number
  currentAnchor: number
  scriptUnits: ScriptUnit[]
  playerChoices: PlayerChoice[]
  globalState: GlobalState
}
```

#### Script Unit
```typescript
interface ScriptUnit {
  type: 'narration' | 'dialogue' | 'interaction'
  content: string
  speaker?: string
  choiceId?: string
  defaultReply?: string
  metadata?: Record<string, any>
}
```

### Backend Models

#### Turn Event (Pydantic)
```python
class TurnEvent(BaseModel):
    t: int  # Turn number
    role: TurnEventRole
    anchor: Optional[str]
    choice: Optional[str]
    script: Optional[List[ScriptUnit]]
    deviation_delta: float
    affinity_changes: Optional[Dict[str, int]]
    metadata: Dict[str, Any]
```

#### Global State
```python
class GlobalState(BaseModel):
    deviation: float = 0.15
    affinity: Dict[str, int] = {}
    flags: Dict[str, bool] = {}
    variables: Dict[str, Any] = {}
```

### Data Files

#### `/data` Directory
- `storylines_data.json` - Storyline definitions and node relationships
- `characters_data.json` - Character information and metadata
- Text chunk files - Original novel text segments

## 🌐 API Reference

### Game Flow APIs

#### Start Game
```http
POST /api/v1/game/start
Content-Type: application/json

{
  "session_id": "player_123",
  "protagonist": "c_san_shang_wu",
  "chapter_id": 1,
  "anchor_index": 0
}
```

#### Process Turn
```http
POST /api/v1/game/turn
Content-Type: application/json

{
  "session_id": "player_123",
  "player_choice": "选择相信她的话",
  "chapter_id": 1,
  "anchor_index": 5,
  "current_anchor_id": "a1_5"
}
```

### Service-Specific APIs

#### LLM Generation
```http
POST /api/v1/llm/generate
```

#### Anchor Context
```http
GET /api/v1/anchor/context/{chapter_id}/{anchor_index}
```

#### Save/Load State
```http
POST /api/v1/save/snapshot
GET /api/v1/save/snapshot/{session_id}
```

## 🔑 Key Components

### Frontend Key Components

#### InteractiveGameReader
Main game logic component handling:
- Script rendering with typewriter effect
- Player choice handling
- Session management
- API communication

#### GlassDialogueBox
Dialogue display component featuring:
- Glass morphism styling
- Typewriter animation
- Speaker identification
- Choice presentation

#### GameService
API client service providing:
- Session initialization
- Turn processing
- Error handling
- Response parsing

### Backend Key Components

#### LLMRepository
OpenAI integration handling:
- Structured output generation
- Memory context injection
- Token management
- Error recovery

#### AnchorService
Context building with:
- Multi-chunk assembly
- Cross-chapter transitions
- Storyline navigation
- Text extraction

#### MemoryManager
LangGraph integration for:
- Short-term memory (20 events)
- Long-term memory persistence
- Semantic search capability
- Background summarization

## ⚙️ Configuration

### Environment Variables
```bash
# backend_services/api_keys.env
OPENAI_API_KEY=your-api-key-here
OPENAI_ORG_ID=your-org-id  # optional
```

### Frontend Configuration
- `vite.config.js` - Build configuration
- `tailwind.config.js` - Styling configuration
- `tsconfig.json` - TypeScript configuration

### Backend Configuration
- `app/core/config.py` - Application settings
- `llm_settings.py` - AI model configuration
- CORS and middleware settings

## 👨‍💻 Development Guide

### Setup Instructions

#### Backend Setup
```bash
cd backend_services
pip install -r requirements.txt
cp api_keys.env.example api_keys.env
# Edit api_keys.env with your OpenAI API key
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup
```bash
npm install
npm run dev
```

### Code Standards
- TypeScript strict mode enabled
- Pydantic models for API validation
- Comprehensive error handling
- Logging at all service levels

### Testing
- Frontend: Component testing setup
- Backend: FastAPI test client
- API connectivity tests included

### Deployment Considerations
- Docker support planned
- Environment-based configuration
- Production logging setup
- Performance monitoring hooks

## 📈 Performance Optimization

### Frontend
- Lazy loading for components
- Memoization for expensive operations
- Debounced API calls
- Optimized re-renders

### Backend
- Async/await throughout
- Connection pooling
- Response caching
- Batch processing capabilities

## 🔒 Security Features

- API key management
- CORS configuration
- Input validation
- Rate limiting ready
- Secure file operations

## 🚀 Future Enhancements

### Planned Features
- Multi-language support
- Voice acting integration
- Save slot management
- Achievement system
- Analytics dashboard

### Technical Roadmap
- GraphQL API option
- WebSocket support
- Redis caching
- Kubernetes deployment
- Performance monitoring

---

*This index is generated from the WhatIf codebase and reflects the current project structure as of 2025-07-30.*