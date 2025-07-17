"""
Service layer for anchor service.

This module contains the core business logic for assembling text from anchor points.
The AnchorService class implements O(N) algorithm for processing anchors with 
cross-chapter handling and optional intro-patch functionality.
"""

from typing import List
from .models import Anchor, AssembleResponse, Span, ChunkResponse, AnchorContextResponse
from .repositories import AnchorRepository


class AnchorService:
    """
    Service class for anchor-based text assembly.
    
    Core algorithm:
    1. O(N) traversal of anchor points
    2. Cross-chapter handling with "Flush + Reset" 
    3. Optional intro-patch for first anchor
    """
    
    def __init__(self, repo: AnchorRepository):
        """
        Initialize service with repository dependency.
        
        Args:
            repo: AnchorRepository instance for data access
        """
        self.repo = repo

    def assemble_by_anchors(
        self, 
        anchors: List[Anchor], 
        *, 
        include_intro: bool = False
    ) -> AssembleResponse:
        """
        Assemble text from a list of anchor points.
        
        Algorithm:
        1. Initialize span with first anchor (with optional intro-patch)
        2. Traverse subsequent anchors
        3. On chapter change: flush current span and start new one
        4. Finalize last span
        
        Args:
            anchors: List of anchor points (must be non-empty)
            include_intro: Whether to include chapter introduction at beginning
            
        Returns:
            AssembleResponse with assembled text and spans for highlighting
            
        Raises:
            ValueError: If anchors list is empty
        """
        if not anchors:
            return AssembleResponse(text="", spans=[])

        parts: List[str] = []
        spans: List[Span] = []
        
        # ---- Initialize span with first anchor ----
        first = anchors[0]
        try:
            span_start = (
                self.repo.get_first_chunk_id(first.chapter_id)    # Chapter intro
                if include_intro else
                first.chunk_id                                    # Original start
            )
        except ValueError as e:
            # Handle case where chapter has no chunks
            raise ValueError(f"Failed to get first chunk for chapter {first.chapter_id}: {e}")
        
        prev = first

        # ---- Traverse subsequent anchors ----
        for curr in anchors[1:]:
            if curr.chapter_id != prev.chapter_id:                # Cross-chapter detected
                # Flush current span
                try:
                    texts = self.repo.get_chunks_in_range(
                        chapter_id=prev.chapter_id,
                        start_id=span_start,
                        end_id=prev.chunk_id
                    )
                    joined = "".join(texts)
                    parts.append(joined)
                    spans.append(Span(
                        chapter_id=prev.chapter_id,
                        start_id=span_start,
                        end_id=prev.chunk_id,
                        text=joined
                    ))
                except Exception as e:
                    # Log error but continue processing
                    print(f"Warning: Failed to get chunks for chapter {prev.chapter_id}, "
                          f"range {span_start}-{prev.chunk_id}: {e}")
                    
                # Reset for new chapter
                try:
                    span_start = (
                        self.repo.get_first_chunk_id(curr.chapter_id)
                        if include_intro else
                        curr.chunk_id
                    )
                except ValueError as e:
                    # If intro fails, fallback to current chunk
                    span_start = curr.chunk_id
                    print(f"Warning: Failed to get first chunk for chapter {curr.chapter_id}, "
                          f"using current chunk: {e}")
                    
            prev = curr

        # ---- Finalize last span ----
        try:
            texts = self.repo.get_chunks_in_range(
                chapter_id=prev.chapter_id,
                start_id=span_start,
                end_id=prev.chunk_id
            )
            joined = "".join(texts)
            parts.append(joined)
            spans.append(Span(
                chapter_id=prev.chapter_id,
                start_id=span_start,
                end_id=prev.chunk_id,
                text=joined
            ))
        except Exception as e:
            print(f"Warning: Failed to get chunks for final chapter {prev.chapter_id}, "
                  f"range {span_start}-{prev.chunk_id}: {e}")

        return AssembleResponse(
            text="\n\n".join(parts),  # Join spans with double newline
            spans=spans
        )

    def validate_anchors(self, anchors: List[Anchor]) -> List[str]:
        """
        Validate that all anchor chunks exist in the database.
        
        Args:
            anchors: List of anchor points to validate
            
        Returns:
            List of error messages for invalid anchors (empty if all valid)
        """
        errors = []
        
        for i, anchor in enumerate(anchors):
            if not self.repo.chunk_exists(anchor.chunk_id):
                errors.append(f"Anchor {i}: chunk_id '{anchor.chunk_id}' does not exist")
                
        return errors

    def get_assembly_stats(self, anchors: List[Anchor]) -> dict:
        """
        Get statistics about the assembly operation.
        
        Args:
            anchors: List of anchor points
            
        Returns:
            Dictionary with assembly statistics
        """
        if not anchors:
            return {
                "total_anchors": 0,
                "unique_chapters": 0,
                "estimated_spans": 0
            }
            
        unique_chapters = len(set(anchor.chapter_id for anchor in anchors))
        
        # Estimate number of spans (cross-chapter boundaries + 1)
        estimated_spans = 1
        prev_chapter = anchors[0].chapter_id
        for anchor in anchors[1:]:
            if anchor.chapter_id != prev_chapter:
                estimated_spans += 1
                prev_chapter = anchor.chapter_id
        
        return {
            "total_anchors": len(anchors),
            "unique_chapters": unique_chapters,
            "estimated_spans": estimated_spans,
            "chapter_sequence": [anchor.chapter_id for anchor in anchors]
        }

    def get_chunk(self, chunk_id: str) -> ChunkResponse:
        """
        Get a single chunk with metadata.
        
        Args:
            chunk_id: Chunk identifier (e.g., "ch1_5")
            
        Returns:
            ChunkResponse with chunk data and navigation info
            
        Raises:
            ValueError: If chunk not found
        """
        # Parse chapter and chunk number from chunk_id
        try:
            parts = chunk_id.split('_')
            if len(parts) != 2 or not parts[0].startswith('ch'):
                raise ValueError(f"Invalid chunk_id format: {chunk_id}")
            
            chapter_id = int(parts[0][2:])  # Remove 'ch' prefix
            chunk_num = int(parts[1])
        except (ValueError, IndexError):
            raise ValueError(f"Invalid chunk_id format: {chunk_id}")
        
        # Get chunk text
        text = self.repo.get_chunk_text(chunk_id)
        if not text:
            raise ValueError(f"Chunk not found: {chunk_id}")
        
        # Get chapter info
        chapter_chunk_count = self.repo.get_chapter_chunk_count(chapter_id)
        all_chapters = self.repo.get_all_chapters()
        
        # Determine if this is the last chunk in chapter
        is_last_in_chapter = chunk_num >= chapter_chunk_count
        
        # Determine if this is the last chunk overall
        is_last_overall = False
        if is_last_in_chapter:
            # Check if this is the last chapter
            max_chapter_id = max(ch['id'] for ch in all_chapters) if all_chapters else chapter_id
            is_last_overall = chapter_id >= max_chapter_id
        
        # Determine next chunk ID
        next_chunk_id = None
        if not is_last_overall:
            if is_last_in_chapter:
                # Move to next chapter
                next_chapter_id = chapter_id + 1
                next_chunk_id = f"ch{next_chapter_id}_1"
            else:
                # Next chunk in same chapter
                next_chunk_id = f"ch{chapter_id}_{chunk_num + 1}"
        
        return ChunkResponse(
            chunk_id=chunk_id,
            chapter_id=chapter_id,
            text=text,
            is_last_in_chapter=is_last_in_chapter,
            is_last_overall=is_last_overall,
            next_chunk_id=next_chunk_id
        )

    def get_next_chunk(self, current_chunk_id: str) -> ChunkResponse:
        """
        Get the next chunk in sequence.
        
        Args:
            current_chunk_id: Current chunk identifier
            
        Returns:
            ChunkResponse for the next chunk
            
        Raises:
            ValueError: If current chunk not found or no next chunk available
        """
        # First get current chunk to validate and get next chunk ID
        current_chunk = self.get_chunk(current_chunk_id)
        
        if current_chunk.is_last_overall:
            raise ValueError("No more chunks available - reached end of story")
        
        if not current_chunk.next_chunk_id:
            raise ValueError("Next chunk ID not available")
        
        # Get the next chunk
        return self.get_chunk(current_chunk.next_chunk_id)

    def get_first_chunk(self) -> ChunkResponse:
        """
        Get the first chunk of the story.
        
        Returns:
            ChunkResponse for the first chunk (ch1_1)
        """
        return self.get_chunk("ch1_1")

    def build_anchor_context(
        self, 
        current_anchor: Anchor, 
        previous_anchor: Anchor = None,
        include_tail: bool = False,
        is_last_anchor_in_chapter: bool = False
    ) -> AnchorContextResponse:
        """
        Build context for a specific anchor: 从章节开头或上一锚点到当前锚点的完整内容
        
        对于第一个锚点(如a1_1对应ch1_23)，应该包含ch1_1到ch1_23的所有内容
        对于后续锚点，应该包含上一锚点之后到当前锚点的所有内容
        
        Args:
            current_anchor: 当前锚点
            previous_anchor: 上一个锚点 (如果存在)
            include_tail: 是否包含锚点后的尾部内容
            is_last_anchor_in_chapter: 是否是本章最后一个锚点
            
        Returns:
            AnchorContextResponse with context and metadata
        """
        context_parts = []
        chunks_included = 0
        
        # 1. 确定起始位置
        if previous_anchor and previous_anchor.chapter_id == current_anchor.chapter_id:
            # 如果有上一个锚点，从上一锚点的下一个chunk开始
            prev_chunk_parts = previous_anchor.chunk_id.split('_')
            prev_chunk_num = int(prev_chunk_parts[1])
            start_chunk_id = f"ch{current_anchor.chapter_id}_{prev_chunk_num + 1}"
        else:
            # 如果是第一个锚点，从章节开头开始
            start_chunk_id = self.repo.get_first_chunk_id(current_anchor.chapter_id)
        
        # 2. 确定结束位置 (当前锚点)
        end_chunk_id = current_anchor.chunk_id
        
        # 3. 提取从起始位置到当前锚点的所有内容
        try:
            chunk_texts = self.repo.get_chunks_in_range(
                chapter_id=current_anchor.chapter_id,
                start_id=start_chunk_id,
                end_id=end_chunk_id
            )
            if chunk_texts:
                context_parts.extend(chunk_texts)
                chunks_included += len(chunk_texts)
        except Exception as e:
            print(f"Warning: Failed to get chunks from {start_chunk_id} to {end_chunk_id}: {e}")
            # 如果范围获取失败，至少尝试获取当前锚点的内容
            try:
                anchor_text = self.repo.get_chunk_text(current_anchor.chunk_id)
                if anchor_text:
                    context_parts.append(anchor_text)
                    chunks_included += 1
            except Exception as e2:
                print(f"Warning: Failed to get anchor text: {e2}")
        
        # 4. 视情况添加尾部内容
        has_tail = False
        if include_tail and is_last_anchor_in_chapter:
            curr_chunk_parts = current_anchor.chunk_id.split('_')
            curr_chunk_num = int(curr_chunk_parts[1])
            chapter_chunk_count = self.repo.get_chapter_chunk_count(current_anchor.chapter_id)
            
            if curr_chunk_num < chapter_chunk_count:
                # 添加锚点后到章节结尾的所有内容
                tail_start_id = f"ch{current_anchor.chapter_id}_{curr_chunk_num + 1}"
                tail_end_id = f"ch{current_anchor.chapter_id}_{chapter_chunk_count}"
                try:
                    tail_texts = self.repo.get_chunks_in_range(
                        chapter_id=current_anchor.chapter_id,
                        start_id=tail_start_id,
                        end_id=tail_end_id
                    )
                    if tail_texts:
                        context_parts.extend(tail_texts)
                        has_tail = True
                        chunks_included += len(tail_texts)
                except Exception as e:
                    print(f"Warning: Failed to get tail chunks: {e}")
        
        context_text = "".join(context_parts)
        
        return AnchorContextResponse(
            context=context_text,
            current_anchor=current_anchor,
            context_stats={
                "total_length": len(context_text),
                "has_prefix": True,  # 总是有前文内容
                "has_tail": has_tail,
                "chunks_included": chunks_included,
                "previous_anchor_provided": previous_anchor is not None,
                "include_tail_requested": include_tail,
                "is_last_anchor_in_chapter": is_last_anchor_in_chapter,
                "start_chunk_id": start_chunk_id,
                "end_chunk_id": end_chunk_id
            }
        )
