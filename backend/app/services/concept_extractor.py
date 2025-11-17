"""
Concept extraction service for MVP_0.
Extracts key concepts from documents and dialogue for interactive learning.
"""

import json
import re
from typing import List, Dict, Any, Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConceptExtractor:
    """
    Extracts and maps concepts for interactive learning features.
    """

    def __init__(self, llm_service):
        """
        Args:
            llm_service: LLMService instance for concept extraction
        """
        self.llm = llm_service

    async def extract_concepts_from_document(
        self,
        document_text: str,
        target_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract key concepts from uploaded document using LLM.

        Args:
            document_text: The full document text
            target_count: Target number of concepts (8-12)

        Returns:
            List of concept dictionaries with id, name, definition, importance
        """
        logger.info("extracting_concepts", text_length=len(document_text))

        prompt = f"""Analyze this educational content and extract the {target_count} most important concepts.

Document:
{document_text[:3000]}

Return ONLY valid JSON (no markdown, no explanation) in this exact structure:
{{
  "concepts": [
    {{
      "id": "c1",
      "name": "Photosynthesis",
      "definition": "The process by which plants convert light energy into chemical energy",
      "importance": 0.95,
      "category": "core_process"
    }}
  ]
}}

Guidelines:
- Extract {target_count} concepts (±2)
- Use clear, natural concept names (not technical jargon)
- Importance: 0.0-1.0 scale (most important = 1.0)
- Categories: "core_process", "mechanism", "component", "principle", "outcome"
- Focus on CORE ideas, not minor details
- Sort by importance (most important first)
"""

        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_instruction="You are an expert at identifying key concepts in educational content. Return only valid JSON.",
                temperature=0.3,  # Lower temp for more consistent concept extraction
                max_tokens=2048,
                response_format="json"
            )

            # Parse JSON response
            # First, clean the result in case LLM wraps it in markdown code blocks
            result_cleaned = result.strip()
            if result_cleaned.startswith('```json'):
                result_cleaned = result_cleaned[7:]  # Remove ```json
            if result_cleaned.startswith('```'):
                result_cleaned = result_cleaned[3:]  # Remove ```
            if result_cleaned.endswith('```'):
                result_cleaned = result_cleaned[:-3]  # Remove trailing ```
            result_cleaned = result_cleaned.strip()

            concepts_data = json.loads(result_cleaned)

            # Validate structure - ensure it's a dict, not a string
            if not isinstance(concepts_data, dict):
                logger.error("concept_extraction_invalid_type",
                           type=type(concepts_data).__name__,
                           data_preview=str(concepts_data)[:200])
                raise ValueError(f"Expected dict but got {type(concepts_data).__name__}")

            if "concepts" not in concepts_data:
                logger.error("concept_extraction_missing_key", keys=list(concepts_data.keys()))
                raise ValueError("Response missing 'concepts' key")

            concepts = concepts_data["concepts"]

            # Validate concepts is a list
            if not isinstance(concepts, list):
                logger.error("concepts_invalid_type",
                           type=type(concepts).__name__,
                           data_preview=str(concepts)[:200])
                raise ValueError(f"Expected list of concepts but got {type(concepts).__name__}")

            logger.info("concepts_extracted", count=len(concepts))
            return concepts

        except json.JSONDecodeError as e:
            logger.error("concept_extraction_json_error", error=str(e), response=result[:200])
            # Return fallback concepts
            return self._create_fallback_concepts(document_text)
        except Exception as e:
            logger.error("concept_extraction_failed", error=str(e))
            return self._create_fallback_concepts(document_text)

    async def extract_concept_relationships(
        self,
        concepts: List[Dict[str, Any]],
        document_text: str
    ) -> List[Dict[str, Any]]:
        """
        Identify relationships between concepts for graph visualization.

        Args:
            concepts: List of extracted concepts
            document_text: Original document text

        Returns:
            List of relationship dicts with source_id, target_id, type, strength
        """
        concept_names = [c["name"] for c in concepts]

        prompt = f"""Given these concepts from an educational text, identify the key relationships between them.

Concepts:
{json.dumps(concept_names, indent=2)}

Document excerpt:
{document_text[:2000]}

Return ONLY valid JSON (no markdown) with relationships:
{{
  "relationships": [
    {{
      "source_id": "c1",
      "target_id": "c2",
      "type": "enables",
      "strength": 0.8,
      "description": "Photosynthesis enables glucose production"
    }}
  ]
}}

Relationship types: "enables", "requires", "produces", "part_of", "similar_to", "contrasts_with"
Strength: 0.0-1.0 (strongest = 1.0)
Include 5-15 relationships total.
"""

        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_instruction="You are an expert at identifying conceptual relationships. Return only valid JSON.",
                temperature=0.3,
                max_tokens=1024,
                response_format="json"
            )

            relationships_data = json.loads(result)
            return relationships_data.get("relationships", [])

        except Exception as e:
            logger.error("relationship_extraction_failed", error=str(e))
            return []

    def extract_concepts_from_dialogue(
        self,
        dialogue_script: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract concept markers and timestamps from generated dialogue.

        Looks for [CONCEPT: name] markers in dialogue text.

        Args:
            dialogue_script: List of dialogue turns with speaker, text, etc.

        Returns:
            Dict mapping concept_name -> {turn_index, timestamp, speaker, text_snippet}
        """
        concept_map = {}
        avg_turn_duration = 15  # seconds per turn (estimated)

        for i, turn in enumerate(dialogue_script):
            text = turn.get("text", "")

            # Find all [CONCEPT: ...] markers
            concept_matches = re.findall(r'\[CONCEPT:\s*([^\]]+)\]', text)

            for concept_name in concept_matches:
                concept_name = concept_name.strip()

                # Only track first mention of each concept
                if concept_name not in concept_map:
                    # Extract a snippet of text around the concept
                    snippet = text.replace(f'[CONCEPT: {concept_name}]', concept_name)
                    snippet = snippet[:100] + "..." if len(snippet) > 100 else snippet

                    concept_map[concept_name] = {
                        "turn_index": i,
                        "estimated_timestamp": i * avg_turn_duration,
                        "speaker": turn.get("speaker", "Unknown"),
                        "text_snippet": snippet,
                        "section_id": turn.get("section_id", "")
                    }

        logger.info("concepts_extracted_from_dialogue", count=len(concept_map))
        return concept_map

    def extract_pause_moments(
        self,
        dialogue_script: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract retrieval practice pause moments from dialogue.

        Looks for [PAUSE: prompt] markers.

        Args:
            dialogue_script: List of dialogue turns

        Returns:
            List of pause moment dicts with turn_index, timestamp, prompt
        """
        pause_moments = []
        avg_turn_duration = 15

        for i, turn in enumerate(dialogue_script):
            text = turn.get("text", "")

            # Find [PAUSE: ...] markers
            pause_matches = re.findall(r'\[PAUSE:\s*([^\]]+)\]', text)

            for pause_prompt in pause_matches:
                pause_moments.append({
                    "turn_index": i,
                    "estimated_timestamp": i * avg_turn_duration,
                    "speaker": turn.get("speaker", ""),
                    "prompt": pause_prompt.strip(),
                    "pause_duration_sec": 3  # 3-second pause for retrieval
                })

        logger.info("pause_moments_extracted", count=len(pause_moments))
        return pause_moments

    def merge_concepts(
        self,
        document_concepts: List[Dict[str, Any]],
        dialogue_concept_map: Dict[str, Dict[str, Any]],
        dialogue_script: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Merge concepts extracted from document with those found in dialogue.

        Adds timestamp information to document concepts based on dialogue mentions.

        Args:
            document_concepts: Concepts extracted from original document
            dialogue_concept_map: Concept markers found in dialogue with timestamps
            dialogue_script: Full dialogue script for fuzzy concept matching

        Returns:
            Enriched concept list with timestamps
        """
        enriched_concepts = []

        for doc_concept in document_concepts:
            concept_name = doc_concept["name"]

            # Check if this concept was mentioned in dialogue (explicit markers)
            dialogue_info = dialogue_concept_map.get(concept_name)

            # If no explicit marker, try to find concept in dialogue text
            if not dialogue_info and dialogue_script:
                dialogue_info = self._find_concept_in_dialogue(
                    concept_name,
                    dialogue_script
                )

            enriched = {
                **doc_concept,
                "mentioned_in_dialogue": dialogue_info is not None,
            }

            if dialogue_info:
                enriched.update({
                    "timestamp": dialogue_info["estimated_timestamp"],
                    "turn_index": dialogue_info["turn_index"],
                    "speaker": dialogue_info.get("speaker", ""),
                    "context_snippet": dialogue_info.get("text_snippet", "")
                })
            else:
                # Concept not explicitly mentioned in dialogue
                enriched.update({
                    "timestamp": None,
                    "turn_index": None
                })

            enriched_concepts.append(enriched)

        # Sort by importance, then by timestamp
        enriched_concepts.sort(
            key=lambda x: (
                -x.get("importance", 0),
                x.get("timestamp") if x.get("timestamp") is not None else 9999
            )
        )

        return enriched_concepts

    def _find_concept_in_dialogue(
        self,
        concept_name: str,
        dialogue_script: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Search for concept mentions in dialogue text (fuzzy matching).

        Args:
            concept_name: Name of concept to search for
            dialogue_script: Full dialogue script

        Returns:
            Dialogue info dict with timestamp if found, None otherwise
        """
        avg_turn_duration = 15

        # Create search patterns (case-insensitive)
        # Handle multi-word concepts like "Light Energy Conversion" -> ["light energy", "light"]
        concept_lower = concept_name.lower()
        search_terms = [concept_lower]

        # Add variations without common words
        filtered_words = [
            word for word in concept_lower.split()
            if word not in ['the', 'a', 'an', 'of', 'in', 'and', 'or']
        ]

        # Add individual important words if multi-word concept
        if len(filtered_words) > 1:
            search_terms.extend(filtered_words)

        # Search through dialogue
        for i, turn in enumerate(dialogue_script):
            text = turn.get("text", "").lower()

            # Check if any search term appears in this turn
            for term in search_terms:
                if term in text:
                    return {
                        "turn_index": i,
                        "estimated_timestamp": i * avg_turn_duration,
                        "speaker": turn.get("speaker", ""),
                        "text_snippet": turn.get("text", "")[:100]
                    }

        return None

    def _create_fallback_concepts(self, document_text: str) -> List[Dict[str, Any]]:
        """Create simple fallback concepts if LLM extraction fails."""
        # Extract first few sentences as basic concepts
        sentences = document_text.split('.')[:5]

        fallback_concepts = []
        for i, sentence in enumerate(sentences):
            if len(sentence.strip()) > 10:
                # Extract first few words as concept name
                words = sentence.strip().split()[:3]
                name = ' '.join(words).replace('\n', ' ')

                fallback_concepts.append({
                    "id": f"c{i+1}",
                    "name": name,
                    "definition": sentence.strip()[:100],
                    "importance": 0.5,
                    "category": "fallback"
                })

        logger.warning("using_fallback_concepts", count=len(fallback_concepts))
        return fallback_concepts[:8]


# Global instance (will be initialized with llm_service)
concept_extractor: Optional[ConceptExtractor] = None


def init_concept_extractor(llm_service):
    """Initialize the global concept extractor with LLM service."""
    global concept_extractor
    concept_extractor = ConceptExtractor(llm_service)
    logger.info("concept_extractor_initialized")
    return concept_extractor
