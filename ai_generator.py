"""
AI Content Generator for Social Media Posts
Creates natural, engaging posts from book excerpts with context
Supports multiple AI providers (OpenAI, Gemini, Claude, Local)
"""

from typing import List, Dict, Optional
import json
import time

from config import AI_CONFIG


class AIContentGenerator:
    def __init__(self, api_key: str = None, provider: str = None, model: str = None):
        self.api_key = api_key or AI_CONFIG['api_key']
        self.provider = provider or AI_CONFIG['provider']
        self.model = model or AI_CONFIG['model']
        
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate AI client based on provider"""
        if not self.api_key:
            print("⚠ Warning: No API key provided. AI generation will use mock mode.")
            return
        
        if self.provider == 'openai':
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
                print(f"✓ Initialized OpenAI client with model: {self.model}")
            except ImportError:
                print("⚠ OpenAI library not installed. Run: pip install openai")
            except Exception as e:
                print(f"⚠ Error initializing OpenAI: {e}")
        
        elif self.provider == 'gemini':
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
                print(f"✓ Initialized Gemini client with model: {self.model}")
            except ImportError:
                print("⚠ Google generativeai library not installed. Run: pip install google-generativeai")
            except Exception as e:
                print(f"⚠ Error initializing Gemini: {e}")
        
        elif self.provider == 'claude':
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
                print(f"✓ Initialized Claude client with model: {self.model}")
            except ImportError:
                print("⚠ Anthropic library not installed. Run: pip install anthropic")
            except Exception as e:
                print(f"⚠ Error initializing Claude: {e}")
        
        elif self.provider == 'local':
            print(f"✓ Using local model mode: {self.model}")
        
        else:
            print(f"⚠ Unknown provider: {self.provider}. Using mock mode.")
    
    def generate_post(self, segment: Dict, video_info: Dict = None) -> Dict:
        """
        Generate a natural social media post from a text segment
        
        Args:
            segment: Dict with 'content', 'context_before', 'context_after'
            video_info: Optional dict with video metadata (title, channel, etc.)
        
        Returns:
            Dict with generated post content and metadata
        """
        content = segment.content if hasattr(segment, 'content') else segment.get('content', '')
        context_before = segment.context_before if hasattr(segment, 'context_before') else segment.get('context_before', '')
        context_after = segment.context_after if hasattr(segment, 'context_after') else segment.get('context_after', '')
        score = segment.score if hasattr(segment, 'score') else segment.get('score', 0.0)
        
        # Build the prompt
        prompt = self._build_prompt(content, context_before, context_after, video_info)
        
        # Generate response
        if self.api_key and self._client:
            try:
                generated_text = self._call_ai_api(prompt)
            except Exception as e:
                print(f"⚠ AI API call failed: {e}. Falling back to template mode.")
                generated_text = self._generate_template_post(content, context_before, video_info)
        else:
            # Mock/template mode when no API key
            generated_text = self._generate_template_post(content, context_before, video_info)
        
        return {
            'content': generated_text,
            'original_excerpt': content,
            'context_before': context_before,
            'context_after': context_after,
            'score': score,
            'is_visible': True,
            'generation_method': 'ai' if self.api_key else 'template'
        }
    
    def _build_prompt(self, content: str, context_before: str, 
                     context_after: str, video_info: Dict = None) -> str:
        """Build the AI prompt for generating a natural post"""
        
        video_context = ""
        if video_info:
            video_context = f"""
- Video: "{video_info.get('title', 'Unknown')}"
- Channel: {video_info.get('channel_title', 'Unknown')}
"""
        
        prompt = f"""Bạn là một người yêu sách và muốn chia sẻ những đoạn trích hay từ video đọc sách lên mạng xã hội.

Thông tin video:{video_context}

Đoạn trích từ sách:
"{content}"

Ngữ cảnh trước đó: {context_before if context_before else "(Không có)"}
Ngữ cảnh sau đó: {context_after if context_after else "(Không có)"}

