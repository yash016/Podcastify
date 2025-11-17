"""
Enhanced episode generation endpoint for MVP_0.
Supports document-based generation with concept extraction and interactive features.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm import llm_service
from app.services.tts_unified import unified_tts_service
from app.services.concept_extractor import init_concept_extractor
from app.core.logging_config import get_logger

# Import sessions from upload endpoint
from app.api.endpoints.upload import sessions

router = APIRouter()
logger = get_logger(__name__)

# Get data directory
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Initialize concept extractor (lazy initialization)
concept_extractor = None


def get_concept_extractor():
    """Get or initialize concept extractor."""
    global concept_extractor
    if concept_extractor is None:
        concept_extractor = init_concept_extractor(llm_service)
    return concept_extractor


class GenerateRequest(BaseModel):
    session_id: Optional[str] = None  # MVP_0: From document upload
    topic: Optional[str] = None  # Fallback: Direct topic input


class GenerateResponse(BaseModel):
    episode_id: str
    title: str
    socratic_question: str
    key_insight: str
    duration_min: float
    turn_count: int
    audio_url: str
    # MVP_0 additions:
    concepts: List[Dict[str, Any]] = []
    concept_map: Dict[str, Dict[str, Any]] = {}
    pause_moments: List[Dict[str, Any]] = []
    dialogue_script: List[Dict[str, Any]] = []
    chapters: List[Dict[str, Any]] = []  # NEW: Chapter navigation


def _map_concepts_to_timestamps(
    concepts: List[Dict],
    timed_script: List[Dict],
    dialogue_concept_map: Dict
) -> List[Dict]:
    """
    Map concepts to precise timestamps based on actual audio timing.

    Args:
        concepts: List of concepts extracted from document
        timed_script: Dialogue script with actual timing metadata (start_timestamp, end_timestamp)
        dialogue_concept_map: Dict mapping concept names to turn indices

    Returns:
        List of concepts enriched with actual timestamps
    """
    for concept in concepts:
        concept_name = concept['name']

        # Get dialogue info (turn where concept appears)
        dialogue_info = dialogue_concept_map.get(concept_name)

        if dialogue_info:
            turn_index = dialogue_info['turn_index']

            # Safety check: ensure turn exists in timed_script
            if 0 <= turn_index < len(timed_script):
                turn = timed_script[turn_index]

                # Use actual turn timestamp (not estimated!)
                concept['turn_index'] = turn_index
                concept['turn_timestamp'] = turn.get('start_timestamp', 0)
                concept['absolute_timestamp'] = turn.get('start_timestamp', 0)
                concept['section_id'] = turn.get('section_id', '')

                logger.debug(
                    "concept_mapped_to_timestamp",
                    concept=concept_name,
                    timestamp=concept['absolute_timestamp']
                )
            else:
                logger.warning(
                    "concept_turn_index_out_of_range",
                    concept=concept_name,
                    turn_index=turn_index,
                    script_length=len(timed_script)
                )
                concept['absolute_timestamp'] = None
        else:
            # Concept not mentioned in dialogue
            concept['absolute_timestamp'] = None
            logger.debug(
                "concept_not_in_dialogue",
                concept=concept_name
            )

    return concepts


def _generate_chapters_from_sections(
    outline: Dict,
    timed_script: List[Dict],
    concepts: List[Dict]
) -> List[Dict]:
    """
    Generate chapter markers from outline sections using actual timing.

    Args:
        outline: Podcast outline with sections
        timed_script: Dialogue script with actual timing metadata
        concepts: List of concepts with section_id mappings

    Returns:
        List of chapter dictionaries with timestamps and metadata
    """
    chapters = []

    for i, section in enumerate(outline.get('sections', []), start=1):
        # Get section ID with fallback: id -> title -> generated "section_N"
        section_id = section.get('id') or section.get('title') or f"section_{i}"

        # Find all turns in this section
        section_turns = [
            turn for turn in timed_script
            if turn.get('section_id') == section_id
        ]

        if not section_turns:
            logger.warning(
                "section_has_no_turns",
                section_id=section_id,
                section_title=section.get('title', 'Untitled'),
                section_index=i
            )
            continue

        # Chapter starts at first turn, ends at last turn
        start_timestamp = section_turns[0].get('start_timestamp', 0)
        end_timestamp = section_turns[-1].get('end_timestamp', 0)

        # Find concepts in this section
        section_concepts = [
            c['id'] for c in concepts
            if c.get('section_id') == section_id and c.get('absolute_timestamp') is not None
        ]

        chapter = {
            "id": f"ch_{section_id}",
            "title": section.get('title', 'Untitled'),
            "timestamp": start_timestamp,
            "duration": end_timestamp - start_timestamp,
            "section_id": section_id,
            "key_concepts": section_concepts,
            "turn_count": len(section_turns)
        }

        chapters.append(chapter)

        logger.debug(
            "chapter_generated",
            chapter_id=chapter['id'],
            timestamp=start_timestamp,
            duration=chapter['duration'],
            concepts=len(section_concepts)
        )

    return chapters


@router.post("/generate", response_model=GenerateResponse)
async def generate_episode(request: GenerateRequest):
    """
    Generate a complete 2-3 minute interactive learning episode with concepts.

    MVP_0 Features:
    - Document-based generation (session_id from upload)
    - Concept extraction and tagging
    - Retrieval practice pause moments
    - Interactive concept graph data
    """
    # Determine source: session_id (uploaded document) or topic (direct input)
    document_text = None
    topic = None
    source_filename = None

    if request.session_id:
        # MVP_0: Get uploaded document from session
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found or expired")

        session_data = sessions[request.session_id]
        document_text = session_data['text']
        source_filename = session_data['filename']

        # Use first 100 chars as topic summary
        topic = document_text[:100].replace('\n', ' ').strip()
        logger.info("generating_from_document", session_id=request.session_id, filename=source_filename)

    elif request.topic:
        topic = request.topic.strip()
        logger.info("generating_from_topic", topic=topic)
    else:
        raise HTTPException(status_code=400, detail="Either session_id or topic must be provided")

    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    try:
        # MVP_0 Step 1: Extract concepts from document (if available)
        document_concepts = []
        if document_text:
            logger.info("extracting_concepts_from_document")
            extractor = get_concept_extractor()
            document_concepts = await extractor.extract_concepts_from_document(
                document_text=document_text,
                target_count=10
            )
            logger.info("concepts_extracted", count=len(document_concepts))

        # Step 2: Generate outline
        logger.info("generating_outline")
        outline = await llm_service.generate_outline(
            topic=topic,
            level="adaptive",
            duration=1.0,  # Reduced from 3.0 for faster testing
        )

        # Step 3: Generate dialogue (now includes concept markers and pause moments)
        logger.info("generating_dialogue_with_learning_features")
        dialogue_result = await llm_service.generate_dialogue(
            outline=outline,
            teaching_materials=document_concepts,  # Pass concepts so LLM incorporates them
            topic=topic,
            level="adaptive",
            duration=1.0,  # Reduced from 3.0 for faster testing
        )

        script = dialogue_result["script"]
        metadata = dialogue_result["metadata"]

        # MVP_0 Step 4: Extract concepts and pause moments from dialogue
        extractor = get_concept_extractor()
        dialogue_concept_map = extractor.extract_concepts_from_dialogue(script)
        pause_moments = extractor.extract_pause_moments(script)

        # MVP_0 Step 5: Merge document concepts with dialogue concepts
        if document_concepts:
            enriched_concepts = extractor.merge_concepts(
                document_concepts,
                dialogue_concept_map,
                dialogue_script=script  # Pass dialogue for fuzzy concept matching
            )
        else:
            # Use only dialogue-extracted concepts
            enriched_concepts = [
                {
                    "id": f"c{i+1}",
                    "name": name,
                    "definition": info.get("text_snippet", ""),
                    "importance": 0.7,
                    "timestamp": info.get("estimated_timestamp"),
                    "turn_index": info.get("turn_index"),
                    "mentioned_in_dialogue": True
                }
                for i, (name, info) in enumerate(dialogue_concept_map.items())
            ]

        logger.info(
            "concepts_processed",
            total_concepts=len(enriched_concepts),
            dialogue_concepts=len(dialogue_concept_map),
            pause_moments=len(pause_moments)
        )

        # Step 6: Generate audio
        logger.info("generating_audio", turn_count=len(script))

        # Create unique episode ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        episode_id = f"ep_{timestamp}"
        audio_filename = f"{episode_id}.mp3"
        audio_path = AUDIO_DIR / audio_filename

        # Generate audio using unified TTS service (Parler TTS with parallel processing)
        audio_result = await unified_tts_service.generate_episode_audio(
            script=script,
            output_path=str(audio_path),
            silence_between_turns=400,  # 400ms for faster pace
            use_emotions=True
        )

        # NEW Step 7: Enrich dialogue script with actual timing metadata
        turn_timings = audio_result.get('turn_timings', [])

        for turn, timing in zip(script, turn_timings):
            turn['start_timestamp'] = timing['start_ms'] / 1000.0  # Convert ms to seconds
            turn['end_timestamp'] = timing['end_ms'] / 1000.0
            turn['duration_ms'] = timing['duration_ms']

        # NEW Step 8: Map concepts to precise timestamps using actual timing
        precise_concepts = _map_concepts_to_timestamps(
            enriched_concepts,
            script,  # Now has actual timestamps!
            dialogue_concept_map
        )

        # NEW Step 9: Generate chapter markers from sections
        chapters = _generate_chapters_from_sections(
            outline,
            script,  # With timing metadata
            precise_concepts
        )

        logger.info(
            "mvp0_episode_generation_complete",
            episode_id=episode_id,
            duration_sec=audio_result['duration_seconds'],
            turn_count=len(script),
            concepts=len(precise_concepts),
            pause_moments=len(pause_moments),
            chapters=len(chapters)
        )

        # Return enhanced MVP_0 response with chapters and precise timestamps
        return GenerateResponse(
            episode_id=episode_id,
            title=outline.get("title", "Micro-Episode"),
            socratic_question=outline.get("socratic_question", ""),
            key_insight=outline.get("key_insight", ""),
            duration_min=round(audio_result['duration_seconds'] / 60, 1),
            turn_count=len(script),
            audio_url=f"/api/audio/{audio_filename}",
            # MVP_0 additions:
            concepts=precise_concepts,  # Now with ACTUAL timestamps!
            concept_map=dialogue_concept_map,
            pause_moments=pause_moments,
            dialogue_script=script,  # Now with timing metadata
            chapters=chapters  # NEW: Chapter navigation
        )

    except Exception as e:
        logger.error("episode_generation_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate episode: {str(e)}"
        )


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """
    Serve audio file.
    """
    from fastapi.responses import FileResponse

    audio_path = AUDIO_DIR / filename

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )
