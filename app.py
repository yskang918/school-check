import streamlit as st
import pdfplumber
import re
import google.generativeai as genai
import os

# --- [설정 구간] ---
# 선생님의 API 키를 따옴표 안에 넣어주세요.
api_key = "AIzaSyCKy8Hd3eJK8DmiRxPaqFsjoKErvrkvnNA"

# 모델 설정 (최신 키와 호환되는 모델)
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')
# ------------------

st.write(f"현재 설치된 버전: {genai.__version__}")
st.set_page_config(page_title="생활기록부 AI 점검 도구", page_icon="🏫")

st.title("🏫 생활기록부 AI 점검 도구")
st.markdown("---")
st.info("💡 선생님들의 칼퇴를 돕기 위해 만든 도구입니다. 개인정보는 서버에 저장되지 않습니다.")

# 1. 점검 기준 PDF 파일 읽기
@st.cache_data
def load_criteria():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "guide.pdf")
    
    if os.path.exists(file_path):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    return None

criteria_text = load_criteria()

if not criteria_text:
    st.error("⚠️ 'guide.pdf' 파일이 없습니다. 개발자 선생님에게 문의하세요.")

# 2. 사용자 입력 받기 (이미 코드에 키를 심었으므로 입력창은 숨김 처리)
uploaded_file = st.file_uploader("📂 점검할 일람표 PDF를 올려주세요", type="pdf")

# 3. 개인정보 지우기 (마스킹)
def clean_text(text):
    text = re.sub(r'\d{6}-\d{7}', '******-*******', text) # 주민번호
    return text

# 4. 버튼 누르면 실행
if st.button("검사 시작하기 🚀"):
    if not uploaded_file:
        st.warning("PDF 파일을 올려주세요!")
    elif not criteria_text:
        st.warning("기준 파일이 없습니다.")
    else:
        st.success("분석을 시작합니다... (잠시만 기다려주세요)")
        
        try:
            # PDF 텍스트 추출
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "".join([page.extract_text() for page in pdf.pages])
            
            # 개인정보 지우기
            safe_text = clean_text(raw_text)
            
            # AI에게 물어보기
            prompt = f"""
            당신은 꼼꼼한 생활기록부 점검관입니다.
            아래 [점검 기준]을 바탕으로 [학생 기록]을 점검하세요.
            오탈자, 금지어, 문맥상 어색한 부분을 찾아 표로 정리해주세요.

            [점검 기준]
            {criteria_text}

            [학생 기록]
            {safe_text}
            """
            
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.balloons()
            
        except Exception as e:
            st.error(f"오류가 났어요 ㅠㅠ: {e}")
