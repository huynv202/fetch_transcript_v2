"""
Quote Extractor - Uses AI to find the best quotes/excerpts from text segments
Analyzes paragraphs and extracts memorable, impactful sentences for social media sharing
"""

from typing import List, Dict, Optional
import json
import re

from config import AI_CONFIG


class QuoteExtractor:
    """Extract meaningful quotes from text segments using AI"""
    
    def __init__(self, api_key: str = None, provider: str = None, model: str = None):
        self.api_key = api_key or AI_CONFIG['api_key']
        self.provider = provider or AI_CONFIG['provider']
        self.model = model or AI_CONFIG['model']
        
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate AI client based on provider"""
        if not self.api_key:
            print("⚠ Warning: No API key provided. Quote extraction will use rule-based mode.")
            return
        
        if self.provider == 'openai':
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                print(f"✓ Initialized OpenAI client for quote extraction: {self.model}")
            except ImportError:
                print("⚠ OpenAI library not installed. Run: pip install openai")
            except Exception as e:
                print(f"⚠ Error initializing OpenAI: {e}")
        
        elif self.provider == 'gemini':
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
                print(f"✓ Initialized Gemini client for quote extraction: {self.model}")
            except ImportError:
                print("⚠ Google generativeai library not installed. Run: pip install google-generativeai")
            except Exception as e:
                print(f"⚠ Error initializing Gemini: {e}")
        
        elif self.provider == 'claude':
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
                print(f"✓ Initialized Claude client for quote extraction: {self.model}")
            except ImportError:
                print("⚠ Anthropic library not installed. Run: pip install anthropic")
            except Exception as e:
                print(f"⚠ Error initializing Claude: {e}")
        
        elif self.provider == 'local':
            print(f"✓ Using local model mode for quote extraction: {self.model}")
        
        else:
            print(f"⚠ Unknown provider: {self.provider}. Using rule-based mode.")
    
    def extract_quotes_from_paragraph(self, paragraph: Dict, 
                                       num_quotes: int = 1,
                                       video_info: Dict = None) -> List[Dict]:
        """
        Extract best quotes from a single paragraph
        
        Args:
            paragraph: Dict with 'content', 'content_raw', etc.
            num_quotes: Number of quotes to extract
            video_info: Optional video metadata for context
        
        Returns:
            List of extracted quote dicts
        """
        content = paragraph.get('content', '') or paragraph.get('content_raw', '')
        
        if not content or len(content.strip()) < 20:
            return []
        
        # Use AI if available, otherwise use rule-based extraction
        if self.api_key and self._client:
            try:
                quotes = self._extract_quotes_with_ai(content, num_quotes, video_info)
                return quotes
            except Exception as e:
                print(f"⚠ AI quote extraction failed: {e}. Falling back to rule-based.")
                return self._extract_quotes_rule_based(content, num_quotes)
        else:
            return self._extract_quotes_rule_based(content, num_quotes)
    
    def extract_quotes_from_paragraphs(self, paragraphs: List[Dict],
                                        video_info: Dict = None,
                                        max_quotes_total: int = 10) -> List[Dict]:
        """
        Extract quotes from multiple paragraphs
        
        Args:
            paragraphs: List of paragraph dicts
            video_info: Video metadata
            max_quotes_total: Maximum total quotes to return
        
        Returns:
            List of all extracted quotes
        """
        all_quotes = []
        total = len(paragraphs)
        
        for i, para in enumerate(paragraphs, 1):
            print(f"Extracting quotes from paragraph {i}/{total}...", end=" ")
            
            # Determine how many quotes to extract from this paragraph
            remaining_quotes = max_quotes_total - len(all_quotes)
            if remaining_quotes <= 0:
                break
            
            num_quotes_from_para = min(1, remaining_quotes)  # Default 1 quote per paragraph
            
            quotes = self.extract_quotes_from_paragraph(para, num_quotes_from_para, video_info)
            
            if quotes:
                all_quotes.extend(quotes)
                print(f"✓ Found {len(quotes)} quote(s)")
            else:
                print("✗ No quotes found")
        
        return all_quotes
    
    def _extract_quotes_with_ai(self, content: str, num_quotes: int, 
                                 video_info: Dict = None) -> List[Dict]:
        """Use AI to extract the best quotes from content"""
        
        # Build prompt
        prompt = self._build_quote_extraction_prompt(content, num_quotes, video_info)
        
        # Call AI API
        response_text = self._call_ai_api(prompt)
        
        # Parse response
        quotes = self._parse_ai_quote_response(response_text, content)
        
        return quotes
    
    def _build_quote_extraction_prompt(self, content: str, num_quotes: int,
                                        video_info: Dict = None) -> str:
        """Build AI prompt for quote extraction"""
        
        video_context = ""
        if video_info:
            video_context = f"- Video: \"{video_info.get('title', 'Unknown')}\" by {video_info.get('channel_title', 'Unknown')}\n"
        
        prompt = f"""Bạn là chuyên gia phân tích văn bản và cần trích xuất những câu nói hay, đáng nhớ từ đoạn văn sau.

