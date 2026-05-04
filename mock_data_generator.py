"""
Module tạo dữ liệu giả lập (mock) cho video dài (1+ giờ)
Dùng để test khi YouTube API bị chặn hoặc không lấy được sub thật.
"""

import random

def generate_long_mock_subtitles(video_id: str, duration_minutes: int = 60, language: str = "vi"):
    """
    Tạo danh sách phụ đề giả lập cho video dài.
    
    Args:
        video_id: ID của video YouTube
        duration_minutes: Thời lượng video (phút), mặc định 60 phút
        language: Ngôn ngữ giả lập
        
    Returns:
        List[dict]: Danh sách các đoạn phụ đề với cấu trúc:
            [{'text': str, 'start': float, 'duration': float}, ...]
    """
    
    # Các mẫu câu đa dạng để tạo nội dung dài và tự nhiên hơn
    sample_sentences = [
        "Xin chào các bạn, hôm nay chúng ta sẽ cùng nhau khám phá một chủ đề rất thú vị.",
        "Đây là một câu chuyện về lòng dũng cảm và sự kiên trì vượt qua mọi khó khăn.",
        "Nhân vật chính trong câu chuyện này đã phải đối mặt với nhiều thử thách khắc nghiệt.",
        "Bài học rút ra từ đây là không bao giờ được từ bỏ trước bất kỳ thất bại nào.",
        "Hãy cùng nhau đi sâu vào chi tiết để hiểu rõ hơn về vấn đề này nhé các bạn.",
        "Trong cuộc sống, chúng ta thường gặp phải những tình huống bất ngờ không lường trước được.",
        "Sự thành công không đến dễ dàng mà đòi hỏi sự nỗ lực không ngừng nghỉ mỗi ngày.",
        "Mỗi người đều có một con đường riêng để đi, quan trọng là không lạc lối giữa đường.",
        "Những kinh nghiệm quý báu này sẽ giúp ích rất nhiều cho hành trình sắp tới của bạn.",
        "Chúng ta cần phải biết lắng nghe và học hỏi từ những người đi trước mình.",
        "Thời gian là thứ quý giá nhất mà chúng ta không thể mua lại được bằng tiền bạc.",
        "Hãy trân trọng từng khoảnh khắc trong cuộc đời vì nó sẽ không bao giờ lặp lại.",
        "Sự thay đổi luôn đáng sợ nhưng cũng là cơ hội để chúng ta trưởng thành hơn.",
        "Đừng ngại mắc sai lầm vì đó chính là cách tốt nhất để chúng ta học hỏi và tiến bộ.",
        "Một tâm hồn đẹp sẽ tỏa sáng ngay cả trong những hoàn cảnh khó khăn nhất.",
        "Tình bạn chân chính là khi chúng ta ở bên nhau dù trong lúc vui hay buồn.",
        "Gia đình luôn là nơi bình yên nhất để chúng ta trở về sau những bão giông cuộc đời.",
        "Ước mơ sẽ chỉ là ước mơ nếu chúng ta không bắt tay vào hành động cụ thể.",
        "Niềm tin vào bản thân là chìa khóa quan trọng nhất để mở cánh cửa thành công.",
        "Hãy sống hết mình cho hiện tại vì tương lai là tổng hòa của những giây phút này.",
        "Sự tử tế nhỏ bé cũng có thể tạo nên những thay đổi lớn lao trong cuộc đời người khác.",
        "Học cách tha thứ không phải vì người khác mà chính là để giải thoát cho bản thân mình.",
        "Mỗi ngày mới là một cơ hội để chúng ta bắt đầu lại và làm những điều tốt đẹp hơn.",
        "Đừng so sánh bản thân với người khác vì mỗi người có một giá trị riêng biệt.",
        "Sự kiên nhẫn là đức tính quan trọng giúp chúng ta vượt qua mọi sóng gió cuộc đời.",
        "Hãy luôn giữ cho trái tim mình ấm áp và khối óc mình tỉnh táo trước mọi quyết định.",
        "Thành công thực sự không phải là đạt được bao nhiêu mà là giúp đỡ được bao nhiêu người.",
        "Cuộc sống này ngắn ngủi lắm, hãy dành thời gian cho những điều thực sự ý nghĩa.",
        "Nụ cười là ngôn ngữ chung của nhân loại, có thể xóa tan mọi khoảng cách giữa người với người.",
        "Đọc sách là cách tuyệt vời để mở rộng tầm nhìn và làm giàu kiến thức của bản thân.",
    ]
    
    subtitles = []
    current_time = 0.0
    
    # Tính toán số lượng segment cần thiết
    # Trung bình mỗi segment khoảng 3-5 giây, mỗi câu khoảng 4-8 giây
    total_segments = (duration_minutes * 60) // 4  # Khoảng 900 segments cho 1 giờ
    
    print(f"📝 Đang tạo {total_segments} đoạn phụ đề giả lập cho video {video_id} ({duration_minutes} phút)...")
    
    for i in range(total_segments):
        # Chọn ngẫu nhiên một câu từ danh sách mẫu
        # Có thể kết hợp 2 câu để tạo độ dài đa dạng
        if random.random() > 0.7 and i < total_segments - 1:
            text = sample_sentences[i % len(sample_sentences)] + " " + sample_sentences[(i + 1) % len(sample_sentences)]
            duration = random.uniform(5.0, 8.0)
        else:
            text = sample_sentences[i % len(sample_sentences)]
            duration = random.uniform(3.0, 5.0)
        
        subtitles.append({
            'text': text,
            'start': round(current_time, 2),
            'duration': round(duration, 2)
        })
        
        current_time += duration
    
    print(f"✅ Đã tạo xong {len(subtitles)} đoạn phụ đề.")
    print(f"⏱️  Tổng thời lượng giả lập: {current_time/60:.1f} phút ({current_time:.0f} giây)")
    
    # Tính tổng ký tự
    total_chars = sum(len(s['text']) for s in subtitles)
    print(f"📊 Tổng số ký tự: {total_chars:,}")
    
    return subtitles


def get_mock_subtitles_for_video(video_id: str):
    """
    Hàm tiện lợi để lấy phụ đề giả lập cho một video cụ thể.
    Có thể mở rộng để lưu cache nếu cần.
    """
    return generate_long_mock_subtitles(video_id, duration_minutes=65)


if __name__ == "__main__":
    # Test nhanh
    test_subs = get_mock_subtitles_for_video("TEST_VIDEO_ID")
    print("\n--- Mẫu 5 đoạn đầu tiên ---")
    for i, sub in enumerate(test_subs[:5]):
        print(f"[{i}] {sub['start']:.2f}s: {sub['text']}")
