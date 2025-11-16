# Podcastify MVP_0 - 12-Hour Hackathon Build

> Interactive learning podcasts that beat Google NotebookLM with research-backed learning science

**Timeline**: 12 hours (hackathon_mvp_0)
**Goal**: Build a fully working prototype with interactive features NotebookLM lacks

---

## What is This?

This is a **self-contained MVP_0 implementation** of Podcastify, focused on building the core interactive learning features in 12 hours.

### Why MVP_0 Beats NotebookLM

| Feature | NotebookLM | Podcastify MVP_0 |
|---------|-----------|------------------|
| **Interactivity** | ❌ Passive audio only | ✅ Concept navigation, quizzes |
| **Visual Learning** | ❌ Audio-only | ✅ Dual coding (coming in MVP_1) |
| **Testing Understanding** | ❌ No quizzes | ✅ Retrieval practice quizzes |
| **Concept Navigation** | ❌ Linear playback only | ✅ Click concepts → jump to timestamp |
| **Learning Science** | ❌ None applied | ✅ Research-backed (6 principles) |

**Research Backing**:
- Active learning: 93.5% retention vs 79% passive (VanLehn 2011)
- Retrieval practice: 54% improvement in long-term retention (Roediger 2011)
- Dual coding: 89% better recall than single-mode (Paivio 1990)

---

## Quick Start (5 minutes)

### Prerequisites

- Python 3.11+
- Gemini API key (get free at https://makersuite.google.com/app/apikey)

### Setup

1. **Navigate to backend**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

5. **Run the server**:
   ```bash
   python -m app.main
   ```

6. **Open in browser**:
   ```
   http://localhost:8000
   ```

---

## MVP_0 Features (12 Hours)

### ✅ Core Features

1. **Document Upload & Processing** (90 min)
   - Accept PDF, text files, or paste content
   - Extract text and prepare for podcast generation

2. **Learning Science-Enhanced Dialogue** (120 min)
   - Brainy & Snarky personalities
   - Retrieval practice "pause and predict" moments
   - Concept markers for navigation

3. **Interactive Concept Graph** (150 min)
   - Visual network of key concepts (D3.js)
   - Click concept → jump to timestamp in audio
   - Track which concepts have been covered

4. **Enhanced Audio Player with Analytics** (90 min)
   - Engagement tracking (play, pause, rewind, speed)
   - **Struggle detection**: Identify wheel-spinning vs productive struggle
   - Adaptive recommendations

5. **Live Transcript with Auto-Highlighting** (75 min)
   - Real-time transcript display
   - Auto-scroll and highlight current sentence
   - Clickable to jump to specific moments

6. **Retrieval Practice Quiz System** (150 min)
   - Post-episode quizzes with 5-7 questions
   - Immediate feedback with misconception correction
   - Link wrong answers → relevant timestamp

### ❌ Explicitly NOT in MVP_0

Saving for MVP_1 or later:
- Visual dual coding (concept images)
- 3-part episode series (scaffolding)
- Spaced repetition
- User accounts/database
- Mobile app
- Advanced graph layouts

---

## Project Structure

```
podcastify_mvp_0/
├── backend/
│   ├── app/
│   │   ├── api/endpoints/     # FastAPI routes
│   │   ├── core/              # Config, logging
│   │   ├── services/          # LLM, TTS services
│   │   ├── models/            # Pydantic schemas
│   │   ├── static/            # Web UI (index.html)
│   │   └── main.py            # FastAPI app
│   ├── requirements.txt
│   └── .env.example
├── prompts/
│   ├── dialogue_generation.md  # Brainy/Snarky dialogue
│   ├── outline_generation.md   # Episode structure
│   └── research_compression.md # RAG (not used in MVP_0)
├── data/
│   └── audio/                  # Generated podcast files
├── docs/
│   ├── HACKATHON_STRATEGY_FINAL.md
│   ├── LEARNING_SCIENCE_CROSSREFERENCE.md
│   ├── PROJECT_VISION.md
│   └── ZPD_ADAPTIVE_LEARNING_PRINCIPLES.md
└── README.md                   # This file
```

---

## Demo Script (3-4 minutes)

**Perfect demo flow for judges**:

1. **Upload** "Photosynthesis.pdf" (5 pages)
2. **Click** "Generate Learning Podcast"
3. **See** interactive concept graph (10 concepts: Chlorophyll, Light Reactions, etc.)
4. **Play** audio - Brainy explains, Snarky questions
5. **Pause moment** at 1:15 - "Before we continue, what do YOU think happens next?"
6. **Click** "Chlorophyll" in graph → audio jumps to 0:45 where it's discussed
7. **Transcript** auto-scrolls, highlights current sentence
8. **Rewind** same section 3x → "This seems challenging, need help?" notification
9. **Quiz** appears after podcast ends (5 questions)
10. **Answer** question → immediate feedback ("Not quite - LSTMs don't use bigger gradients, they preserve them. Replay at 1:23?")
11. **Results** → "4/5 - Excellent! You've mastered 8/10 concepts"

---

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **LLM**: Gemini 2.0 Flash (free tier!)
- **TTS**: Chatterbox (HuggingFace Gradio client)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no framework)
- **Concept Graph**: D3.js force-directed layout
- **Storage**: localStorage (no database for hackathon)

