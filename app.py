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

st.title("🏫 일람표 AI 점검 도구")
st.markdown("---")
st.info("💡 **이름 마스킹 기능 탑재!** 이름을 가려도 **'학생 번호'**를 함께 추출하여 누구인지 식별할 수 있습니다.")

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
col1, col2 = st.columns(2)
with col1:
    api_key_input = st.text_input("🔑 구글 AI Studio API 키", type="password")
with col2:
    uploaded_file = st.file_uploader("📂 점검할 일람표 PDF 업로드", type="pdf")

# 🛡️ [보안 핵심 기능] 이름 마스킹 입력창
with st.container():
    st.success("🛡️ **[보안 옵션]** 아래 칸에 우리 반 학생 명단을 붙여넣으세요. (이름을 찾아 자동으로 가려줍니다)")
    student_names_input = st.text_area(
        "학생 이름을 여기에 붙여넣으세요 (예: 김철수, 이영희, 박민수 ...)", 
        height=100,
        placeholder="나이스 명렬표에서 이름 열을 복사해서 여기에 붙여넣기 하세요."
    )

# 3. 개인정보 지우기 로직
def clean_text(text, names_input):
    text = re.sub(r'\d{6}-\d{7}', '******-*******', text) # 주민번호 제거
    
    if names_input:
        names = re.split(r'[,\n\s]+', names_input)
        names = sorted(names, key=len, reverse=True)
        
        count = 0
        for name in names:
            name = name.strip()
            if len(name) >= 2:
                if name in text:
                    text = text.replace(name, "OOO")
                    count += 1
        return text, count
    return text, 0

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
        # 파일 읽기
        with pdfplumber.open(uploaded_file) as pdf:
            raw_text = "".join([page.extract_text() for page in pdf.pages])
        
        # 이름 마스킹 실행
        safe_text, masked_count = clean_text(raw_text, student_names_input)
        
        if student_names_input and masked_count > 0:
            st.toast(f"🔒 보안 적용 완료! 학생 이름 {masked_count}건을 'OOO'으로 가렸습니다.", icon="🛡️")
        
        st.success("AI가 생활기록부를 정밀 분석 중입니다... (논리 오류 수정 적용됨)")
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # [논리 수정된 프롬프트]
            prompt = f"""
            당신은 대한민국 초등학교 생활기록부 감사관입니다.
            제공된 [학생 기록]을 [점검 기준]에 맞춰 **학생별로 매우 상세하게** 점검해야 합니다.
            (학생 이름이 'OOO'으로 마스킹되어 있어도, 문맥을 통해 **학생 번호(예: 1번, 2번)**를 찾아내어 구분하세요.)

            **[필수 점검 1: 금지어 및 명칭 사용]**
            1. **기재 금지 명칭**: 대학명, 사설 기관명, 상호명, 강사명 절대 금지.
            2. 발견 시 "금지어 사용"으로 지적.

            **[필수 점검 2: 출결 상황 (우선순위 로직 적용 - 매우 중요)]**
            
            **[STEP 1] 수업일수 확인 (최우선)**
            - 학생의 수업일수가 **190**인지 확인하세요.
            - **[중요] 만약 수업일수가 190이 아니라면**:
               1. 무조건 "수업일수 오류"로 지적하세요.
               2. **그리고 그 학생에 대해서는 '개근' 관련 점검을 절대 하지 말고 생략하세요.** (이미 수업일수가 틀렸으므로 개근 판정은 무의미함)
            
            **[STEP 2] '개근' 여부 확인 (수업일수가 190일인 학생에게만 수행)**
            - **오직 수업일수가 190일로 정확한 학생만 이 단계를 수행하세요.**
            - 결석/지각/조퇴/결과가 모두 '0' -> 특기사항에 **'개근'** 필수. (없으면 오류)
            - 하나라도 '0' 아님 -> 특기사항에 **'개근'** 금지. (있으면 오류)

            **[STEP 3] 특기사항 사유 기재 (공통)**
            - 장기결석(연속 7일↑), 단기결석 누계 20일↑, 기타결석(1일이라도), 지각/조퇴/결과 누계 7회↑인 경우 **사유 필수**.
            - 위 조건 미만은 사유 없어도 정상.

            **[필수 점검 3: 교과 및 창체]**
            1. 9개 교과 내용 유무 확인.
            2. 창체 영역에 스포츠클럽 관련 기재 확인.
            3. 명백한 오타/띄어쓰기만 지적 (**온점 누락 무시**).

            **[출력 데이터 형식 - JSON Only]**
            결과는 **반드시** 아래와 같은 **JSON 리스트 형식**으로만 출력하세요. 설명글 금지.
            **반드시 '학생번호' 필드를 포함하세요.**

            [
              {{
                "학생번호": "1번",
                "학생명": "OOO",
                "영역": "출결상황",
                "오류유형": "수업일수 오류",
                "오류내용": "수업일수 95일 (기준 190일 미달)",
                "수정제안": "수업일수 190일로 수정 필요"
              }}
            ]

            **오류가 없다면 빈 리스트 `[]`를 출력하세요.**

            [점검 기준]
            {criteria_text}

            [학생 기록]
            {safe_text}
            """
            
            response = model.generate_content(prompt)
            
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
                    
                    if not df.empty:
                        desired_columns = ["학생번호", "학생명", "영역", "오류유형", "오류내용", "수정제안"]
                        cols = [c for c in desired_columns if c in df.columns]
                        df = df[cols]
                    
                    st.dataframe(df, use_container_width=True)
                    
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

