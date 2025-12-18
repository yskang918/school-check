import streamlit as st
import pdfplumber
import re
import google.generativeai as genai
import os

# 페이지 설정
st.set_page_config(page_title="생활기록부 AI 점검 도구", page_icon="🏫")

st.title("🏫 생활기록부 AI 점검 도구")
st.markdown("---")
st.info("💡 선생님들의 칼퇴를 돕기 위해 만든 도구입니다. 개인정보는 서버에 저장되지 않습니다.")

# 버전 확인 (잘 적용되었는지 화면에 표시)
st.caption(f"시스템 버전: {genai.__version__}")

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
    st.error("⚠️ 'guide.pdf' 파일이 없습니다. (파일 경로 확인 필요)")

# 2. 사용자 입력 받기
# 주의: 복사 과정에서 들어간 공백을 제거하기 위해 .strip()을 추가할 예정
api_key_input = st.text_input("🔑 구글 AI Studio에서 받은 키를 입력하세요", type="password")
uploaded_file = st.file_uploader("📂 점검할 일람표 PDF를 올려주세요", type="pdf")

# 3. 개인정보 지우기
def clean_text(text):
    text = re.sub(r'\d{6}-\d{7}', '******-*******', text)
    return text

# 4. 검사 시작
if st.button("검사 시작하기 🚀"):
    # [핵심 수정] 입력된 키 앞뒤의 공백을 자동으로 삭제합니다.
    api_key = api_key_input.strip()

    if not api_key:
        st.warning("API 키를 입력해주세요!")
    elif not uploaded_file:
        st.warning("PDF 파일을 올려주세요!")
    elif not criteria_text:
        st.warning("기준 파일이 없습니다.")
    else:
        st.success("분석을 시작합니다... (잠시만 기다려주세요)")
        
        try:
            # 설정 및 모델 연결 (공백 제거된 키 사용)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # PDF 텍스트 추출
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "".join([page.extract_text() for page in pdf.pages])
            
            # 개인정보 지우기
            safe_text = clean_text(raw_text)
            
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
            st.error(f"오류가 발생했습니다: {e}")
            # [디버깅용] 만약 또 안 되면, 키가 무슨 모델을 쓸 수 있는지 확인해줍니다.
            try:
                st.warning("🔍 (참고) 현재 키로 사용 가능한 모델 목록:")
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        st.write(f"- {m.name}")
            except:
                st.error("API 키가 올바르지 않아 모델 목록조차 불러올 수 없습니다. 키를 다시 확인해주세요.")
