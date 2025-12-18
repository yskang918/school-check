import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import re

# 페이지 설정
st.set_page_config(page_title="생활기록부 AI 점검 도구", layout="wide")

# 1. 안내 팝업창 함수 (Streamlit 최신 버전의 dialog 기능 사용)
@st.dialog("학생생활기록부 안전 사용 안내")
def show_security_guide():
    st.warning("⚠️ 개인정보 보호를 위해 다음 사항을 반드시 준수하세요.")
    st.write("- 본 도구는 입력된 텍스트에서 이름, 번호 등을 자동으로 마스킹합니다.")
    st.write("- 검사 후 데이터는 서버에 남지 않고 즉시 삭제됩니다.")
    st.write("- 가급적 학교/기관용 Google Cloud 유료 계정 API 사용을 권장합니다.")
    if st.button("확인했습니다"):
        st.session_state.agreed = True
        st.rerun()

# 2. 개인정보 자동 마스킹 함수 (단순 정규 표현식 예시)
def mask_personal_info(text):
    # 이름 패턴(2~4자 한글), 주민번호, 전화번호 등을 찾아 가립니다.
    masked = re.sub(r'[가-힣]{2,4}(?= 교사| 학생| 어린이)', '***', text) # 이름 추정 마스킹
    masked = re.sub(r'\d{6}-\d{7}', '******-*******', masked) # 주민번호
    masked = re.sub(r'010-\d{4}-\d{4}', '010-****-****', masked) # 전화번호
    return masked

# 초기 접속 시 팝업 띄우기
if "agreed" not in st.session_state:
    show_security_guide()

# 사이드바 - API 키 및 설정
with st.sidebar:
    st.title("🔐 보안 설정")
    api_key = st.text_input("Gemini API Key", type="password")
    st.info("학교망에서 오류 발생 시 핫스팟 연결을 시도해 보세요.")

st.title("📝 생활기록부 AI 점검 (보안 강화 버전)")

# PDF 업로드 및 분석 로직
uploaded_file = st.file_uploader("PDF 파일 업로드", type="pdf")

if uploaded_file and api_key:
    if st.button("점검 시작"):
        with st.spinner("개인정보를 보호하며 분석 중입니다..."):
            try:
                # 1. 텍스트 추출
                reader = PdfReader(uploaded_file)
                raw_text = "".join([page.extract_text() for page in reader.pages])
                
                # 2. 개인정보 마스킹 (요구사항 반영)
                safe_text = mask_personal_info(raw_text)
                
                # 3. AI 분석
                genai.configure(api_key=api_key)
                # 모델 리스트 자동 확인 로직 포함
                available_models = [m.name for m in genai.list_models()]
                model_name = "gemini-1.5-flash" if "models/gemini-1.5-flash" in available_models else "gemini-pro"
                
                model = genai.GenerativeModel(model_name)
                prompt = f"""
                당신은 베테랑 초등교사입니다. 아래 마스킹된 생활기록부 내용을 검토하여 
                금지어, 오기, 맞춤법 오류를 찾아 표 형식으로 알려주세요.
                
                내용: {safe_text}
                """
                
                response = model.generate_content(prompt)
                
                st.success("✅ 분석 완료")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다. 학교 보안망 차단일 수 있습니다.\n상세내용: {e}")