Yêu cầu:
1. Viết một bài đăng ngắn (2-4 câu) tự nhiên như đang chia sẻ cảm xúc cá nhân
2. Bắt đầu bằng cách giới thiệu ngữ cảnh hoặc cảm xúc của bạn về đoạn sách
3. Trích dẫn đoạn sách hay nhất (dùng dấu ngoặc kép)
4. Kết thúc bằng suy nghĩ/cảm nhận cá nhân hoặc câu hỏi gợi mở
5. Giọng văn chân thật, gần gũi, không quá trang trọng
6. Thêm 2-3 hashtag phù hợp (#sachhay, #docbook, v.v.)

Ví dụ phong cách:
"Vừa đọc đến đoạn này trong cuốn [tên sách] mà thấy thấm quá! '[đoạn trích]' - Đúng là chúng ta thường mải chạy theo tương lai mà quên mất hiện tại mới là món quà quý giá nhất. Các bạn có đồng ý không?"

Bài đăng của bạn:"""
        
        return prompt
    
    def _call_ai_api(self, prompt: str) -> str:
        """Call the appropriate AI API based on provider"""
        
        if self.provider == 'openai':
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Bạn là một người yêu sách, viết bài chia sẻ tự nhiên, chân thật trên mạng xã hội."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.8,
                top_p=0.9
            )
            return response.choices[0].message.content.strip()
        
        elif self.provider == 'gemini':
            response = self._client.generate_content(prompt)
            return response.text.strip()
        
        elif self.provider == 'claude':
            response = self._client.messages.create(
                model=self.model,
                max_tokens=300,
                system="Bạn là một người yêu sách, viết bài chia sẻ tự nhiên, chân thật trên mạng xã hội.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        
        elif self.provider == 'local':
            # Placeholder for local model integration (Ollama, LM Studio, etc.)
            return self._call_local_model(prompt)
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _call_local_model(self, prompt: str) -> str:
        """Call a local model (placeholder for Ollama, LM Studio, etc.)"""
        # This can be extended based on your local setup
        # Example for Ollama:
        # import requests
        # response = requests.post('http://localhost:11434/api/generate', 
        #                         json={'model': self.model, 'prompt': prompt})
        # return response.json()['response']
        
        return self._generate_template_post_from_prompt(prompt)
    
    def _generate_template_post(self, content: str, context_before: str, 
                                video_info: Dict = None) -> str:
        """Generate a post using templates when AI is not available"""
        
        # Extract a good quote from content
        quote = content[:150] + "..." if len(content) > 150 else content
        
        # Get book/video title if available
        book_title = "cuốn sách này"
        if video_info and video_info.get('title'):
            # Try to extract book title from video title
            title = video_info['title']
            if '"' in title:
                book_title = title.split('"')[1][:50]
            else:
                book_title = title[:50]
        
        # Template patterns
        templates = [
            f"""Vừa đọc đến đoạn này trong {book_title} mà thấy thấm quá! 

"{quote}"

Đúng là một chân lý sâu sắc! Đôi khi chúng ta cần chậm lại để thực sự cảm nhận cuộc sống. 📖✨

#sachhay #docbook #trichdanhay""",
            
            f"""Hôm nay tình cờ nghe được đoạn này từ {book_title}, phải ghi lại ngay!

"{quote}"

Bạn nghĩ sao về điều này? Cá nhân mình thấy rất đáng suy ngẫm... 💭

#sach #reading #bookquotes""",
            
            f"""Một đoạn trích hay từ {book_title} muốn chia sẻ với mọi người:

"{quote}"

Đọc xong mà thấy lòng nhẹ nhõm hẳn. Có những điều giản đơn vậy mà ta mãi đi tìm ở đâu xa... 🌿

#sachvanhoc #docmoingay #inspiration"""
        ]
        
        # Select template based on content characteristics
        if any(word in content.lower() for word in ['hạnh phúc', 'vui vẻ', 'yêu thương']):
            return templates[0]
        elif any(word in content.lower() for word in ['suy nghĩ', 'nghĩ về', 'câu hỏi']):
            return templates[1]
        else:
            return templates[2]
    
    def _generate_template_post_from_prompt(self, prompt: str) -> str:
        """Fallback template generator"""
        return self._generate_template_post(prompt, "")
    
    def generate_multiple_posts(self, segments: List[Dict], 
                               video_info: Dict = None,
                               limit: int = None) -> List[Dict]:
        """
        Generate posts for multiple segments
        
        Args:
            segments: List of segment dicts
            video_info: Video metadata
            limit: Maximum number of posts to generate
        
        Returns:
            List of generated post dicts
        """
        if limit:
            segments = segments[:limit]
        
        posts = []
        total = len(segments)
        
        for i, segment in enumerate(segments, 1):
            print(f"Generating post {i}/{total}...")
            
            try:
                post = self.generate_post(segment, video_info)
                posts.append(post)
                
                # Rate limiting
                if self.api_key and i < total:
                    time.sleep(0.5)
            
            except Exception as e:
                print(f"⚠ Error generating post {i}: {e}")
                continue
        
        return posts


# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_segment = {
        'content': 'Hạnh phúc không phải là điểm đến, mà là hành trình. Chúng ta thường mải mê chạy theo mục tiêu mà quên mất tận hưởng hiện tại.',
        'context_before': 'Tác giả đã chia sẻ rằng cuộc sống hiện đại khiến chúng ta luôn vội vã.',
        'context_after': 'Hãy nhớ rằng mỗi ngày đều là một món quà quý giá.',
        'score': 0.85
    }
    
    sample_video = {
        'title': 'Đắc Nhân Tâm - Nghệ Thuật Ứng Xử Trong Cuộc Sống',
        'channel_title': 'Sách Nói Online'
    }
    
    print("=" * 60)
    print("Testing AI Content Generator")
    print("=" * 60)
    
    generator = AIContentGenerator()  # Will use mock mode without API key
    
    post = generator.generate_post(sample_segment, sample_video)
    
    print("\nGenerated Post:")
    print("-" * 40)
    print(post['content'])
    print("-" * 40)
    print(f"\nMethod: {post['generation_method']}")
    print(f"Original excerpt score: {post['score']}")
