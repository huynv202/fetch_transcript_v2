"""
Smart Text Segmenter
Intelligently divides transcript text into meaningful segments with context
for creating natural social media posts about book excerpts
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

from config import PROCESSING_CONFIG


@dataclass
class TextSegment:
    """Represents a meaningful text segment with context"""
    content: str
    content_raw: str
    start_time: float
    end_time: float
    score: float = 0.0  # Quality/relevance score
    context_before: str = ""
    context_after: str = ""


class SmartTextSegmenter:
    def __init__(self):
        self.min_length = PROCESSING_CONFIG['min_segment_length']
        self.max_length = PROCESSING_CONFIG['max_segment_length']
        self.context_window = PROCESSING_CONFIG['context_window']
        
        # Vietnamese sentence endings
        self.sentence_endings = re.compile(r'[.!?…]|(?:\.\.\.)')
        
        # Patterns that indicate good quote material
        self.quote_indicators = [
            r'^[A-ZÀ-Ỹ]',  # Starts with capital letter
            r'(rằng|là|rằng:|:)',  # Contains "that" or colon (often introduces quotes)
            r'(nên|phải|cần|đừng|hãy)',  # Imperative/advice words
            r'(tôi nghĩ|tôi tin|theo tôi)',  # Personal opinion markers
            r'(điều quan trọng|đáng chú ý|thú vị là)',  # Importance markers
            r'(bởi vì|vì|do|nên)',  # Reasoning/connectors
            r'(nếu|khi|lúc|trong khi)',  # Conditional/temporal
            r'\d+',  # Contains numbers (statistics, examples)
        ]
        
        # Patterns to avoid (incomplete thoughts, interruptions)
        self.avoid_patterns = [
            r'^\s*$',  # Empty or whitespace only
            r'^[a-zà-ỹ]',  # Starts with lowercase (likely continuation)
            r'(\.\.\.|—)$',  # Ends with ellipsis or dash (incomplete)
            r'^(uh|um|à|ừ|ờ|dạ|vâng)\b',  # Filler words
        ]
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences, handling Vietnamese properly"""
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Split on sentence endings while keeping the punctuation
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '.!?…':
                # Check if this is really end of sentence
                if current.strip():
                    sentences.append(current.strip())
                    current = ""
        
        # Add remaining text
        if current.strip():
            sentences.append(current.strip())
        
        return sentences
    
    def create_segments_from_subtitles(self, subtitles: List[Dict]) -> List[TextSegment]:
        """
        Create meaningful segments from subtitle data
        
        Args:
            subtitles: List of dicts with 'text', 'start', 'duration'
        
        Returns:
            List of TextSegment objects
        """
        if not subtitles:
            return []
        
        # Combine subtitles into continuous text with timing info
        segments = []
        current_segment_texts = []
        current_start = subtitles[0]['start']
        current_end = subtitles[0]['start'] + subtitles[0]['duration']
        
        for i, sub in enumerate(subtitles):
            text = sub['text'].strip()
            if not text:
                continue
            
            start = sub['start']
            duration = sub['duration']
            end = start + duration
            
            # Check if we should start a new segment
            should_split = False
            
            # Check for natural break points
            if current_segment_texts:
                combined = ' '.join(current_segment_texts)
                
                # Too long - need to split
                if len(combined) > self.max_length:
                    should_split = True
                
                # Natural sentence boundary and reasonable length
                elif len(combined) >= self.min_length:
                    last_text = current_segment_texts[-1]
                    if self.sentence_endings.search(last_text):
                        should_split = True
            
            if should_split:
                # Create segment
                segment = self._create_segment(
                    current_segment_texts,
                    current_start,
                    current_end,
                    subtitles,
                    i
                )
                if segment:
                    segments.append(segment)
                
                # Reset for next segment
                current_segment_texts = [text]
                current_start = start
                current_end = end
            else:
                current_segment_texts.append(text)
                current_end = end
        
        # Don't forget the last segment
        if current_segment_texts:
            segment = self._create_segment(
                current_segment_texts,
                current_start,
                current_end,
                subtitles,
                len(subtitles)
            )
            if segment:
                segments.append(segment)
        
        # Score and rank segments
        self._score_segments(segments)
        
        return segments
    
    def _create_segment(self, texts: List[str], start: float, end: float,
                       all_subtitles: List[Dict], current_idx: int) -> TextSegment:
        """Create a TextSegment from collected texts"""
        if not texts:
            return None
        
        content_raw = ' '.join(texts)
        
        # Clean up the content
        content = self._clean_text(content_raw)
        
        if len(content) < self.min_length:
            return None
        
        # Get context windows
        context_before = self._get_context_before(all_subtitles, current_idx)
        context_after = self._get_context_after(all_subtitles, current_idx)
        
        return TextSegment(
            content=content,
            content_raw=content_raw,
            start_time=start,
            end_time=end,
            context_before=context_before,
            context_after=context_after
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Fix common issues
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Space before punctuation
        text = re.sub(r'([\"\'\(])\s+', r'\1', text)  # Space after opening quote/paren
        text = re.sub(r'\s+([\"\'\)])', r'\1', text)  # Space before closing quote/paren
        
        return text.strip()
    
    def _get_context_before(self, subtitles: List[Dict], idx: int) -> str:
        """Get context before current position"""
        context_parts = []
        count = 0
        
        for i in range(idx - 1, max(-1, idx - self.context_window - 5), -1):
            if count >= self.context_window:
                break
            
            text = subtitles[i]['text'].strip() if i < len(subtitles) else ""
            if text:
                context_parts.insert(0, text)
                count += 1
        
        return ' '.join(context_parts)
    
    def _get_context_after(self, subtitles: List[Dict], idx: int) -> str:
        """Get context after current position"""
        context_parts = []
        count = 0
        
        for i in range(idx, min(len(subtitles), idx + self.context_window + 5)):
            if count >= self.context_window:
                break
            
            text = subtitles[i]['text'].strip()
            if text:
                context_parts.append(text)
                count += 1
        
        return ' '.join(context_parts)
    
    def _score_segments(self, segments: List[TextSegment]):
        """Score segments based on quality indicators"""
        for segment in segments:
            score = 0.0
            
            # Length scoring (prefer medium-length segments)
            length = len(segment.content)
            if self.min_length <= length <= self.max_length:
                score += 0.3
            elif length > self.max_length * 1.5:
                score -= 0.2
            
            # Completeness scoring
            if self.sentence_endings.search(segment.content):
                score += 0.2
            
            # Quote indicator scoring
            for pattern in self.quote_indicators:
                if re.search(pattern, segment.content, re.IGNORECASE):
                    score += 0.1
            
            # Avoid incomplete thoughts
            for pattern in self.avoid_patterns:
                if re.search(pattern, segment.content, re.IGNORECASE):
                    score -= 0.15
            
            # Context availability bonus
            if segment.context_before and segment.context_after:
                score += 0.1
            
            segment.score = max(0.0, min(1.0, score))
    
    def get_best_segments(self, segments: List[TextSegment], 
                         threshold: float = None,
                         limit: int = None) -> List[TextSegment]:
        """
        Get best segments based on score threshold and limit
        
        Args:
            segments: List of all segments
            threshold: Minimum score threshold (default from config)
            limit: Maximum number of segments to return
        
        Returns:
            Filtered and sorted list of segments
        """
        if threshold is None:
            threshold = PROCESSING_CONFIG['quote_selection_threshold']
        
        # Filter by threshold
        filtered = [s for s in segments if s.score >= threshold]
        
        # Sort by score descending
        filtered.sort(key=lambda x: x.score, reverse=True)
        
        # Apply limit if specified
        if limit:
            filtered = filtered[:limit]
        
        return filtered
    
    def merge_adjacent_segments(self, segments: List[TextSegment], 
                                max_length: int = None) -> List[TextSegment]:
        """Merge adjacent segments that are too short"""
        if max_length is None:
            max_length = self.max_length
        
        if len(segments) <= 1:
            return segments
        
        merged = []
        current = segments[0]
        
        for next_seg in segments[1:]:
            combined_length = len(current.content) + len(next_seg.content) + 1
            
            if combined_length <= max_length:
                # Merge
                current = TextSegment(
                    content=f"{current.content} {next_seg.content}",
                    content_raw=f"{current.content_raw} {next_seg.content_raw}",
                    start_time=current.start_time,
                    end_time=next_seg.end_time,
                    score=(current.score + next_seg.score) / 2,
                    context_before=current.context_before,
                    context_after=next_seg.context_after
                )
            else:
                # Keep separate
                merged.append(current)
                current = next_seg
        
        merged.append(current)
        return merged
    
    def export_for_display(self, segments: List[TextSegment]) -> List[Dict]:
        """Export segments in format suitable for database storage"""
        return [
            {
                'content': seg.content,
                'content_raw': seg.content_raw,
                'start_time': seg.start_time,
                'end_time': seg.end_time,
                'score': seg.score,
                'context_before': seg.context_before,
                'context_after': seg.context_after
            }
            for seg in segments
        ]


# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_subtitles = [
        {'text': 'Xin chào các bạn, hôm nay chúng ta sẽ cùng nhau đọc một cuốn sách rất hay.', 'start': 0.0, 'duration': 4.0},
        {'text': 'Cuốn sách này nói về cách tư duy tích cực trong cuộc sống.', 'start': 4.5, 'duration': 3.5},
        {'text': 'Tác giả đã chia sẻ rằng: \"Hạnh phúc không phải là điểm đến, mà là hành trình.\"', 'start': 8.5, 'duration': 5.0},
        {'text': 'Điều này thật sự có ý nghĩa với tôi.', 'start': 14.0, 'duration': 2.5},
        {'text': 'Chúng ta thường mải mê chạy theo mục tiêu mà quên mất tận hưởng hiện tại.', 'start': 17.0, 'duration': 4.5},
        {'text': 'Hãy nhớ rằng mỗi ngày đều là một món quà quý giá.', 'start': 22.0, 'duration': 3.5},
    ]
    
    print("=" * 60)
    print("Testing Smart Text Segmenter")
    print("=" * 60)
    
    segmenter = SmartTextSegmenter()
    segments = segmenter.create_segments_from_subtitles(sample_subtitles)
    
    print(f"\nCreated {len(segments)} segments:")
    for i, seg in enumerate(segments, 1):
        print(f"\n--- Segment {i} (Score: {seg.score:.2f}) ---")
        print(f"Content: {seg.content}")
        if seg.context_before:
            print(f"Context before: ...{seg.context_before[-50:]}")
        if seg.context_after:
            print(f"Context after: {seg.context_after[:50]}...")
    
    # Get best segments
    best = segmenter.get_best_segments(segments, threshold=0.3)
    print(f"\n\nBest segments (threshold >= 0.3): {len(best)}")
    for i, seg in enumerate(best, 1):
        print(f"  {i}. [Score: {seg.score:.2f}] {seg.content[:60]}...")
