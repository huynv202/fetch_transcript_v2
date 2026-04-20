# YouTube Book Reader Pipeline - README

## 📖 Giới thiệu

Hệ thống tự động lấy transcript từ video YouTube (sách đọc), xử lý thành các đoạn văn có ngữ cảnh, và tạo bài đăng mạng xã hội tự nhiên như người thật chia sẻ.

## 🏗️ Kiến trúc hệ thống

```
YouTube Video → Subtitle Fetcher → Smart Segmenter → AI Generator → MySQL Database
```

### Các module chính:

1. **`config.py`** - Cấu hình database, API keys, và các tham số xử lý
2. **`database.py`** - Quản lý kết nối và thao tác MySQL
3. **`youtube_fetcher.py`** - Lấy transcript từ YouTube
4. **`text_segmenter.py`** - Chia văn bản thành đoạn có ý nghĩa với ngữ cảnh
5. **`ai_generator.py`** - Tạo bài đăng tự nhiên bằng AI (hoặc template khi không có API key)
6. **`main.py`** - Pipeline chính, điều phối toàn bộ quy trình

## 🚀 Cài đặt

### 1. Cài đặt dependencies:

```bash
pip install mysql-connector-python youtube-transcript-api requests
# Optional - nếu dùng OpenAI:
pip install openai
# Optional - nếu dùng Gemini:
pip install google-generativeai
# Optional - nếu dùng Claude:
pip install anthropic
```

### 2. Cấu hình database (`config.py`):

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'YOUR_PASSWORD',
    'database': 'treebook'
}
```

### 3. Cấu hình AI API (optional - `config.py`):

```python
AI_CONFIG = {
    'api_key': 'sk-...',  # Để trống nếu không dùng AI
    'model': 'gpt-4o-mini',
    'provider': 'openai'  # 'openai', 'gemini', 'claude', 'local'
}
```

## 📝 Sử dụng

### Chạy pipeline cho một video:

```bash
# Cơ bản
python main.py --video SYwXwiuxO-0

# Với language cụ thể
python main.py --video SYwXwiuxO-0 --language vi

# Không tạo posts (chỉ lưu paragraphs)
python main.py --video SYwXwiuxO-0 --no-generate-posts

# Giới hạn số posts tạo
python main.py --video SYwXwiuxO-0 --post-limit 5

# Bỏ qua nếu video đã tồn tại
python main.py --video SYwXwiuxO-0 --skip-if-exists
```

### Regenerate posts cho video đã tồn tại:

```bash
python main.py --regenerate --video-db-id 1 --post-limit 10
```

## 🔧 Xử lý vấn đề IP Block từ YouTube

Khi chạy từ cloud providers (AWS, GCP, Azure...), YouTube có thể block IP. Có 2 cách khắc phục:

### Cách 1: Dùng Cookies (Khuyến nghị)

1. Cài extension browser: **"Get cookies.txt LOCALLY"**
2. Truy cập youtube.com
3. Export cookies ra file `cookies.txt` trong thư mục project
4. Sửa `config.py`:
   ```python
   YOUTUBE_CONFIG = {
       'use_cookies': True,
       'cookies_file': 'cookies.txt'
   }
   ```

### Cách 2: Dùng Proxy

Cấu hình proxy environment variables trước khi chạy:
```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
python main.py --video ...
```

## 📊 Cấu trúc Database

### Bảng `youtube_videos`:
- Lưu thông tin video YouTube
- Fields: video_id, title, channel_title, description, thumbnail, publish_time, v.v.

### Bảng `youtube_paragraphs`:
- Lưu các đoạn văn bản đã được chia nhỏ
- Fields: ordinal_number, content_raw, content, youtube_video_id
- Mỗi paragraph có context_before và context_after để giữ ngữ cảnh

### Bảng `youtube_quotes`:
- Lưu các bài đăng đã tạo (từ AI hoặc template)
- Fields: ordinal_number, content, is_visible, youtube_video_id
- `is_visible`: Điều khiển hiển thị bài đăng

## 🎯 Quy trình xử lý

1. **Fetch Subtitles**: Lấy transcript từ YouTube (ưu tiên tiếng Việt)
2. **Smart Segmentation**: 
   - Chia transcript thành đoạn 50-500 ký tự
   - Score mỗi đoạn dựa trên: độ hoàn chỉnh, từ khóa quan trọng, ngữ cảnh
   - Giữ lại context trước/sau mỗi đoạn
3. **AI Content Generation**:
   - Tạo prompt với ngữ cảnh đầy đủ
   - Generate post tự nhiên như người thật chia sẻ
   - Nếu không có API key: dùng template có sẵn
4. **Database Storage**: Lưu vào MySQL

## ⚙️ Tùy chỉnh

### Điều chỉnh segmentation (`config.py`):

```python
PROCESSING_CONFIG = {
    'min_segment_length': 50,      # Độ dài tối thiểu mỗi đoạn
    'max_segment_length': 500,     # Độ dài tối đa mỗi đoạn
    'context_window': 3,           # Số câu context giữ lại
    'quote_selection_threshold': 0.7,  # Điểm threshold để chọn segment tốt
}
```

### Thêm AI Provider mới:

Sửa `ai_generator.py` trong method `_call_ai_api()`:
```python
elif self.provider == 'your_provider':
    # Implement your provider logic here
    pass
```

## 📈 Ví dụ Output

### Bài đăng mẫu (template mode):

```
Vừa đọc đến đoạn này trong Đắc Nhân Tâm mà thấy thấm quá!

"Hạnh phúc không phải là điểm đến, mà là hành trình. Chúng ta thường mải mê chạy theo mục tiêu mà quên mất tận hưởng hiện tại."

Đúng là một chân lý sâu sắc! Đôi khi chúng ta cần chậm lại để thực sự cảm nhận cuộc sống. 📖✨

#sachhay #docbook #trichdanhay
```

## 🔐 Bảo mật

- **Không commit** file `cookies.txt` vào git
- **Không commit** API keys thật vào code
- Dùng `.env` file hoặc secrets manager cho production

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra kết nối MySQL: `mysql -u root -p`
2. Test YouTube fetch riêng: `python youtube_fetcher.py`
3. Test segmentation riêng: `python text_segmenter.py`
4. Test AI generator riêng: `python ai_generator.py`

## 📝 License

MIT License - Tự do sử dụng và chỉnh sửa
