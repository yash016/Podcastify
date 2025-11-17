# Podcastify

> Building on NotebookLM's Audio Overview with interactive learning features

Transform your study materials into engaging two-person conversational podcasts with concept graphs, synchronized transcripts, and Socratic quizzes.

---

## 🎯 What is Podcastify?

Podcastify replicates Google's NotebookLM Audio Overview feature and enhances it with research-backed active learning tools:

- **Audio Overview**: Natural two-person dialogue generated from your documents
- **Concept Maps**: Interactive D3.js graph showing relationships between key ideas
- **Synchronized Transcript**: Auto-highlighted dialogue that follows along with audio
- **Socratic Quizzes**: Wrong-answer analysis with guided questioning (not just hints)
- **Chapter Navigation**: Jump to specific sections with timestamps

### Why Podcastify?

| Feature | NotebookLM | Podcastify |
|---------|-----------|------------|
| **Audio Generation** | ✅ Two-person dialogue | ✅ Two-person dialogue |
| **Concept Visualization** | ❌ | ✅ Interactive graph |
| **Quiz System** | ❌ | ✅ Socratic questioning |
| **Transcript** | ❌ | ✅ Synchronized highlighting |
| **Chapter Navigation** | ❌ | ✅ Section-based jumping |

**Learning Science**: Active learning with retrieval practice shows 93.5% retention vs 79% passive listening (VanLehn 2011)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Gemini API key](https://makersuite.google.com/app/apikey) (free tier available)
- [Parler TTS API](https://github.com/collabora/chatterbox-tts-api) (via ngrok or local)

### Setup

1. **Clone and navigate**:
   ```bash
   git clone https://github.com/yash016/Podcastify.git
   cd Podcastify/backend
   ```

2. **Create environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```bash
   GEMINI_API_KEY=your_key_here
   PARLER_TTS_URL=your_chatterbox_ngrok_url
   ```

4. **Run server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

5. **Open browser**:
   ```
   http://localhost:8001
   ```

---

## 📚 Features

### 1. Document Upload
- Upload PDFs or text files
- Paste content directly
- Session-based processing (no database required)

### 2. Podcast Generation
- Two-person conversational dialogue
- Natural voice synthesis with Parler TTS
- Concept-based section organization
- Configurable duration (1-3 minutes for testing, expandable)

### 3. Interactive Concept Graph
- D3.js force-directed layout
- Click concepts to jump to timestamps
- Visual relationship mapping
- Importance-based node sizing

### 4. Synchronized Transcript
- Auto-scrolling dialogue display
- Current sentence highlighting
- Speaker identification
- Clickable lines for navigation

### 5. Chapter Navigation
- Outline-based section markers
- Timestamp-based chapter jumping
- Concept count per section
- Duration tracking

### 6. Socratic Quiz System
- 5 multiple-choice questions per podcast
- **Dynamic hint generation** that analyzes YOUR specific wrong answer
- 3-level graduated hints (subtle → moderate → explicit)
- Wrong answer reasoning with guiding questions
- Question navigation (previous/next)
- Progress tracking

---

## 🏗️ Architecture

### Tech Stack

**Backend**:
- FastAPI (async Python web framework)
- Google Gemini 2.5 Flash (LLM for outline, dialogue, concepts, quizzes)
- Parler TTS via Chatterbox API (audio generation)
- PyPDF2 (document parsing)

**Frontend**:
- Vanilla HTML/CSS/JavaScript
- D3.js (concept graph visualization)
- FilePond (document upload)
- HTML5 Audio API (playback control)

**Infrastructure**:
- Session-based architecture (no database)
- Local file storage for audio
- Async processing for speed

### Project Structure

```
Podcastify/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── endpoints/
│   │   │       ├── upload.py          # Document upload
│   │   │       ├── generate.py        # Podcast generation
│   │   │       └── quiz.py            # Quiz system
│   │   ├── services/
│   │   │   ├── llm.py                 # Gemini integration
│   │   │   ├── tts_unified.py         # Parler TTS client
│   │   │   ├── concept_extractor.py   # Concept extraction
│   │   │   ├── quiz_generator.py      # Quiz generation
│   │   │   └── socratic_hint_generator.py  # Dynamic hints
│   │   ├── models/
│   │   │   ├── schemas.py             # Pydantic models
│   │   │   └── quiz_session.py        # Quiz state
│   │   ├── static/
│   │   │   ├── index.html             # Landing page
│   │   │   └── generate.html          # Podcast player
│   │   └── main.py                    # FastAPI app
│   ├── requirements.txt
│   └── docker-compose.yml
└── README.md
```

---

## 🎮 Demo Flow

1. **Upload** a PDF or paste text (e.g., "Are We Living In A Simulation.pdf")
2. **Click** "Generate Learning Podcast"
3. **Watch** concept graph build (10+ concepts extracted)
4. **Listen** to two-person dialogue discussing key ideas
5. **See** transcript auto-scroll and highlight current dialogue
6. **Click** a concept in the graph → audio jumps to that timestamp
7. **Navigate** using chapter markers in the Outline section
8. **Answer** quiz questions after listening
9. **Get wrong answer?** → See Socratic hints analyzing YOUR specific choice
10. **Click hint levels** (💡 Level 1, 🔍 Level 2, 📖 Level 3) for more guidance
11. **Navigate questions** with Previous/Next buttons

---

## 🧠 Learning Science

### Socratic Questioning

Unlike generic hints, Podcastify analyzes the specific wrong answer you selected:

**Traditional Hint**:
> "Think about what happens in the light-dependent reactions."

**Podcastify Socratic Hint (Level 1)**:
> You selected "The Calvin cycle produces oxygen" - but where in the process does oxygen actually come from? What molecule gets split during photosynthesis?

**Level 2**:
> Your answer suggests oxygen comes from carbon fixation, but oxygen is actually released during water photolysis in Photosystem II. What would this mean for when oxygen appears?

**Level 3**:
> The Calvin cycle uses ATP and NADPH but doesn't produce oxygen. Oxygen is released when water molecules are split in the light reactions (around timestamp 1:23). This happens BEFORE the Calvin cycle.

### Research-Backed Principles

- **Active Recall**: Retrieval practice vs passive review (54% retention boost - Roediger 2011)
- **Graduated Hints**: Scaffolded support within Zone of Proximal Development
- **Dual Coding**: Audio + visual concept map (89% better recall - Paivio 1990)
- **Metacognitive Prompts**: Wrong answer analysis promotes self-reflection

---

## 🔧 API Endpoints

### Core Endpoints

```
POST /api/upload              # Upload PDF/text document
POST /api/upload/text         # Upload pasted text
POST /api/generate            # Generate podcast from session
GET  /api/audio/{filename}    # Serve generated audio
```

### Quiz Endpoints

```
POST /api/quiz/generate       # Generate quiz from session
POST /api/quiz/submit-answer  # Submit answer, get Socratic hints
POST /api/quiz/get-hint       # Request specific hint level
POST /api/quiz/navigate-question  # Previous/next question
```

---

## 💡 Development

### Running in Development

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# TTS Configuration
PARLER_TTS_URL=http://your-ngrok-url  # Chatterbox API endpoint

# Optional
LOG_LEVEL=INFO
```

### Key Configuration Files

- `backend/app/core/config.py` - Environment configuration
- `backend/app/core/logging_config.py` - Structured logging
- `backend/docker-compose.yml` - Container orchestration

---

## 📊 Cost per Episode

- **LLM (Gemini 2.5 Flash)**: ~$0.001 per episode (free tier: 1,500 requests/day)
- **TTS (Parler via Chatterbox)**: $0.00 (open-source, self-hosted)
- **Total**: ~$0.001 per episode 🎉

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Kill existing process on port 8001
lsof -ti:8001 | xargs kill -9
```

### Gemini API errors
```bash
# Check API key format (no quotes in .env)
GEMINI_API_KEY=AIzaSy...  # ✅ Correct
```

### TTS connection issues
- Verify Chatterbox is running: Visit ngrok URL in browser
- Check PARLER_TTS_URL in `.env` includes full protocol

### Quiz generation fails
- Ensure document was uploaded successfully (check session ID)
- Verify concepts were extracted (check backend logs)
- Gemini may occasionally return malformed JSON - retry generation

---

## 🚀 Deployment

### Docker (Recommended)

```bash
cd backend
docker-compose up -d
```

### Manual Deployment

1. Configure reverse proxy (nginx/Caddy)
2. Set up SSL certificates
3. Run with production ASGI server:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

---

## 🎯 Roadmap

### Current Features ✅
- Document upload and processing
- Two-person podcast generation
- Concept graph visualization
- Synchronized transcript
- Socratic quiz system

### Planned Features 🔜
- User accounts and progress tracking
- Spaced repetition scheduling
- Multi-document podcasts
- Custom voice profiles
- Mobile responsive design
- Offline mode

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **NotebookLM** - Inspiration for Audio Overview format
- **Google Gemini** - Powerful LLM for content generation
- **Parler TTS** - High-quality open-source voice synthesis
- **Learning Science Research** - VanLehn (2011), Roediger (2011), Paivio (1990)

---

## 📞 Contact

- **GitHub**: [@yash016](https://github.com/yash016)
- **Project**: [Podcastify](https://github.com/yash016/Podcastify)

---

**Built with research-backed learning science | Making education accessible through audio** 🎧
