import streamlit as st
import pdfplumber
import re
import google.generativeai as genai
import os

# 페이지 설정
st.set_page_config(page_title="일람표 AI 점검 도구", page_icon="🏫")

st.title("🏫 일람표 AI 점검 도구")
st.markdown("---")
st.info("💡 선생님들의 칼퇴를 돕기 위해 만든 도구입니다. 개인정보는 서버에 저장되지 않습니다.")

# 버전 확인
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
api_key_input = st.text_input("🔑 구글 AI Studio에서 받은 키를 입력하세요", type="password")
uploaded_file = st.file_uploader("📂 점검할 일람표 PDF를 올려주세요", type="pdf")

# 3. 개인정보 지우기
def clean_text(text):
    text = re.sub(r'\d{6}-\d{7}', '******-*******', text)
    return text

# 4. 검사 시작
if st.button("검사 시작하기 🚀"):
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
            genai.configure(api_key=api_key)
            # 선생님 키에 맞는 최신 모델
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "".join([page.extract_text() for page in pdf.pages])
            
            safe_text = clean_text(raw_text)
            
            # [강력해진 프롬프트]
            prompt = f"""
            당신은 대한민국 초등학교 생활기록부 전문가이자 꼼꼼한 점검관입니다.
            아래 [점검 기준]과 [특별 점검 사항]을 바탕으로 [학생 기록]을 엄격하게 점검하세요.

            **[특별 점검 사항 - 필수 확인]**
            
            1. **출결 상황 '수업일수' 체크 (매우 중요)**: 
               - 학생 기록의 '출결 상황' 표에서 '수업일수' 숫자를 찾으세요.
               - 그 숫자가 정확히 **190**인지 확인하세요.
               - 만약 190이 아니라면(예: 95, 188, 191 등) 무조건 오류로 표시하고 "수업일수 오류: 190일이어야 합니다. (현재: OOO일)"이라고 지적하세요.
            
            2. **교과 학습 발달 상황 '9개 과목' 누락 체크**:
               - '교과학습발달상황' 영역에 다음 9개 과목의 내용이 모두 들어있는지 확인하세요.
               - **필수 과목: 국어, 사회, 도덕, 수학, 과학, 체육, 음악, 미술, 영어**
               - 위 9개 과목 중 하나라도 내용이 보이지 않는다면, "과목 누락: OO 과목의 내용이 없습니다."라고 오류로 표시하세요.
            
            3. **스포츠클럽 기재 체크**:
               - '창의적 체험활동'(자율활동, 동아리활동, 진로활동) 영역을 확인하세요.
               - '학교스포츠클럽', '365+체육온', '방과후학교스포츠클럽' 관련 내용이 기재되어 있는지 확인하세요.
               - 만약 관련 내용이 전혀 없다면 "스포츠클럽 미기재: 스포츠클럽 관련 내용이 확인되지 않습니다."라고 알림을 주세요.

            **[결과 작성 가이드]**
            1. 발견된 오류나 확인 사항이 있다면 **| 항목 | 내용 | 수정 제안 |** 형식의 표로 깔끔하게 정리하세요.
            2. 오탈자, 띄어쓰기 오류, 금지어 사용도 함께 찾아주세요.
            3. **만약 위 3가지 특별 점검 사항(수업일수 190일, 9개 과목 완비, 스포츠클럽 기재)을 모두 통과하고 오탈자도 없다면, 표를 만들지 말고 "✅ 발견된 오류가 없습니다. 완벽합니다!"라고만 답변하세요.**

            [점검 기준]
            {criteria_text}

            [학생 기록]
            {safe_text}
            """
            
            response = model.generate_content(prompt)
            st.markdown(response.text)
            
            # 오류가 없을 때 축하 풍선
            if "없습니다" in response.text and "완벽합니다" in response.text:
                st.balloons()
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
