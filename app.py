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

st.title("🏫 일람표 AI 점검 도구 (초정밀 버전)")
st.markdown("---")
st.info("💡 선생님들의 칼퇴를 돕기 위해 만든 도구입니다. '학생별/영역별'로 상세하게 분석하여 엑셀로 제공합니다.")

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
        st.success("상세 분석을 시작합니다... (학생별로 꼼꼼히 보느라 시간이 조금 걸릴 수 있습니다)")
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            with pdfplumber.open(uploaded_file) as pdf:
                raw_text = "".join([page.extract_text() for page in pdf.pages])
            
            safe_text = clean_text(raw_text)
            
            # [초정밀 분석을 위한 강력한 프롬프트]
            prompt = f"""
            당신은 대한민국 초등학교 생활기록부 감사관입니다.
            제공된 [학생 기록]을 [점검 기준]에 맞춰 **학생별로 매우 상세하게** 점검해야 합니다.

            **[필수 지시사항 - 절대 요약하지 마세요]**
            1. 모든 오류는 **건별로 분리**해서 출력하세요. (예: 김철수 학생에게 오타가 3개 있으면, 데이터도 3줄이 나와야 함)
            2. **학생 이름**을 반드시 찾아내어 기재하세요.
            3. **수업일수 190일**, **9개 교과(국/사/도/수/과/체/음/미/영) 존재 여부**, **스포츠클럽 기재 여부**를 필수 체크하세요.
            4. **오탈자/띄어쓰기/온점 누락**은 "어떤 단어가 틀렸는지" 정확히 지적하세요.

            **[출력 데이터 형식]**
            결과는 반드시 아래와 같은 **JSON 리스트 형식**이어야 합니다. 다른 말은 절대 하지 마세요.

            [
              {{
                "학생명": "김철수",
                "영역": "창의적체험활동(동아리)",
                "오류유형": "띄어쓰기 오류",
                "오류내용": "친구 들과 함께 -> 친구들과 함께",
                "수정제안": "띄어쓰기 수정 필요"
              }},
              {{
                "학생명": "이영희",
                "영역": "교과학습발달(국어)",
                "오류유형": "문장 부호 누락",
                "오류내용": "...발표함 -> ...발표함.",
                "수정제안": "문장 끝에 온점(.) 추가"
              }},
              {{
                "학생명": "박민수",
                "영역": "출결상황",
                "오류유형": "수업일수 오류",
                "오류내용": "188일 기재됨",
                "수정제안": "190일로 수정 필요"
              }}
            ]

            **만약 오류가 하나도 없다면 빈 리스트 `[]`를 출력하세요.**

            [점검 기준]
            {criteria_text}

            [학생 기록]
            {safe_text}
            """
            
            response = model.generate_content(prompt)
            
            # JSON 데이터 정제 (가끔 AI가 붙이는 ```json 태그 제거)
            json_str = response.text.replace("```json", "").replace("```", "").strip()
            
            # 파이썬 데이터로 변환
            data = json.loads(json_str)
            
            if not data:
                st.balloons()
                st.success("✅ 발견된 오류가 없습니다. 모든 학생의 기록이 완벽합니다!")
            else:
                st.error(f"⚠️ 총 {len(data)}건의 수정 필요 사항이 발견되었습니다.")
                
                # 데이터프레임 생성 (컬럼 순서 지정)
                df = pd.DataFrame(data)
                
                # 컬럼 순서가 뒤죽박죽일 수 있으니 정리
                if not df.empty:
                    desired_columns = ["학생명", "영역", "오류유형", "오류내용", "수정제안"]
                    # 실제 데이터에 있는 컬럼만 추려서 순서 맞춤
                    cols = [c for c in desired_columns if c in df.columns]
                    df = df[cols]
                
                # 1. 화면에 표로 보여주기 (넓게 보기)
                st.dataframe(df, use_container_width=True)
                
                # 2. 엑셀 파일 생성
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='점검결과')
                    
                    # 엑셀 열 너비 자동 조정
                    worksheet = writer.sheets['점검결과']
                    for column_cells in worksheet.columns:
                        length = max(len(str(cell.value)) for cell in column_cells)
                        if length > 50: length = 50 # 너무 넓어지는 것 방지
                        worksheet.column_dimensions[column_cells[0].column_letter].width = length + 2

                # 3. 다운로드 버튼
                st.download_button(
                    label="📥 상세 점검 결과 엑셀 다운로드",
                    data=buffer.getvalue(),
                    file_name="일람표_상세점검결과.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
        except json.JSONDecodeError:
            st.error("AI가 데이터를 표로 만드는 과정에서 실수를 했습니다. 다시 한 번 '검사 시작하기'를 눌러주세요.")
            with st.expander("AI의 원본 답변 보기 (디버깅용)"):
                st.write(response.text)
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
