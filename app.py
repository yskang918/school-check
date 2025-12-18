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
st.info("💡 선생님들의 칼퇴를 돕기 위해 만든 도구입니다. 출결/교과/창체를 정밀 분석합니다.")

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
            
            # [전문가급 프롬프트]
            prompt = f"""
            당신은 대한민국 초등학교 생활기록부 감사관입니다.
            제공된 [학생 기록]을 [점검 기준]에 맞춰 **학생별로 매우 상세하게** 점검해야 합니다.

            **[필수 점검 로직 - 출결 상황]**
            1. **수업일수 190일 체크**: 모든 학생의 수업일수가 190일인지 확인하세요.
            2. **'개근' 로직 (매우 중요)**:
               - 결석(질병/미인정/기타/인정), 지각, 조퇴, 결과가 **모두 '0'**인 경우 -> 특기사항에 **'개근'**이 반드시 있어야 함. (없으면 오류: '개근 누락')
               - 위 항목 중 **하나라도 '0'이 아닌** 경우 -> 특기사항에 **'개근'**이 있으면 절대 안 됨. (있으면 오류: '개근 삭제 필요')
            3. **특기사항 기재 요건**:
               - **기타결석**: '기타' 결석이 1일이라도 있으면 사유가 반드시 기재되어야 함.
               - **장기결석/지각/조퇴/결과**: 특기사항에 '장기' 관련 내용이 보이면 사유가 적절한지 확인.
               - **단기결석/지각/조퇴/결과**: 특별한 사유 없이 횟수만 적혀 있다면, 합산하여 사유를 적어야 하는 조건(7회/20일 등)이 되었는지 맥락을 살펴볼 것.

            **[필수 점검 로직 - 교과 및 창체]**
            1. **9개 교과 확인**: 국어, 사회, 도덕, 수학, 과학, 체육, 음악, 미술, 영어 내용 유무 확인.
            2. **스포츠클럽**: 창체 영역에 스포츠클럽/체육온 관련 기재 여부 확인.
            3. **오탈자/띄어쓰기/온점**: 정밀 확인.

            **[출력 데이터 형식 - JSON Only]**
            분석 결과는 **반드시** 아래와 같은 **JSON 리스트 형식**으로만 출력하세요. 앞뒤에 설명이나 ```json 태그를 붙이지 마세요. 순수 JSON만 출력하세요.

            [
              {{
                "학생명": "홍길동",
                "영역": "출결상황",
                "오류유형": "개근 로직 오류",
                "오류내용": "결석이 0일인데 '개근'이 없음",
                "수정제안": "특기사항에 '개근' 입력 필요"
              }},
              {{
                "학생명": "김철수",
                "영역": "출결상황",
                "오류유형": "특기사항 오류",
                "오류내용": "기타결석 1일이 있으나 사유가 없음",
                "수정제안": "기타결석 사유 입력 요망"
              }}
            ]

            **오류가 없다면 빈 리스트 `[]`를 출력하세요.**

            [점검 기준]
            {criteria_text}

            [학생 기록]
            {safe_text}
            """
            
            response = model.generate_content(prompt)
            
            # [JSON 추출 마법 코드] 
            # AI가 답변에 ```json 같은걸 붙이거나 잡담을 섞어도, 대괄호 [...] 안에 있는 내용만 쏙 뽑아냅니다.
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
            st.write("AI 원본 응답:", response.text)
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