---

## Cost per Episode

- **LLM (Gemini Flash)**: $0.00 (free tier)
- **TTS (Chatterbox)**: $0.00 (open-source)
- **Total**: **FREE** 🎉

---

## Implementation Checklist

See [`docs/MVP_0_IMPLEMENTATION_CHECKLIST.md`](docs/MVP_0_IMPLEMENTATION_CHECKLIST.md) for detailed feature breakdown and time allocations.

---

## Key Documentation

1. **HACKATHON_STRATEGY_FINAL.md** - Complete 12-hour implementation plan
2. **LEARNING_SCIENCE_CROSSREFERENCE.md** - Research-backed learning principles
3. **PROJECT_VISION.md** - Why we're building this, NotebookLM differentiation
4. **ZPD_ADAPTIVE_LEARNING_PRINCIPLES.md** - Zone of Proximal Development theory

---

## Success Criteria

✅ Must demonstrate this flow perfectly:
- Upload document → Generate podcast in 30-60 seconds
- Interactive concept graph with 8-12 concepts
- Audio with 2-3 "pause and predict" moments
- Click concept → jump to timestamp
- Live transcript with auto-highlighting
- Struggle detection with intervention
- Post-episode quiz with immediate feedback

---

## Development Timeline

**Total: 12 hours**

1. Document Upload (90 min) - Hours 0-1.5
2. Enhanced Dialogue Generation (120 min) - Hours 1.5-3.5
3. Interactive Concept Graph (150 min) - Hours 3.5-6
4. Enhanced Audio Player (90 min) - Hours 6-7.5
5. Live Transcript (75 min) - Hours 7.5-8.75
6. Quiz System (150 min) - Hours 8.75-11.25
7. Polish & Integration (60 min) - Hours 11.25-12

---

## Troubleshooting

### "ModuleNotFoundError"
Make sure you're in the `backend/` directory with activated venv:
```bash
cd backend
source venv/bin/activate
```

### "401 Unauthorized from Gemini"
Check your API key in `.env` (no quotes):
```bash
GEMINI_API_KEY=AIzaSy...  # ✅ Correct
```

### Server won't start
Check if port 8000 is available:
```bash
lsof -ti:8000 | xargs kill -9  # Kill existing process
```

---

## Next Steps

After completing MVP_0:
1. ✅ Test with 5-10 users
2. ✅ Gather feedback on interactivity
3. ➡️ Start MVP_1 (12 hours): Visual dual coding, episode series, embedded checkpoints

See parent Podcastify project for full roadmap (3-12 months).

---

**Status**: MVP_0 - 12-Hour Hackathon Build
**Last Updated**: November 15, 2025
**Next Milestone**: Complete all 6 core features in 12 hours
