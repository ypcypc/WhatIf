# WhatIf Quick Reference Guide

## 🚀 Quick Start

### Running the Project
```bash
# Terminal 1 - Backend
cd backend_services
source api_keys.env  # Load API keys
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
npm run dev
```

### Access Points
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Key Files & Locations

### Frontend
- **Entry Point**: `src/main.tsx`
- **Main App**: `src/App.tsx`
- **Game Logic**: `src/components/InteractiveGameReader.tsx`
- **API Client**: `src/services/gameService.ts`
- **State Store**: `src/stores/gameStore.ts`

### Backend
- **Entry Point**: `backend_services/app/main.py`
- **Game Flow**: `app/services/game_router.py`
- **AI Logic**: `app/services/llm_service/services.py`
- **Text Management**: `app/services/anchor_service/services.py`

### Configuration
- **API Keys**: `backend_services/api_keys.env`
- **Frontend Config**: `vite.config.js`, `tsconfig.json`
- **Backend Config**: `app/core/config.py`

## 🔑 Key Concepts

### Anchors
- **What**: Predefined story nodes in the narrative
- **Format**: `a{chapter}_{index}` (e.g., `a1_5`)
- **Purpose**: Navigate non-linear storylines

### Deviation System
- **0.00**: Perfect text preservation
- **≤0.05**: Minor optimization only
- **≤0.30**: Moderate adaptation allowed
- **>0.30**: Significant changes, guided back

### Script Units
1. **Narration**: Story description
2. **Dialogue**: Character speech
3. **Interaction**: Player choice point

## 🛠️ Common Tasks

### Add New Character
1. Update `data/characters_data.json`
2. Add character ID mapping in `game_router.py`
3. Update frontend character assets

### Modify AI Behavior
1. Edit `app/services/llm_service/llm_settings.py`
2. Adjust prompts in `repositories.py`
3. Update deviation logic in `services.py`

### Add New Route
1. Create endpoint in appropriate router
2. Add to main.py router registration
3. Update frontend API client
4. Add TypeScript types

## 🐛 Debugging

### Check Logs
```bash
# Backend logs
tail -f backend_services/logs/app.log

# Frontend console
Open browser DevTools (F12)
```

### Common Issues

**OpenAI API Error**
- Check `api_keys.env` has valid key
- Verify API quota/limits
- Check network connectivity

**Empty Context Error**
- Verify text chunks exist in data/
- Check anchor ID is valid
- Ensure storyline data loaded

**CORS Error**
- Backend running on port 8000?
- Check `middleware.py` CORS settings
- Frontend proxy configured?

## 📊 Data Structures

### Session State
```python
{
    "session_id": "player_123",
    "protagonist": "c_san_shang_wu",
    "globals": {
        "deviation": 0.15,
        "affinity": {"char_003": 50},
        "flags": {"named": true},
        "variables": {}
    },
    "turn_number": 5
}
```

### API Response
```typescript
{
    script: ScriptUnit[],
    updated_state: GlobalState,
    anchor_info: {
        current_anchor_id: string,
        next_anchor_id: string,
        chapter_id: number
    }
}
```

## 🎮 Game Flow

1. **Start** → Load first anchor → Generate opening
2. **Turn** → Player choice → Find next anchor → Generate script
3. **Save** → Events to JSONL → Snapshot to JSON
4. **Memory** → Short-term (20 events) → Long-term (FAISS)

## 🔧 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
OPENAI_ORG_ID=org-...
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173"]
```

## 📝 Testing

### Frontend Testing
```bash
npm test
npm run test:coverage
```

### Backend Testing
```bash
cd backend_services
pytest
pytest --cov=app
```

### API Testing
- Use Swagger UI at `/docs`
- Postman collection available
- cURL examples in API_REFERENCE.md

## 🚀 Performance Tips

### Frontend
- Use production build: `npm run build`
- Enable text compression
- Lazy load heavy components
- Minimize re-renders

### Backend
- Use Redis for caching (future)
- Batch API calls when possible
- Monitor OpenAI token usage
- Profile slow endpoints

## 📦 Deployment Checklist

- [ ] Set production API keys
- [ ] Configure CORS for domain
- [ ] Build frontend: `npm run build`
- [ ] Set up reverse proxy
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Test all endpoints
- [ ] Backup data files

## 🔗 Useful Commands

```bash
# Generate requirements
pip freeze > requirements.txt

# Format Python code
black backend_services/

# Lint TypeScript
npm run lint

# Type check
npm run tsc

# Clean install
rm -rf node_modules package-lock.json
npm install
```

## 📚 Further Reading

- [PROJECT_INDEX.md](./PROJECT_INDEX.md) - Complete project structure
- [API_REFERENCE.md](./API_REFERENCE.md) - Full API documentation
- [COMPONENT_DIAGRAM.md](./COMPONENT_DIAGRAM.md) - Architecture diagrams
- [README.md](./README.md) - Project overview

---

*Quick Reference for WhatIf v0.1.0 - Last updated: 2025-07-30*