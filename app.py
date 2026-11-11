import os
import json
import time
from datetime import datetime
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

# Tải biến môi trường từ file .env nếu có
load_dotenv()

# Kiểm tra thư viện streamlit-mic-recorder
try:
    from streamlit_mic_recorder import mic_recorder
except ImportError:
    st.error("Chưa cài đặt thư viện `streamlit-mic-recorder`. Vui lòng chạy: `pip install streamlit-mic-recorder`")
    mic_recorder = None

# Kiểm tra thư viện google-generativeai
try:
    import google.generativeai as genai
except ImportError:
    st.error("Chưa cài đặt thư viện `google-generativeai`. Vui lòng chạy: `pip install google-generativeai`")
    genai = None

# ==========================================
# CẤU HÌNH TRANG STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Korean Speaking AI Examiner (초급)",
    page_icon="🇰🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tùy biến CSS tăng tính thẩm mỹ và thân thiện
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .score-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 1px solid #BFDBFE;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .score-val {
        font-size: 2.3rem;
        font-weight: 800;
        color: #1D4ED8;
    }
    .score-lbl {
        font-size: 0.95rem;
        font-weight: 600;
        color: #374151;
        margin-top: 0.2rem;
    }
    .korean-box {
        background-color: #F8FAFC;
        border-left: 5px solid #3B82F6;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    .feedback-box {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 10px;
        padding: 1.2rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CÁC CHỦ ĐỀ LUYỆN NÓI TIẾNG HÀN SƠ CẤP (THEO GIÁO TRÌNH & TÌNH HUỐNG THỰC TẾ)
# ==========================================
TOPIC_DATA = {
    # --- CHỦ ĐỀ THEO GIÁO TRÌNH TIẾNG HÀN SƠ CẤP (초급 1) ---
    "👋 1. 인사와 소개 (Greetings & Introductions)": {
        "title": "인사와 소개 (Chào hỏi và Giới thiệu bản thân)",
        "scenario": "Bạn tham gia buổi gặp gỡ đầu tiên của lớp học tiếng Hàn hoặc câu lạc bộ giao lưu. Hãy tự tin chào hỏi lịch sự, giới thiệu họ tên, quốc tịch, nghề nghiệp/trường học và bày tỏ sự vui mừng khi được làm quen.",
        "guiding_questions": [
            "1. Chào hỏi và giới thiệu tên của bạn. (안녕하세요? 제 이름은 무엇입니까 / 뭐예요?)",
            "2. Bạn là người nước nào? (어느 나라 사람입니까?)",
            "3. Bạn là học sinh hay nhân viên công ty? (학생입니까, 회사원입니까?)",
            "4. Rất vui được gặp bạn! (만나서 반갑습니다. 잘 부탁드립니다.)"
        ],
        "target_grammar": [
            "N + 은/는 (trợ từ chủ đề)",
            "N + 입니다 / 입니까? (đuôi câu trang trọng)",
            "N + 이에요/예요 (đuôi câu thân mật)",
            "N + 이/가 아닙니다 (phủ định danh từ)"
        ],
        "target_vocabulary": [
            "안녕하세요 (xin chào)", "이름 (tên)", "베트남 (Việt Nam)", "한국 (Hàn Quốc)",
            "사람 (người)", "학생 (học sinh)", "선생님 (giáo viên)", "회사원 (nhân viên văn phòng)",
            "만나다 (gặp gỡ)", "반갑다 (vui mừng)"
        ]
    },
    "🏫 2. 학교 (School & Campus)": {
        "title": "학교 (Trường học & Cơ sở vật chất)",
        "scenario": "Một người bạn lần đầu đến thăm trường học của bạn. Hãy giới thiệu về trường: tên trường, các cơ sở vật chất (phòng học, thư viện, nhà ăn sinh viên), vị trí ở tầng mấy và nơi bạn thường học tập/đọc sách.",
        "guiding_questions": [
            "1. Đây là trường học của bạn phải không? Tên trường là gì? (여기가 당신의 학교입니까? 학교 이름이 뭐예요?)",
            "2. Trong trường có những phòng/khu vực nào? (학교에 교실, 도서관, 학생 식당이 있어요?)",
            "3. Thư viện và nhà ăn nằm ở đâu (tầng mấy)? (도서관/식당은 어디에 있어요? 몇 층에 있어요?)",
            "4. Bạn thường đọc sách hoặc học bài ở đâu? (어디에서 책을 읽고 공부해요?)"
        ],
        "target_grammar": [
            "여기 / 저기 / 거기 (đại từ chỉ vị trí)",
            "N + 이/가 있어요 / 없어요 (có / không có)",
            "N + 에 있어요 (chỉ vị trí tồn tại)",
            "N + 에서 (chỉ địa điểm diễn ra hành động)"
        ],
        "target_vocabulary": [
            "학교 (trường học)", "교실 (lớp học)", "도서관 (thư viện)", "학생 식당 (nhà ăn sinh viên)",
            "기숙사 (ký túc xá)", "화장실 (nhà vệ sinh)", "층 (tầng)", "1층/2층 (tầng 1/2)",
            "책 (sách)", "공부하다 (học bài)"
        ]
    },
    "🧑‍🤝‍🧑 3. 친구 (Friends & Personality)": {
        "title": "친구 (Bạn bè, Ngoại hình & Tính cách)",
        "scenario": "Hãy giới thiệu về người bạn thân nhất của bạn: bạn ấy tên là gì, là người nước nào, ngoại hình (cao, đẹp, dễ thương) và tính cách ra sao, hai bạn thường cùng nhau làm gì.",
        "guiding_questions": [
            "1. Người bạn thân nhất của bạn tên là gì? (제일 친한 친구 이름이 뭐예요?)",
            "2. Bạn ấy là người thế nào? Tính cách ra sao? (그 친구는 어떤 사람이에요? 성격이 어때요?)",
            "3. Ngoại hình của bạn ấy thế nào (cao, mắt to, đẹp trai/xinh gái)? (키가 커요? 멋있어요/예뻐요?)",
            "4. Hai bạn thường làm gì cùng nhau vào lúc rảnh rỗi? (주말이나 여가 시간에 친구와 무엇을 같이 해요?)"
        ],
        "target_grammar": [
            "N + 하고 / (이)랑 (và, cùng với)",
            "A/V + -아/어요 (đuôi câu thân mật lịch sự)",
            "A + -(으)ㄴ N (định từ tính từ bổ nghĩa cho danh từ: 착한 친구)",
            "같이 / 함께 (cùng nhau)"
        ],
        "target_vocabulary": [
            "친한 친구 (bạn thân)", "성격 (tính cách)", "착하다 (tốt bụng/hiền lành)",
            "친절하다 (thân thiện/chu đáo)", "재미있다 (thú vị)", "키가 크다/작다 (cao/thấp)",
            "멋있다 (ngầu/đẹp trai)", "예쁘다 (xinh xắn)", "이야기하다 (trò chuyện)"
        ]
    },
    "🏡 4. 고향 (Hometown & Nature)": {
        "title": "고향 (Quê hương & Nơi chốn)",
        "scenario": "Hãy giới thiệu về quê hương nơi bạn sinh ra hoặc thành phố bạn đang sống cho bạn bè người Hàn Quốc: vị trí ở đâu, thời tiết các mùa thế nào, cảnh đẹp hoặc điểm du lịch nổi tiếng và món đặc sản.",
        "guiding_questions": [
            "1. Quê hương của bạn ở đâu? Đó là thành phố lớn hay vùng quê thanh bình? (고향이 어디예요? 큰 도시예요, 시골이에요?)",
            "2. Thời tiết ở quê bạn vào mùa này thế nào? (요즘 고향 날씨가 어때요? 더워요, 추워요?)",
            "3. Quê bạn có địa điểm du lịch nào đẹp hoặc nổi tiếng không? (고향에 경치가 좋은 곳이나 유명한 곳이 있어요?)",
            "4. Món ăn nổi tiếng nhất ở quê bạn là món gì? (고향에서 무슨 음식이 제일 유명하고 맛있어요?)"
        ],
        "target_grammar": [
            "A/V + -지만 (nhưng / đối lập)",
            "N + (으)로 유명하다 (nổi tiếng về)",
            "A/V + -아/어서 좋아요 (vì... nên thích)",
            "N + 도 (cũng)"
        ],
        "target_vocabulary": [
            "고향 (quê hương)", "도시 (thành phố)", "시골 (nông thôn)", "경치 (phong cảnh)",
            "아름답다 (tươi đẹp)", "조용하다 (yên tĩnh)", "복잡하다 (đông đúc)",
            "날씨 (thời tiết)", "유명하다 (nổi tiếng)", "특산물 (đặc sản)"
        ]
    },
    "📚 5. 학교 생활 (School Life & Studies)": {
        "title": "학교 생활 (Đời sống học đường & Lớp học)",
        "scenario": "Hãy kể về cuộc sống học tập thường ngày của bạn: bạn học tiếng Hàn vào thứ mấy, từ mấy giờ đến mấy giờ, bạn thích điều gì trong lớp học và sau giờ học bạn thường làm gì.",
        "guiding_questions": [
            "1. Bạn học tiếng Hàn vào những thứ mấy trong tuần? (무슨 요일에 한국어를 배워요?)",
            "2. Tiết học bắt đầu từ mấy giờ và kết thúc lúc mấy giờ? (수업이 몇 시부터 몇 시까지예요?)",
            "3. Bạn thấy lớp học tiếng Hàn thế nào? Phần nào khó nhất? (한국어 수업이 어때요? 어느 부분이 제일 어려워요?)",
            "4. Sau khi kết thúc tiết học, bạn thường làm gì? (수업이 끝난 후에 보통 무엇을 해요?)"
        ],
        "target_grammar": [
            "N + 부터 N + 까지 (từ ~ đến ~)",
            "V + -(으)ㄹ 수 있다/없다 (có thể / không thể)",
            "V + -고 싶다 (muốn làm gì)",
            "V + -(으)ㄹ 때 (khi làm gì)"
        ],
        "target_vocabulary": [
            "수업 (tiết học)", "한국어 (tiếng Hàn)", "선생님 (giáo viên)", "시작하다 (bắt đầu)",
            "끝나다 (kết thúc)", "질문하다 (đặt câu hỏi)", "시험 (kỳ thi)", "동아리 (câu lạc bộ)",
            "숙제 (bài tập)", "어렵다 (khó)", "재미있다 (thú vị)"
        ]
    },
    "🍲 6. 음식 (Food & Taste)": {
        "title": "음식 (Ẩm thực, Món ăn yêu thích & Vị giác)",
        "scenario": "Hãy nói về món ăn Hàn Quốc hoặc món ăn Việt Nam mà bạn yêu thích nhất: tên món ăn, hương vị (cay, ngọt, mặn, thanh đạm), bạn đã từng ăn thử chưa và bạn thường ăn món đó với ai.",
        "guiding_questions": [
            "1. Bạn thích món ăn nào nhất? (무슨 음식을 제일 좋아해요?)",
            "2. Món ăn đó có vị như thế nào? Cay, ngọt hay mặn? (그 음식 맛이 어때요? 매워요, 달아요, 짜요?)",
            "3. Bạn đã từng ăn Kimchi, Tteokbokki hay Samgyeopsal chưa? (김치나 떡볶이를 먹어 봤어요?)",
            "4. Bạn có biết tự nấu món ăn đó không? (그 음식을 직접 만들 줄 알아요?)"
        ],
        "target_grammar": [
            "N + 을/를 좋아하다/싫어하다 (thích / ghét)",
            "V + -아/어 보다 (đã từng thử làm gì)",
            "V + -(으)ㄹ 줄 알다/모르다 (biết / không biết cách làm)",
            "A/V + -(으)니까 (vì... nên)"
        ],
        "target_vocabulary": [
            "음식 (món ăn)", "맛있다 (ngon)", "맵다 (cay)", "달다 (ngọt)", "짜다 (mặn)",
            "싱겁다 (nhạt)", "불고기 (Bulgogi)", "비빔밥 (Bibimbap)", "김치찌개 (canh Kimchi)",
            "만들다 (nấu/làm món)", "식당 (quán ăn)"
        ]
    },
    "⏰ 7. 하루 생활 (Daily Routine)": {
        "title": "하루 생활 (Thời gian biểu & Sinh hoạt một ngày)",
        "scenario": "Hãy miêu tả chi tiết lịch trình sinh hoạt một ngày bình thường của bạn từ sáng đến tối: thức dậy lúc mấy giờ, làm những việc gì vào buổi sáng, chiều, tối và đi ngủ lúc mấy giờ.",
        "guiding_questions": [
            "1. Buổi sáng bạn thường thức dậy lúc mấy giờ? (아침에 보통 몇 시에 일어나요?)",
            "2. Sau khi thức dậy, bạn làm những việc gì? (일어나서 무엇을 해요? 세수를 하고 아침을 먹어요?)",
            "3. Buổi chiều và buổi tối bạn làm gì? Ăn tối lúc mấy giờ? (오후와 저녁에 무엇을 해요? 몇 시에 저녁을 먹어요?)",
            "4. Ban đêm bạn đi ngủ lúc mấy giờ? (밤에 몇 시에 자요?)"
        ],
        "target_grammar": [
            "Thời gian + 에 (vào lúc mấy giờ)",
            "V + -고 (liên từ nối chuỗi hành động liên tiếp)",
            "V + -아/어서 (trình tự thời gian hành động)",
            "Số thuần Hàn + 시, Số Hán Hàn + 분 (cách nói giờ phút)"
        ],
        "target_vocabulary": [
            "일어나다 (thức dậy)", "세수하다 (rửa mặt)", "이를 닦다 (đánh răng)",
            "아침/점심/저녁 (sáng/trưa/tối)", "밥을 먹다 (ăn cơm)",
            "학교에 가다/출근하다 (đi học/đi làm)", "운동하다 (tập thể dục)",
            "자다 (ngủ)", "보통 (thông thường)"
        ]
    },
    # --- CHỦ ĐỀ MỞ RỘNG TÌNH HUỐNG THỰC TẾ ---
    "🧳 8. 여행 및 호텔 문제 해결 (Travel & Hotel Issues)": {
        "title": "여행 및 호텔 문제 해결 (Xử lý sự cố du lịch & khách sạn)",
        "scenario": "Bạn đang đi du lịch hoặc công tác tại Busan. Phòng khách sạn của bạn máy lạnh bị hỏng hoặc bạn bị mất chìa khóa phòng. Hãy đến quầy lễ tân trình bày sự cố và nhờ nhân viên hỗ trợ.",
        "guiding_questions": [
            "1. Xin lỗi, tôi ở phòng 304, điều hòa không hoạt động được. (실례지만 304호인데요, 에어컨이 안 돼요.)",
            "2. Bạn có thể kiểm tra giúp tôi được không? (확인해 주실 수 있어요?)",
            "3. Nếu không sửa được, tôi có thể đổi phòng khác không? (방을 바꿀 수 있어요?)",
            "4. Tôi có thể nhận phòng mới lúc mấy giờ? (새 방을 몇 시에 받을 수 있어요?)"
        ],
        "target_grammar": ["-아/어 주시겠어요?", "-(으)ㄹ 수 있어요/없어요", "-아/어서 (nguyên nhân)", "안 돼요"],
        "target_vocabulary": ["호텔 (khách sạn)", "프런트 (quầy lễ tân)", "방 (phòng)", "열쇠/키 (chìa khóa)", "에어컨 (máy lạnh)", "고장 나다 (bị hỏng)", "바꾸다 (đổi)", "도와주다 (giúp đỡ)"]
    },
    "🛍️ 9. 쇼핑 및 가격 묻기 (Shopping & Asking for Price)": {
        "title": "쇼핑 및 가격 묻기 (Mua sắm tại chợ Dongdaemun)",
        "scenario": "Bạn đang mua áo khoác tại chợ Dongdaemun. Bạn muốn hỏi người bán xem có màu đen hoặc cỡ lớn hơn không, và thử xin giảm giá một chút.",
        "guiding_questions": [
            "1. Cái áo này bao nhiêu tiền ạ? (이 옷 얼마예요?)",
            "2. Có cỡ to hơn hoặc màu đen không ạ? (더 큰 사이즈나 검은색 있어요?)",
            "3. Tôi có thể mặc thử được không? (입어 봐도 돼요?)",
            "4. Bác giảm giá cho cháu một chút được không ạ? (조금만 깎아 주세요.)"
        ],
        "target_grammar": ["-아/어 봐도 돼요?", "-(으)세요", "조금만 ~", "N + 있어요/없어요"],
        "target_vocabulary": ["옷 (quần áo)", "사이즈 (kích cỡ)", "색깔 (màu sắc)", "검은색 (màu đen)", "입어 보다 (mặc thử)", "깎아 주다 (giảm giá)", "얼마예요 (bao nhiêu tiền)", "계산 (thanh toán)"]
    },
    "🏥 10. 병원 및 약국 증상 설명 (Pharmacy & Clinic)": {
        "title": "병원 및 약국 증상 설명 (Mô tả triệu chứng tại hiệu thuốc)",
        "scenario": "Bạn bị cảm lạnh, đau đầu và sốt từ tối qua. Bạn đến hiệu thuốc gần nhà để mua thuốc và hỏi cách uống thuốc.",
        "guiding_questions": [
            "1. Từ hôm qua tôi bị đau đầu và sốt. (어제부터 머리가 아프고 열이 나요.)",
            "2. Hãy cho tôi thuốc cảm. (감기약 좀 주세요.)",
            "3. Thuốc này uống như thế nào ạ? (이 약은 어떻게 먹어야 해요?)"
        ],
        "target_grammar": ["-았/었어요 (quá khứ)", "-아/어야 해요 (phải làm gì)", "하루에 ~번 (số lần)"],
        "target_vocabulary": ["약국 (hiệu thuốc)", "감기약 (thuốc cảm)", "머리가 아프다 (đau đầu)", "열이 나다 (bị sốt)", "식후 (sau bữa ăn)", "하루 세 번 (ngày 3 lần)", "드시다/먹다 (uống/dùng thuốc)"]
    }
}

# ==========================================
# CÁC HÀM XỬ LÝ LƯU TRỮ VÀ WEBHOOK
# ==========================================
CSV_FILE_PATH = os.getenv("CSV_SAVE_PATH", "data/evaluations.csv")

def save_result_to_csv(data_dict: dict, file_path: str = CSV_FILE_PATH):
    """Lưu kết quả chấm thi vào file CSV cục bộ"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df_new = pd.DataFrame([data_dict])
    if os.path.exists(file_path):
        df_new.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(file_path, mode='w', header=True, index=False, encoding='utf-8-sig')

def send_result_to_webhook(webhook_url: str, payload: dict) -> tuple[bool, str]:
    """Gửi kết quả chấm qua Webhook (Google Sheets Apps Script hoặc REST API)"""
    if not webhook_url or not webhook_url.strip():
        return False, "Chưa cấu hình URL Webhook."
    try:
        response = requests.post(
            webhook_url.strip(),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code in [200, 201]:
            return True, "Đã gửi dữ liệu thành công lên Webhook Google Sheets!"
        else:
            return False, f"Webhook trả về mã lỗi: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return False, f"Lỗi khi gửi webhook: {str(e)}"

# ==========================================
# HÀM GỌI GEMINI API PHÂN TÍCH ÂM THANH
# ==========================================
def analyze_korean_speech(audio_bytes: bytes, topic_key: str, student_name: str, api_key: str, model_name: str = "gemini-1.5-flash") -> dict:
    """Gửi trực tiếp audio bytes đến Gemini API để nhận diện và chấm điểm"""
    if not api_key:
        raise ValueError("Vui lòng nhập Gemini API Key để tiếp tục!")

    genai.configure(api_key=api_key)
    topic_info = TOPIC_DATA.get(topic_key, {})

    prompt = f"""
    Bạn là Chuyên gia Khảo thí và Giảng viên Tiếng Hàn giàu kinh nghiệm, chuyên chấm thi nói cho học sinh trình độ SƠ CẤP (초급 - tương đương TOPIK I Cấp 1, Cấp 2 hoặc CEFR A1-B1).

    THÔNG TIN BÀI THI:
    - Học sinh: {student_name}
    - Chủ đề: {topic_info.get('title', topic_key)}
    - Bối cảnh & Nhiệm vụ: {topic_info.get('scenario', '')}
    - Ngữ pháp trọng tâm kỳ vọng: {', '.join(topic_info.get('target_grammar', []))}
    - Từ vựng trọng tâm kỳ vọng: {', '.join(topic_info.get('target_vocabulary', []))}

    NHIỆM VỤ CỦA BẠN:
    1. Lắng nghe trực tiếp file âm thanh tiếng Hàn được cung cấp.
    2. Chuyển đổi chính xác những gì học sinh đã nói thành văn bản tiếng Hàn (Korean Transcript). Giữ nguyên cả những chỗ ngập ngừng, phát âm sai hoặc ngữ pháp chưa chuẩn nếu có.
    3. Dịch nghĩa câu nói của học sinh sang tiếng Việt.
    4. Chấm điểm theo thang điểm 10 (thang 1 chữ số thập phân, ví dụ: 8.5) theo 3 tiêu chí:
       - grammar_vocab (Ngữ pháp & Từ vựng): Sử dụng đúng tiểu từ (은/는, 이/가, 을/를), đuôi câu sơ cấp (-아/어요, -ㅂ/습니다). Đặc biệt ưu tiên đánh giá mức độ vận dụng chính xác các từ vựng và cấu trúc ngữ pháp trọng tâm được kỳ vọng ở chủ đề trên.
       - coherence_fluency (Độ mạch lạc & Lưu loát): Khả năng trả lời đúng trọng tâm nhiệm vụ, tốc độ nói, độ tự nhiên.
       - pronunciation (Phát âm & Ngữ điệu): Phát âm nguyên âm/phụ âm, âm căng (ㄲ, ㄸ, ㅃ, ㅆ, ㅉ), âm bật hơi (ㅋ, ㅌ, ㅍ, ㅊ), nối âm (연음) và biến âm batchim.
       - overall: Điểm trung bình trọng số = (grammar_vocab * 0.35) + (coherence_fluency * 0.35) + (pronunciation * 0.30), làm tròn 1 chữ số thập phân.
    5. Đưa ra phân tích chi tiết:
       - strengths: 2-3 lời khen cụ thể về những gì học sinh đã làm tốt.
       - error_corrections: Danh sách các lỗi sai cần sửa. Mỗi lỗi gồm: 'original' (câu học sinh nói), 'corrected' (câu chuẩn tự nhiên sơ cấp), 'explanation' (giải thích chi tiết bằng tiếng Việt).
       - pronunciation_hints: 1-3 hướng dẫn phát âm cụ thể (ví dụ cách đọc nối âm, ngữ điệu câu hỏi).
       - encouragement: Lời nhận xét tổng quan ấm áp, động viên học sinh kèm 1 câu chúc ngắn bằng tiếng Hàn (ví dụ: '참 잘했어요! 앞으로도 파이팅하세요!').

    ĐỊNH DẠNG TRẢ VỀ:
    BẮT BUỘC trả về định dạng JSON thuần túy (RFC 8259) theo đúng cấu trúc sau, không kèm bất kỳ giải thích ngoài JSON:
    {{
      "transcript_korean": "...",
      "transcript_vietnamese": "...",
      "scores": {{
        "grammar_vocab": 8.0,
        "coherence_fluency": 7.5,
        "pronunciation": 8.0,
        "overall": 7.8
      }},
      "strengths": ["...", "..."],
      "error_corrections": [
        {{
          "original": "...",
          "corrected": "...",
          "explanation": "..."
        }}
      ],
      "pronunciation_hints": [
        {{
          "target_word": "...",
          "phonetic_guide": "...",
          "advice": "..."
        }}
      ],
      "encouragement": "..."
    }}
    """

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.3
        }
    )

    audio_part = {
        "mime_type": "audio/wav",
        "data": audio_bytes
    }

    response = model.generate_content([prompt, audio_part])
    
    # Parse JSON
    try:
        content_text = response.text.strip()
        # Loại bỏ markdown fences nếu còn sót
        if content_text.startswith("```json"):
            content_text = content_text[7:]
        if content_text.endswith("```"):
            content_text = content_text[:-3]
        return json.loads(content_text.strip())
    except Exception as e:
        raise ValueError(f"Không thể đọc kết quả JSON từ Gemini: {str(e)}\nNội dung thô: {response.text}")


# ==========================================
# GIAO DIỆN THANH BÊN (SIDEBAR)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/323/323315.png", width=60)
    st.title("⚙️ Cấu hình hệ thống")
    
    # 1. API Key
    default_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "🔑 Gemini API Key",
        value=default_api_key,
        type="password",
        help="Lấy API Key miễn phí tại Google AI Studio: https://aistudio.google.com"
    )
    
    # 2. Chọn mô hình Gemini
    selected_model = st.selectbox(
        "🧠 Mô hình Gemini",
        ["gemini-1.5-flash", "gemini-3.8-flash", "gemini-1.5-pro"],
        index=0,
        help="Khuyến nghị dùng gemini-1.5-flash hoặc gemini-3.8-flash để xử lý âm thanh nhanh và chính xác."
    )
    
    # 3. Cấu hình Webhook Google Sheets
    default_webhook = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")
    webhook_url_input = st.text_input(
        "🌐 Google Sheets Webhook URL",
        value=default_webhook,
        placeholder="https://script.google.com/macros/s/.../exec",
        help="Dán URL Web App triển khai từ Google Apps Script (xem file google_sheets_script.js)."
    )

    st.markdown("---")
    st.subheader("📊 Lịch sử chấm thi")
    
    if os.path.exists(CSV_FILE_PATH):
        try:
            df_hist = pd.read_csv(CSV_FILE_PATH)
            st.metric("Tổng lượt thi đã lưu", len(df_hist))
            if not df_hist.empty and "Overall_Score" in df_hist.columns:
                st.metric("Điểm trung bình", f"{df_hist['Overall_Score'].mean():.1f} / 10")
            
            # Nút tải file CSV
            with open(CSV_FILE_PATH, "rb") as f:
                st.download_button(
                    label="📥 Tải file CSV kết quả",
                    data=f.read(),
                    file_name=f"korean_speaking_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        except Exception:
            st.info("Chưa có bản ghi kết quả nào.")
    else:
        st.info("Chưa có bản ghi nào. Dữ liệu sẽ xuất hiện khi có học sinh chấm bài.")

# ==========================================
# GIAO DIỆN CHÍNH (MAIN PAGE)
# ==========================================
st.markdown('<div class="main-title">🇰🇷 Khảo Thí Nói Tiếng Hàn Trực Tiếp với AI (초급)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Hệ thống ứng dụng Google Gemini Multimodal Audio AI để nhận diện giọng nói, đánh giá phát âm và phản hồi tức thì cho người học sơ cấp.</div>', unsafe_allow_html=True)

# 1. THÔNG TIN THÍ SINH & CHỦ ĐỀ
col_st1, col_st2 = st.columns([1, 1])
with col_st1:
    student_name = st.text_input("👤 Họ và tên học sinh *", placeholder="Ví dụ: Nguyễn Phương Thảo")
with col_st2:
    student_id = st.text_input("🏷️ Mã số học sinh / Lớp", placeholder="Ví dụ: KOR-B1-02")

selected_topic_key = st.selectbox("🎯 Chọn chủ đề bài thi nói:", list(TOPIC_DATA.keys()))
topic_info = TOPIC_DATA[selected_topic_key]

# Hộp thông tin kịch bản & gợi ý bài thi
with st.container():
    vocab_html = ""
    if "target_vocabulary" in topic_info and topic_info["target_vocabulary"]:
        vocab_tags = " ".join([
            f'<span style="background-color:#EEF2FF;color:#3730A3;padding:3px 9px;border-radius:6px;font-size:0.88rem;margin-right:6px;display:inline-block;margin-bottom:6px;border:1px solid #C7D2FE;font-weight:500;">{v}</span>'
            for v in topic_info["target_vocabulary"]
        ])
        vocab_html = f"<div style='margin-top:0.7rem;'><strong>📖 Từ vựng trọng tâm:</strong><br><div style='margin-top:4px;'>{vocab_tags}</div></div>"

    grammar_tags = " ".join([f'<code>{g}</code>' for g in topic_info.get('target_grammar', [])])

    st.markdown(f"""
    <div class="korean-box">
        <strong>📋 Bối cảnh tình huống:</strong> {topic_info['scenario']}<br>
        <div style="margin-top:0.5rem;"><strong>💡 Gợi ý câu trả lời & nhiệm vụ:</strong>
        <ul style="margin-top:0.3rem; margin-bottom:0.5rem;">
            {''.join(f'<li>{q}</li>' for q in topic_info['guiding_questions'])}
        </ul>
        </div>
        <strong>📌 Ngữ pháp khuyến khích sử dụng:</strong> {grammar_tags}
        {vocab_html}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# 2. KHU VỰC THU ÂM TRỰC TIẾP TỪ TRÌNH DUYỆT
st.subheader("🎙️ Thu âm bài nói trực tiếp")
st.write("Bấm nút **Bắt đầu ghi âm** bên dưới, phát biểu bằng tiếng Hàn tự nhiên (khoảng 20–45 giây), sau đó bấm **Dừng & Nộp bài**:")

audio_col, fallback_col = st.columns([1, 1])

recorded_audio_bytes = None

with audio_col:
    st.markdown("**1. Thu âm trực tiếp qua Microphone:**")
    if mic_recorder:
        audio_output = mic_recorder(
            start_prompt="🔴 Bắt đầu ghi âm",
            stop_prompt="⏹️ Dừng ghi âm",
            key="korean_mic_recorder",
            just_once=False,
            use_container_width=True
        )
        if audio_output is not None and "bytes" in audio_output:
            recorded_audio_bytes = audio_output["bytes"]
            st.success("✅ Đã ghi âm thành công!")
            st.audio(recorded_audio_bytes, format="audio/wav")
    else:
        st.warning("Component mic_recorder chưa sẵn sàng. Bạn có thể sử dụng mục tải file bên cạnh.")

with fallback_col:
    st.markdown("**2. Hoặc tải lên file âm thanh sẵn có:**")
    uploaded_file = st.file_uploader(
        "Chọn file âm thanh (.wav, .mp3, .m4a)",
        type=["wav", "mp3", "m4a", "webm"],
        label_visibility="collapsed"
    )
    if uploaded_file is not None:
        recorded_audio_bytes = uploaded_file.read()
        st.audio(recorded_audio_bytes)

# 3. NÚT CHẤM ĐIỂM
st.markdown("<br>", unsafe_allow_html=True)
evaluate_btn = st.button("🚀 Gửi Bài & Bắt Đầu Chấm Điểm với AI Giám Khảo", type="primary", use_container_width=True)

if evaluate_btn:
    if not student_name.strip():
        st.error("⚠️ Vui lòng nhập họ tên học sinh trước khi chấm điểm.")
    elif not recorded_audio_bytes:
        st.error("⚠️ Chưa có bản thu âm nào. Vui lòng ghi âm trực tiếp hoặc tải file âm thanh lên.")
    elif not api_key_input.strip():
        st.error("⚠️ Vui lòng cấu hình Gemini API Key tại thanh bên trái (Sidebar).")
    else:
        with st.spinner("🤖 AI Giám khảo đang lắng nghe giọng nói tiếng Hàn, chuyển văn bản và phân tích lỗi sai... Vui lòng đợi trong giây lát..."):
            try:
                # Thực hiện phân tích qua Gemini API
                result = analyze_korean_speech(
                    audio_bytes=recorded_audio_bytes,
                    topic_key=selected_topic_key,
                    student_name=student_name,
                    api_key=api_key_input.strip(),
                    model_name=selected_model
                )
                
                # Lưu vào Session State để duy trì hiển thị
                st.session_state["latest_evaluation"] = result
                st.session_state["latest_student_name"] = student_name
                st.session_state["latest_student_id"] = student_id
                st.session_state["latest_topic"] = topic_info["title"]
                
                # Lưu vào CSV cục bộ
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                csv_payload = {
                    "Timestamp": now_str,
                    "Student_Name": student_name,
                    "Student_ID": student_id if student_id else "N/A",
                    "Topic": topic_info["title"],
                    "Overall_Score": result["scores"]["overall"],
                    "Grammar_Score": result["scores"]["grammar_vocab"],
                    "Coherence_Score": result["scores"]["coherence_fluency"],
                    "Pronunciation_Score": result["scores"]["pronunciation"],
                    "Transcript_Korean": result.get("transcript_korean", ""),
                    "Transcript_Vietnamese": result.get("transcript_vietnamese", ""),
                    "Feedback_Summary": result.get("encouragement", "")
                }
                save_result_to_csv(csv_payload, CSV_FILE_PATH)
                
                # Gửi Webhook nếu có cấu hình
                if webhook_url_input.strip():
                    webhook_data = {
                        "timestamp": now_str,
                        "student_name": student_name,
                        "student_id": student_id if student_id else "N/A",
                        "topic": topic_info["title"],
                        "overall_score": result["scores"]["overall"],
                        "grammar_score": result["scores"]["grammar_vocab"],
                        "coherence_score": result["scores"]["coherence_fluency"],
                        "pronunciation_score": result["scores"]["pronunciation"],
                        "transcript_korean": result.get("transcript_korean", ""),
                        "transcript_vietnamese": result.get("transcript_vietnamese", ""),
                        "feedback_summary": result.get("encouragement", "")
                    }
                    wb_success, wb_msg = send_result_to_webhook(webhook_url_input.strip(), webhook_data)
                    st.session_state["webhook_status"] = (wb_success, wb_msg)

                st.success("🎉 Hoàn tất phân tích & chấm điểm!")

            except Exception as ex:
                st.error(f"❌ Quá trình chấm điểm thất bại: {str(ex)}")

# 4. HIỂN THỊ KẾT QUẢ CHẤM ĐIỂM
if "latest_evaluation" in st.session_state:
    res = st.session_state["latest_evaluation"]
    scores = res.get("scores", {})
    
    st.markdown("---")
    st.subheader(f"📊 BẢNG KẾT QUẢ ĐÁNH GIÁ: {st.session_state.get('latest_student_name', '')}")
    
    # 4 Ô Điểm số
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="score-card">
            <div class="score-val">{scores.get('overall', 0)}</div>
            <div class="score-lbl">🏆 ĐIỂM TỔNG KẾT</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="score-card">
            <div class="score-val">{scores.get('grammar_vocab', 0)}</div>
            <div class="score-lbl">📚 Ngữ pháp & Từ vựng</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="score-card">
            <div class="score-val">{scores.get('coherence_fluency', 0)}</div>
            <div class="score-lbl">🗣️ Độ mạch lạc & Phản xạ</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="score-card">
            <div class="score-val">{scores.get('pronunciation', 0)}</div>
            <div class="score-lbl">🎯 Phát âm & Ngữ điệu</div>
        </div>
        """, unsafe_allow_html=True)

    # Hiển thị thông báo Webhook
    if "webhook_status" in st.session_state:
        ok, msg = st.session_state["webhook_status"]
        if ok:
            st.toast(f"✅ {msg}")
        else:
            st.warning(f"⚠️ Webhook: {msg}")

    # Tabs chi tiết
    tab_trans, tab_errors, tab_pronun, tab_encourage = st.tabs([
        "📝 Lời Thoại (Transcript)",
        "🔍 Sửa Lỗi Chi Tiết",
        "🎯 Gợi Ý Phát Âm & Biến Âm",
        "💌 Nhận Xét & Động Viên"
    ])
    
    with tab_trans:
        st.markdown("**Văn bản tiếng Hàn thu nhận được từ bài nói:**")
        st.info(res.get("transcript_korean", "Không có nội dung"))
        st.markdown("**Dịch nghĩa tiếng Việt:**")
        st.write(res.get("transcript_vietnamese", "Không có nội dung"))

    with tab_errors:
        st.markdown("#### 🛠️ Bảng đối chiếu câu sai và câu chuẩn:")
        corrections = res.get("error_corrections", [])
        if corrections:
            for idx, item in enumerate(corrections, 1):
                with st.expander(f"Lỗi {idx}: {item.get('original', '')}", expanded=True):
                    st.markdown(f"❌ **Câu ban đầu:** `{item.get('original', '')}`")
                    st.markdown(f"✅ **Đề xuất sửa lại:** `{item.get('corrected', '')}`")
                    st.markdown(f"💡 **Giải thích:** {item.get('explanation', '')}")
        else:
            st.success("Tuyệt vời! Không phát hiện lỗi ngữ pháp hay từ vựng nghiêm trọng nào.")

    with tab_pronun:
        st.markdown("#### 🔊 Hướng dẫn cải thiện phát âm & Biến âm (받침 / 연음):")
        hints = res.get("pronunciation_hints", [])
        if hints:
            for h in hints:
                st.markdown(f"- **Từ/Cụm từ:** `{h.get('target_word', '')}` → Phát âm chuẩn: `[{h.get('phonetic_guide', '')}]`")
                st.markdown(f"  *Hướng dẫn:* {h.get('advice', '')}")
        else:
            st.info("Phát âm rõ ràng, không có lỗi biến âm đáng kể.")

    with tab_encourage:
        st.markdown("#### 🌟 Điểm mạnh nổi bật:")
        for s in res.get("strengths", []):
            st.markdown(f"- ✅ {s}")
            
        st.markdown("#### 💬 Lời nhắn từ Giám khảo AI:")
        st.markdown(f"""
        <div class="feedback-box">
            {res.get('encouragement', '')}
        </div>
        """, unsafe_allow_html=True)