{video_context}
Đoạn văn:
"{content}"

Yêu cầu:
1. Trích xuất {num_quotes} câu/trích dẫn hay nhất, đáng nhớ nhất từ đoạn văn trên
2. Ưu tiên những câu:
   - Có ý nghĩa sâu sắc, truyền cảm hứng
   - Chứa bài học, chân lý, quan điểm rõ ràng
   - Dễ hiểu và có thể đứng độc lập
   - Độ dài phù hợp (15-150 ký tự)
3. Trả kết quả dưới dạng JSON array với cấu trúc:
   [
     {{
       "quote": "nội dung trích dẫn",
       "reason": "lý do chọn (ngắn gọn)"
     }}
   ]

Chỉ trả về JSON, không thêm giải thích khác."""
        
        return prompt
    
    def _call_ai_api(self, prompt: str) -> str:
        """Call AI API based on provider"""
        
        if self.provider == 'openai':
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia trích xuất câu nói hay từ văn bản. Chỉ trả về JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
                top_p=0.9
            )
            return response.choices[0].message.content.strip()
        
        elif self.provider == 'gemini':
            response = self._client.generate_content(prompt)
            return response.text.strip()
        
        elif self.provider == 'claude':
            response = self._client.messages.create(
                model=self.model,
                max_tokens=500,
                system="Bạn là chuyên gia trích xuất câu nói hay từ văn bản. Chỉ trả về JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        
        elif self.provider == 'local':
            return self._call_local_model(prompt)
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _call_local_model(self, prompt: str) -> str:
        """Placeholder for local model integration"""
        # Can be extended for Ollama, LM Studio, etc.
        return self._extract_quotes_rule_based(prompt, 1)[0]['quote'] if self._extract_quotes_rule_based(prompt, 1) else ""
    
    def _parse_ai_quote_response(self, response_text: str, original_content: str) -> List[Dict]:
        """Parse AI response into structured quotes"""
        quotes = []
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                for item in parsed:
                    quote_text = item.get('quote', '').strip()
                    if quote_text and len(quote_text) >= 10:
                        quotes.append({
                            'content': quote_text,
                            'source_content': original_content,
                            'reason': item.get('reason', ''),
                            'is_visible': True,
                            'extraction_method': 'ai'
                        })
            else:
                # Fallback: try to extract quoted text
                quoted_texts = re.findall(r'[""]([^""\n]{10,200})[""]', response_text)
                for text in quoted_texts[:3]:
                    quotes.append({
                        'content': text.strip(),
                        'source_content': original_content,
                        'reason': 'Extracted from AI response',
                        'is_visible': True,
                        'extraction_method': 'ai'
                    })
        except json.JSONDecodeError:
            print("⚠ Could not parse AI response as JSON, using fallback")
            # Fallback to rule-based
            quotes = self._extract_quotes_rule_based(original_content, 1)
        except Exception as e:
            print(f"⚠ Error parsing AI response: {e}")
            quotes = self._extract_quotes_rule_based(original_content, 1)
        
        return quotes
    
    def _extract_quotes_rule_based(self, content: str, num_quotes: int) -> List[Dict]:
        """Extract quotes using rule-based heuristics when AI is not available"""
        quotes = []
        
        # Split into sentences
        sentences = self._split_into_sentences(content)
        
        # Score each sentence
        scored_sentences = []
        for sent in sentences:
            score = self._score_sentence(sent, content)
            if score > 0.3:  # Minimum threshold
                scored_sentences.append((sent, score))
        
        # Sort by score descending
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N quotes
        for sent, score in scored_sentences[:num_quotes]:
            quotes.append({
                'content': sent.strip(),
                'source_content': content,
                'reason': f'Rule-based selection (score: {score:.2f})',
                'is_visible': True,
                'extraction_method': 'rule_based'
            })
        
        return quotes
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (Vietnamese-aware)"""
        # Common Vietnamese sentence endings
        sentence_endings = re.compile(r'[.!?…]|(?:\\.\\.\\.)')
        
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in '.!?…':
                if current.strip():
                    sentences.append(current.strip())
                    current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        return sentences
    
    def _score_sentence(self, sentence: str, full_text: str) -> float:
        """Score a sentence based on quote-worthiness"""
        score = 0.0
        
        # Length scoring (prefer medium length)
        length = len(sentence)
        if 20 <= length <= 150:
            score += 0.3
        elif length > 150:
            score += 0.1
        elif length < 10:
            return 0.0  # Too short
        
        # Completeness - should have subject and predicate indicators
        if any(word in sentence.lower() for word in ['là', 'có', 'không', 'nên', 'phải']):
            score += 0.2
        
        # Impact words
        impact_words = ['quan trọng', 'đáng', 'tuyệt vời', 'sâu sắc', 'ý nghĩa', 
                       'hạnh phúc', 'thành công', 'thất bại', 'cuộc sống', 'yêu thương']
        if any(word in sentence.lower() for word in impact_words):
            score += 0.2
        
        # Quote indicators
        if '"' in sentence or "'" in sentence:
            score += 0.15
        
        # Avoid incomplete thoughts
        if sentence.endswith(('...', '—', '-')):
            score -= 0.2
        
        # Avoid questions (unless rhetorical)
        if sentence.endswith('?') and 'tại sao' not in sentence.lower() and 'như thế nào' not in sentence.lower():
            score -= 0.1
        
        return min(1.0, max(0.0, score))


# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_paragraph = {
        'content': 'Hạnh phúc không phải là điểm đến, mà là hành trình. Chúng ta thường mải mê chạy theo mục tiêu mà quên mất tận hưởng hiện tại. Điều quan trọng là biết trân trọng từng khoảnh khắc. Cuộc sống này quá ngắn ngủi để sống trong hối tiếc.',
        'content_raw': 'Hạnh phúc không phải là điểm đến, mà là hành trình. Chúng ta thường mải mê chạy theo mục tiêu mà quên mất tận hưởng hiện tại. Điều quan trọng là biết trân trọng từng khoảnh khắc. Cuộc sống này quá ngắn ngủi để sống trong hối tiếc.',
    }
    
    sample_video = {
        'title': 'Đắc Nhân Tâm - Nghệ Thuật Ứng Xử',
        'channel_title': 'Sách Nói Online'
    }
    
    print("=" * 60)
    print("Testing Quote Extractor")
    print("=" * 60)
    
    extractor = QuoteExtractor()  # Will use rule-based mode without API key
    
    quotes = extractor.extract_quotes_from_paragraph(sample_paragraph, num_quotes=2, video_info=sample_video)
    
    print(f"\nExtracted {len(quotes)} quote(s):\n")
    for i, quote in enumerate(quotes, 1):
        print(f"--- Quote {i} ---")
        print(f"Content: {quote['content']}")
        print(f"Reason: {quote['reason']}")
        print(f"Method: {quote['extraction_method']}")
        print()
