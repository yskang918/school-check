import streamlit as st
import pdfplumber
import re
import google.generativeai as genai
import os
import pandas as pd
import json
import io

# 페이지 설정
st.set_page_config(page_title="일람표 AI 점검 도구", page_icon="🏫", layout="wide")

st.title("🏫 일람표 AI 점검 도구 (전문가 버전)")
st.markdown("---")
st.info("💡 선생님들의 칼퇴를 돕기 위해 만든 도구입니다. 출결/교과/금지어를 정밀 분석합니다.")

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
        st.success("AI가 생활기록부를 정밀 분석 중입니다... (1분 정도 걸릴 수 있습니다)")
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "".join([page.extract_text() for page in pdf.pages])
            
            safe_text = clean_text(raw_text)
            
            # [전문가급 프롬프트 - 출결 로직 대폭 수정]
            prompt = f"""
            당신은 대한민국 초등학교 생활기록부 감사관입니다.
            제공된 [학생 기록]을 [점검 기준]에 맞춰 **학생별로 매우 상세하게** 점검해야 합니다.

            **[필수 점검 1: 금지어 및 명칭 사용]**
            1. **기재 금지 명칭**: 대학명, 사설 기관명, 상호명, 강사명 절대 금지.
               - 예시: 유튜브, 스크래치, 줌(Zoom), 굿네이버스, 인천영어마을, 네이버, 구글 등.
            2. 발견 시 "금지어 사용"으로 지적하고 순화어(동영상 자료 등) 제안.

            **[필수 점검 2: 출결 상황 (정밀 로직 적용)]**
            
            **1. 수업일수 190일 체크 (최우선)**
               - 수업일수가 **190**이 아니면 무조건 "수업일수 오류" 지적.
               - 수업일수가 틀리면 '개근' 여부는 판단하지 말 것.

            **2. '개근' 로직 (수업일수 190일인 경우만)**
               - 결석/지각/조퇴/결과가 모두 '0' -> 특기사항에 **'개근'** 필수. (없으면 오류)
               - 하나라도 '0'이 아님 -> 특기사항에 **'개근'** 금지. (있으면 오류)

            **3. 특기사항 사유 기재 조건 (매우 중요 - 엄격 적용)**
               **A. 결석 (질병/미인정/인정)**
                 - **장기결석(연속 7일 이상)**: 특기사항에 사유 입력 **필수**.
                 - **단기결석 누계 20일 이상**: 특기사항에 사유 입력 **필수**.
                 - **★중요: 위 조건에 해당하지 않는 일반 단기결석(예: 2일, 3일, 19일 등)은 사유가 없어도 '정상'입니다. 절대 오류로 지적하지 마세요.**
               
               **B. 기타결석**
                 - 1일이라도 있으면 사유 입력 **필수**. (누락 시 오류)

               **C. 지각/조퇴/결과**
                 - **누계 7회 이상**: 특기사항에 사유 입력 **필수**.
                 - **★중요: 7회 미만(1~6회)인 경우 사유가 없어도 '정상'입니다. 오류로 지적하지 마세요.**

            **[필수 점검 3: 교과 및 창체]**
            1. **9개 교과(국/사/도/수/과/체/음/미/영)** 내용 유무 확인.
            2. 창체 영역에 스포츠클럽 관련 기재 확인.
            3. 명백한 오타/띄어쓰기만 지적 (온점 누락은 무시).

            **[출력 데이터 형식 - JSON Only]**
            결과는 **반드시** 아래와 같은 **JSON 리스트 형식**으로만 출력하세요.

            [
              {{
                "학생명": "박민수",
                "영역": "출결상황",
                "오류유형": "특기사항 누락",
                "오류내용": "기타결석 1일이 있으나 사유가 없음",
                "수정제안": "기타결석 사유 입력 필요"
              }},
               {{
                "학생명": "이영희",
                "영역": "출결상황",
                "오류유형": "특기사항 누락",
                "오류내용": "지각이 8회인데 사유가 없음",
                "수정제안": "반복되는 지각 사유 입력 필요"
              }}
            ]

            **오류가 없다면 빈 리스트 `[]`를 출력하세요.**

            [점검 기준]
            {criteria_text}

            [학생 기록]
            {safe_text}
            """
            
            response = model.generate_content(prompt)
            
            # JSON 추출
            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            
            if match:
                json_str = match.group()
                data = json.loads(json_str)
                
                if not data:
                    st.balloons()
                    st.success("✅ 발견된 오류가 없습니다. 완벽합니다!")
                else:
                    st.error(f"⚠️ 총 {len(data)}건의 수정 필요 사항이 발견되었습니다.")
                    
                    df = pd.DataFrame(data)
                    
                    # 컬럼 순서 정리
                    if not df.empty:
                        desired_columns = ["학생명", "영역", "오류유형", "오류내용", "수정제안"]
                        cols = [c for c in desired_columns if c in df.columns]
                        df = df[cols]
                    
                    # 화면 표시
                    st.dataframe(df, use_container_width=True)
                    
                    # 엑셀 다운로드
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='점검결과')
                        worksheet = writer.sheets['점검결과']
                        for column_cells in worksheet.columns:
                            length = max(len(str(cell.value)) for cell in column_cells)
                            if length > 50: length = 50
                            worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

                    st.download_button(
                        label="📥 상세 점검 결과 엑셀 다운로드",
                        data=buffer.getvalue(),
                        file_name="일람표_상세점검결과.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.warning("AI가 데이터를 분석했지만, 표 형식으로 변환하지 못했습니다. 아래 내용을 확인해주세요.")
                st.write(response.text)
            
        except json.JSONDecodeError:
            st.error("데이터 변환 중 오류가 발생했습니다. 다시 시도해주시면 해결될 수 있습니다.")
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
