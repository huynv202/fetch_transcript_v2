# Hệ Thống Xử Lý Video Sách Đọc YouTube

## 🎯 Mục Đích
Hệ thống tự động lấy transcript/subtitle từ video YouTube (sách đọc), chia đoạn thông minh có ngữ cảnh, và tạo bài đăng mạng xã hội tự nhiên như người thật chia sẻ.

## ✅ Kết Quả Demo
Đã chạy thành công với video `SYwXwiuxO-0`:
- **19 segments** subtitle được tải về (demo mode)
- **17 paragraphs** được tạo và lưu vào DB
- **3 quotes/posts** AI đã tạo tự động

## 📦 Cài Đặt

### 1. Tạo môi trường ảo
```bash
cd /workspace
python3 -m venv venv
source venv/bin/activate
```

### 2. Cài đặt dependencies
```bash
pip install mysql-connector-python youtube-transcript-api requests
```

### 3. Cấu hình MySQL
Sửa file `config.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '0202',  # Đổi password của bạn
    'database': 'treebook'
}
USE_SQLITE = False  # Đổi sang True nếu muốn dùng SQLite cho testing
```

## 🚀 Sử Dụng

### Chạy pipeline cơ bản
```bash
# Dùng demo data (không cần kết nối YouTube)
python main.py --video SYwXwiuxO-0 --post-limit 5

# Fetch thật từ YouTube (có thể bị block IP)
python main.py --video SYwXwiuxO-0 --language vi
```

### Các tùy chọn
```bash
python main.py --help

# Ví dụ:
python main.py --video https://youtube.com/watch?v=SYwXwiuxO-0 --language vi
python main.py --video SYwXwiuxO-0 --no-generate-posts  # Chỉ lưu subtitle
python main.py --video SYwXwiuxO-0 --post-limit 10      # Tạo tối đa 10 posts
python main.py --regenerate --video-db-id 1             # Tạo lại posts cho video đã tồn tại
```

## 🔧 Xử Lý Vấn Đề

### YouTube Block IP
Nếu gặp lỗi "RequestBlocked" hoặc "IP has been blocked":

**Cách 1: Dùng Demo Mode** (đang mặc định trong code)
```python
# Trong main.py, dòng 61:
subtitles = self.fetcher.fetch_subtitles(video_url_or_id, language, use_demo_data=True)
```

**Cách 2: Dùng Cookies** (RỦI RO - có thể bị khóa tài khoản)
1. Cài extension "Get cookies.txt LOCALLY" trên Chrome/Firefox
2. Vào youtube.com, export cookies ra file `cookies.txt`
3. Sửa `config.py`:
```python
YOUTUBE_CONFIG = {
    'use_cookies': True,
    'cookies_file': 'cookies.txt',
    ...
}
```

**Cách 3: Dùng Proxy**
```bash
python main.py --video SYwXwiuxO-0 --proxy http://user:pass@proxy:port
```

**Cách 4: Chạy từ máy local** thay vì cloud server

## 📊 Cấu Trúc Database

### Bảng `youtube_videos`
- Lưu thông tin video: title, description, thumbnail, publish_time...

### Bảng `youtube_paragraphs`
- Lưu các đoạn văn bản đã được chia nhỏ
- Có ordinal_number để giữ thứ tự
- content_raw: text gốc, content: đã xử lý

### Bảng `youtube_quotes`
- Lưu các bài đăng AI tạo ra
- is_visible: flag để hiển thị/ẩn
- Content format: trích dẫn + cảm nhận cá nhân + hashtags

## 🤖 AI Content Generator

### Chế độ hoạt động
1. **API Mode**: Khi có API key (OpenAI, Gemini, Claude)
   - Sửa `config.py`: `AI_CONFIG['api_key'] = 'your-key'`
   
2. **Template Mode** (mặc định): Khi không có API key
   - Dùng template có sẵn, điền nội dung vào
   - Vẫn tạo ra bài đăng tự nhiên, có cảm xúc

### Template mẫu
```
Một đoạn trích hay từ {video_title} muốn chia sẻ với mọi người:

"{trích_dẫn_nổi_bật}"

Đọc xong mà thấy lòng nhẹ nhõm hẳn. Có những điều giản đơn vậy mà ta mãi đi tìm ở đâu xa... 🌿

#sachvanhoc #docmoingay #inspiration
```

## 📝 Quy Trình Xử Lý

```
1. Fetch Subtitles → 2. Lưu Video Info → 3. Chia Đoạn Thông Minh → 4. Tạo AI Posts → 5. Lưu DB
     ↓                      ↓                    ↓                        ↓
   YouTube               MySQL               Scoring                  Templates/API
```

### Bước 3: Smart Segmentation
- Gom các subtitle liên tiếp thành đoạn có nghĩa
- Score mỗi đoạn dựa trên: độ dài, từ khóa, cấu trúc câu
- Chọn đoạn có score cao nhất để tạo post
- Thêm context trước/sau để giữ ngữ cảnh

## 🎨 Tùy Chỉnh

### Điều chỉnh segmentation
File `config.py`:
```python
PROCESSING_CONFIG = {
    'min_segment_length': 50,      # Độ dài tối thiểu (ký tự)
    'max_segment_length': 500,     # Độ dài tối đa
    'context_window': 100,         # Số ký tự context thêm vào
    'score_threshold': 0.7,        # Điểm tối thiểu để chọn làm quote
    'max_posts_per_video': 10      # Số post tối đa mỗi video
}
```

### Thêm template mới
File `ai_generator.py`, method `_generate_template_post()`:
```python
templates = [
    {
        'intro': "Hôm nay đọc được đoạn này hay quá...",
        'outro': "Bạn nghĩ sao về câu nói này?",
        'hashtags': ['#sachvanhoc', '#trichdanhay']
    },
    # Thêm template khác ở đây
]
```

## 📈 Next Steps

1. **Thêm AI API thật**: OpenAI/Gemini/Claude để tạo content đa dạng hơn
2. **Cải thiện scoring**: Dùng NLP model để đánh giá chất lượng đoạn văn
3. **Auto posting**: Kết nối Facebook/TikTok API để tự động đăng bài
4. **Analytics**: Theo dõi engagement của từng post
5. **Multi-language**: Hỗ trợ nhiều ngôn ngữ hơn

## 🐛 Troubleshooting

### Lỗi: "No space left on device"
```bash
# Dọn dẹp cache
rm -rf /workspace/__pycache__
find . -name "*.pyc" -delete
```

### Lỗi: "json is not defined"
Đã fix: Thêm `import json` vào đầu file `database.py`

### Lỗi: "'TextSegment' object has no attribute 'get'"
Đã fix: Update `ai_generator.py` để handle cả object và dict

---

**Tác giả**: Generated by AI Assistant  
**Version**: 1.0  
**Last Updated**: 2024
