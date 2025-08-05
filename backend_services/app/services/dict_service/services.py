"""
Dictionary Service Business Logic

Handles text segment retrieval, dictionary operations, and content management.
Coordinates between repositories and external APIs.
"""

import logging
import json
import os
from typing import List, Optional
from datetime import datetime

from .repositories import DictRepository, FileSystemRepository
from .schemas import SegmentResponse, DictLookupResponse, CharacterResponse, GlossaryResponse

logger = logging.getLogger(__name__)


class DictService:
    """
    Dictionary service for handling text segments and dictionary operations.
    
    Provides high-level business logic for:
    - Text segment retrieval by anchor
    - Dictionary term lookups
    - Content indexing and management
    """
    
    def __init__(self):
        """Initialize service with repositories."""
        self.dict_repo = DictRepository()
        self.file_repo = FileSystemRepository()
        self.data_dir = os.path.join(os.path.dirname(__file__), "../../../../data")
        self._characters_data = None
        self._glossary_data = None
    
    async def fetch_segment(self, anchor: str) -> SegmentResponse:
        """
        Fetch text segment by anchor identifier.
        
        Args:
            anchor: Anchor identifier (e.g., "A01", "B02_03")
            
        Returns:
            SegmentResponse with text content and metadata
            
        Raises:
            ValueError: If anchor not found
        """
        logger.info(f"Fetching segment for anchor: {anchor}")
        
        # Get anchor metadata
        anchor_info = await self.dict_repo.get_anchor_info(anchor)
        if not anchor_info:
            raise ValueError(f"Anchor not found: {anchor}")
        
        # Get text content
        text_content = await self.file_repo.get_text_by_anchor(anchor)
        if not text_content:
            raise ValueError(f"No text content found for anchor: {anchor}")
        
        return SegmentResponse(
            anchor=anchor,
            text=text_content["text"],
            start_offset=text_content["start_offset"],
            end_offset=text_content["end_offset"],
            chapter=anchor_info.get("chapter"),
            metadata={
                "source_file": text_content.get("source_file"),
                "language": text_content.get("language", "zh"),
                "character_count": len(text_content["text"]),
                "retrieved_at": datetime.now().isoformat()
            }
        )
    
    async def lookup_terms(
        self, 
        terms: List[str], 
        language: Optional[str] = "zh"
    ) -> List[DictLookupResponse]:
        """
        Look up terms in dictionary.
        
        Args:
            terms: List of terms to look up
            language: Target language code
            
        Returns:
            List of dictionary lookup responses
        """
        logger.info(f"Looking up {len(terms)} terms in language: {language}")
        
        results = []
        for term in terms:
            try:
                dict_entry = await self.dict_repo.lookup_term(term, language)
                if dict_entry:
                    results.append(DictLookupResponse(
                        term=term,
                        definitions=dict_entry.get("definitions", []),
                        pronunciation=dict_entry.get("pronunciation"),
                        part_of_speech=dict_entry.get("part_of_speech"),
                        examples=dict_entry.get("examples", [])
                    ))
                else:
                    # Return empty result for not found terms
                    results.append(DictLookupResponse(
                        term=term,
                        definitions=[f"定义未找到: {term}"],
                        pronunciation=None,
                        part_of_speech=None,
                        examples=[]
                    ))
            except Exception as e:
                logger.error(f"Error looking up term '{term}': {e}")
                results.append(DictLookupResponse(
                    term=term,
                    definitions=[f"查询错误: {term}"],
                    pronunciation=None,
                    part_of_speech=None,
                    examples=[]
                ))
        
        return results
    
    async def list_anchors(self, chapter: Optional[str] = None) -> List[str]:
        """
        Get list of available anchors.
        
        Args:
            chapter: Optional chapter filter
            
        Returns:
            List of anchor identifiers
        """
        logger.info(f"Listing anchors for chapter: {chapter or 'all'}")
        
        return await self.dict_repo.list_anchors(chapter)
    
    async def index_content(self, source_path: str) -> dict:
        """
        Index new content and create anchors.
        
        Args:
            source_path: Path to content file
            
        Returns:
            Indexing result summary
        """
        logger.info(f"Indexing content from: {source_path}")
        
        # This would implement content indexing logic
        # For now, return a placeholder
        return {
            "indexed_files": 1,
            "created_anchors": 0,
            "processed_at": datetime.now().isoformat()
        }
    
    async def _load_characters_data(self) -> dict:
        """Load characters data from JSON file."""
        if self._characters_data is None:
            characters_path = os.path.join(self.data_dir, "characters_data.json")
            try:
                with open(characters_path, 'r', encoding='utf-8') as f:
                    self._characters_data = json.load(f)
            except FileNotFoundError:
                logger.error(f"Characters data file not found: {characters_path}")
                self._characters_data = {"characters": []}
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing characters data: {e}")
                self._characters_data = {"characters": []}
        return self._characters_data
    
    async def _load_glossary_data(self) -> dict:
        """Load glossary data from JSON file."""
        if self._glossary_data is None:
            glossary_path = os.path.join(self.data_dir, "glossary_data.json")
            try:
                with open(glossary_path, 'r', encoding='utf-8') as f:
                    self._glossary_data = json.load(f)
            except FileNotFoundError:
                logger.warning(f"Glossary data file not found: {glossary_path}")
                self._glossary_data = {"terms": []}
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing glossary data: {e}")
                self._glossary_data = {"terms": []}
        return self._glossary_data
    
    async def query_character(self, character_id: str) -> Optional[CharacterResponse]:
        """
        Query character data by ID.
        
        Args:
            character_id: Character ID to query
            
        Returns:
            CharacterResponse if found, None otherwise
        """
        logger.info(f"Querying character: {character_id}")
        
        characters_data = await self._load_characters_data()
        
        # Find character by ID
        for character in characters_data.get("characters", []):
            if character.get("id") == character_id:
                return CharacterResponse(
                    id=character.get("id", ""),
                    name=character.get("name", ""),
                    aliases=character.get("aliases", []),
                    race=character.get("race"),
                    gender=character.get("gender"),
                    debut_chapter=character.get("debut_chapter"),
                    appearance_chapters=character.get("appearance_chapters", []),
                    abilities=character.get("abilities", []),
                    description=character.get("description"),
                    relationships=character.get("relationships", {}),
                    is_protagonist=character.get("is_protagonist", False),
                    created_at=character.get("created_at"),
                    updated_at=character.get("updated_at")
                )
        
        return None
    
    async def query_glossary(self, term_id: str) -> Optional[GlossaryResponse]:
        """
        Query glossary data by ID.
        
        Args:
            term_id: Glossary term ID to query
            
        Returns:
            GlossaryResponse if found, None otherwise
        """
        logger.info(f"Querying glossary term: {term_id}")
        
        glossary_data = await self._load_glossary_data()
        
        # Find term by ID
        for term in glossary_data.get("terms", []):
            if term.get("id") == term_id:
                return GlossaryResponse(
                    id=term.get("id", ""),
                    term=term.get("term", ""),
                    definition=term.get("definition", ""),
                    category=term.get("category"),
                    related_terms=term.get("related_terms", [])
                )
        
        # For now, return None since glossary_data.json doesn't exist yet
        return None
    
    async def list_characters(self) -> List[str]:
        """
        Get list of all character IDs.
        
        Returns:
            List of character identifiers
        """
        logger.info("Listing all characters")
        
        characters_data = await self._load_characters_data()
        return [char.get("id", "") for char in characters_data.get("characters", []) if char.get("id")]
    
    async def list_glossary(self) -> List[str]:
        """
        Get list of all glossary term IDs.
        
        Returns:
            List of glossary term identifiers
        """
        logger.info("Listing all glossary terms")
        
        glossary_data = await self._load_glossary_data()
        return [term.get("id", "") for term in glossary_data.get("terms", []) if term.get("id")]
    
    async def batch_query_characters(self, character_ids: List[str], include_relationships: bool = True) -> dict:
        """
        Query multiple characters by their IDs in a single request.
        
        Args:
            character_ids: List of character IDs to query
            include_relationships: Whether to include relationship information
            
        Returns:
            Dictionary with characters data and list of not found IDs
        """
        logger.info(f"Batch querying {len(character_ids)} characters")
        
        characters_data = await self._load_characters_data()
        
        # Create a lookup dict for faster access
        all_characters = {char.get("id"): char for char in characters_data.get("characters", []) if char.get("id")}
        
        result_characters = {}
        not_found = []
        
        for char_id in character_ids:
            if char_id in all_characters:
                character = all_characters[char_id]
                char_response = CharacterResponse(
                    id=character.get("id", ""),
                    name=character.get("name", ""),
                    aliases=character.get("aliases", []),
                    race=character.get("race"),
                    gender=character.get("gender"),
                    debut_chapter=character.get("debut_chapter"),
                    appearance_chapters=character.get("appearance_chapters", []),
                    abilities=character.get("abilities", []),
                    description=character.get("description"),
                    relationships=character.get("relationships", {}) if include_relationships else {},
                    is_protagonist=character.get("is_protagonist", False),
                    created_at=character.get("created_at"),
                    updated_at=character.get("updated_at")
                )
                result_characters[char_id] = char_response
            else:
                not_found.append(char_id)
        
        logger.info(f"Found {len(result_characters)} characters, {len(not_found)} not found")
        
        return {
            "characters": result_characters,
            "not_found": not_found
        } 