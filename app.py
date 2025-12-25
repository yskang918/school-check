import streamlit as st
import pandas as pd
import io
import os
import re
import time
import random

# --- 1. [테마 및 라이브러리 설정] ---
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")

try:
    with open(".streamlit/config.toml", "w", encoding="utf-8") as f:
        f.write("""[theme]
primaryColor = "#5DADEC"
backgroundColor = "#F0F2F6" 
secondaryBackgroundColor = "#FFFFFF"
textColor = "#262730"
font = "sans serif"
""")
except:
    pass

try:
    import xlsxwriter
except ImportError:
    st.error("⚠️ 라이브러리 설치 필요: 터미널에 'pip install xlsxwriter' 입력")
    st.stop()

# 사이드바 없이 넓은 화면 사용
st.set_page_config(page_title="반편성 프로그램 v11.0", layout="wide", initial_sidebar_state="collapsed") 

# CSS: 디자인 디테일 설정
st.markdown("""
<style>
    .stApp { background-color: #F4F6F9; }
    .block-container { 
        padding-top: 2rem; 
        padding-bottom: 5rem; 
        padding-left: 1rem; 
        padding-right: 1rem; 
        max-width: 100%;
    }

    /* 점수판 헤더 */
    .class-header {
        width: 100%;
        margin-bottom: 6px;
        background-color: white;
        border-top: 4px solid #5DADEC;
        border-radius: 6px;
        padding: 6px 2px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .class-title { 
        font-size: 16px; font-weight: 800; color: #333; 
        margin: 0; line-height: 1.2; 
        white-space: nowrap;
    }
    .real-count-tag { font-size: 13px; color: #555; font-weight: 600; margin-left: 2px;}
    .score-text { font-size: 20px; font-weight: 900; color: #E65100; line-height: 1.0; margin: 3px 0; }
    
    /* 인원수 텍스트 */
    .count-text { 
        font-size: 11px; color: #333; font-weight: 700; 
        margin: 2px 0 0 0; line-height: 1.2; white-space: nowrap;
    }
    .count-sub {
        font-size: 10px; color: #757575; font-weight: 600;
        display: block; margin-top: 1px; white-space: nowrap;
    }
    
    /* 뱃지 */
    .badge-container { display: flex; justify-content: center; flex-wrap: wrap; gap: 2px; margin-top: 3px; }
    .stat-badge {
        background-color: #F3E5F5; color: #7B1FA2; border: 1px solid #E1BEE7; 
        border-radius: 4px; padding: 1px 3px; font-size: 9px; font-weight: bold;
    }
    .transfer-badge {
        background-color: #E3F2FD; color: #1565C0; border: 1px solid #90CAF9;
        border-radius: 4px; padding: 1px 3px; font-size: 9px; font-weight: bold;
    }
    
    /* 그리드 및 카드 */
    .student-grid {
        display: grid;
        grid-template-columns: 1fr 1fr; 
        gap: 2px;
    }
    .student-card {
        width: 100%; border-radius: 4px; 
        padding: 3px 1px;
        text-align: center; box-shadow: 0 1px 1px rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.05); 
        line-height: 1.1;
        overflow: hidden;
    }
    .empty-card { width: 100%; height: 100%; min-height: 25px; background: transparent; border: none; }
    
    .bg-male { background-color: #E1F5FE; border-left: 3px solid #29B6F6; }
    .bg-female { background-color: #FCE4EC; border-left: 3px solid #EC407A; }
    .card-conflict { border: 2px solid #FF3D00 !important; background-color: #FFF3E0 !important; }
    
    .std-name { 
        font-size: 13px; font-weight: 800; color: #263238; margin: 0; 
        display: flex; justify-content: center; align-items: center; gap: 1px;
        padding-bottom: 1px;
        white-space: nowrap;
    }
    .prev-class { font-size: 10px; color: #90A4AE; font-weight: 600; margin-left: 1px; } 
    .std-note { 
        font-size: 10px; color: #D81B60; font-weight: 700; 
        display: block; margin-top: 1px; 
        overflow: hidden; white-space: nowrap; text-overflow: ellipsis; 
        line-height: 1.1;
    }
    .tag-transfer-front { 
        background-color: #ffffff; color: #1565C0; border: 1px solid #1565C0; 
        padding: 0px 1px; border-radius: 2px; font-size: 9px; font-weight: bold; 
        margin-right: 1px; vertical-align: middle;
    }

    div[data-testid="stDataEditor"] { zoom: 1.1; }
    div[data-testid="stDataEditor"] th { font-weight: 800 !important; color: #111 !important; font-size: 13px !important; }
    div[data-testid="stDataEditor"] td { font-weight: 600 !important; color: #333 !important; font-size: 13px !important;}
    
    .header-title-text {
        font-size: 24px; font-weight: 700; color: #333; margin-bottom: 0px; line-height: 1.5; white-space: nowrap;
    }
    
    /* 교환 센터 스타일 */
    div[data-testid="stExpander"] {
        border: 1px solid #ddd;
        border-radius: 8px;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏫 반편성 프로그램 (v11.0)")

# --- 2. 상단 컨트롤 패널 ---
col_set, col_down, col_blank = st.columns([2, 1.5, 6.5])

with col_set:
    target_classes = st.number_input("학급 수 설정", 1, 15, 4)
    class_names = ["가", "나", "다", "라", "마", "바", "사", "아", "자", "차", "카", "타", "파", "하"]
    target_class_names = class_names[:target_classes]

with col_down:
    template_cols = ["현재반", "번호", "이름", "성별", "곤란도", "곤란도점수", "비고(쌍생아/전출)", "쌍생아_이름", "쌍생아_반", "쌍생아반편성", "분리희망학생_이름", "분리희망학생_반", "분리희망학생_번호"]
    
    def get_template_excel():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=template_cols).to_excel(writer, index=False, sheet_name='명단작성')
            ws = writer.sheets['명단작성']
            wb = writer.book
            header_format = wb.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#DCE6F1', 'border': 1})
            for i, col in enumerate(template_cols):
                ws.write(0, i, col, header_format)
                ws.set_column(i, i, len(col) + 12)
            val_int = {'validate': 'integer', 'criteria': '>', 'value': 0, 'error_title': '입력 오류', 'error_message': '숫자만 입력할 수 있습니다. (예: 1, 2, 3)'}
            col_rules = {}
            for c in [0, 1, 5, 8, 11, 12]: col_rules[c] = val_int.copy()
            val_list_reason = {'validate': 'list', 'source': ["학습부진", "교우관계", "생활지도", "학부모민원", "특수학급", "완전통합", "학교폭력", "다문화"]}
            col_rules[4] = val_list_reason
            val_list_note = {'validate': 'list', 'source': ["쌍생아", "전출예정"], 'error_message': '목록에 있는 값만 선택해주세요.'}
            col_rules[6] = val_list_note
            val_list_twin = {'validate': 'list', 'source': ["분반희망", "합반희망"], 'error_message': '목록에 있는 값만 선택해주세요.'}
            col_rules[9] = val_list_twin
            msgs = {0: "현재 학급을\n숫자로 입력하세요.\n(예: 1)", 1: "학생 번호를\n숫자로 입력하세요.\n(예: 15)", 3: "남/여 중\n하나를 입력하세요."}
            for c, msg in msgs.items():
                if c not in col_rules: col_rules[c] = {'validate': 'any'}
                col_rules[c]['input_title'] = '입력 안내'
                col_rules[c]['input_message'] = msg
            for c, rule in col_rules.items():
                col_char = chr(65 + c)
                ws.data_validation(f"{col_char}2:{col_char}1000", rule)
            ws.freeze_panes(1, 0)
        return output.getvalue()
    
    st.write("") 
    st.write("")
    st.download_button("📥 기초명단 양식", get_template_excel(), '반편성_양식.xlsx', type="primary", use_container_width=False)

# --- 3. 데이터 처리 함수 ---
def clean_text(text): return re.sub(r'[^가-힣a-zA-Z0-9]', '', str(text)) if pd.notna(text) else ""
def clean_number(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    try: return str(int(float(val)))
    except: return str(val).strip()
def get_given_name(full_name): return full_name[1:] if len(full_name) >= 2 else full_name

def build_conflict_map(df):
    lookup = {}
    conflict_pairs = set()
    separation_pairs = set()
    for _, r in df.iterrows():
        lookup[r['Internal_ID']] = r 
        lookup[f"{r['이름']}"] = r['Internal_ID']
        lookup[f"{r['이름']}_{r['현재반']}_{r['번호']}"] = r['Internal_ID']
    # 1. 분리희망
    for _, r in df.iterrows():
        my_id = r['Internal_ID']
        t_name = r['분리희망학생_이름']
        if t_name:
            t_key = f"{t_name}_{r['분리희망학생_반']}_{r['분리희망학생_번호']}"
            target_id = lookup.get(t_key)
            if not isinstance(target_id, str): target_id = lookup.get(t_name)
            if isinstance(target_id, str) and target_id != my_id:
                pair = frozenset([my_id, target_id])
                conflict_pairs.add(pair); separation_pairs.add(pair)
    # 2. 동명이인
    given_name_map = {} 
    for _, r in df.iterrows():
        g_name = get_given_name(r['이름'])
        if g_name:
            if g_name not in given_name_map: given_name_map[g_name] = []
            given_name_map[g_name].append(r['Internal_ID'])
    for g_name, ids in given_name_map.items():
        if len(ids) > 1:
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    conflict_pairs.add(frozenset([ids[i], ids[j]]))
    return conflict_pairs, separation_pairs, lookup

# --- 4. 파일 업로드 ---
st.markdown("---")
uploaded_files = st.file_uploader("엑셀 파일 선택 (여러 개 가능)", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

if uploaded_files:
    curr_files = sorted([f.name for f in uploaded_files])
    if 'uploaded_file_names' not in st.session_state or st.session_state['uploaded_file_names'] != curr_files:
        all_dfs = []
        for file in uploaded_files:
            try:
                df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                df.columns = df.columns.str.replace(' ', '').str.strip()
                all_dfs.append(df)
            except Exception as e: st.error(f"오류: {e}")

        if all_dfs:
            df = pd.concat(all_dfs, ignore_index=True)
            rename_map = {'비고(쌍생아/전출)': '비고', '비고(쌍생아/전출/동명이인)': '비고', '비고(쌍생아/전출예정)': '비고'}
            df.rename(columns=rename_map, inplace=True)
            df['이름'] = df['이름'].apply(clean_text)
            num_cols = ['현재반', '번호', '분리희망학생_반', '분리희망학생_번호', '쌍생아_반']
            if '쌍생아_번호' in df.columns: num_cols.append('쌍생아_번호')
            for c in num_cols: df[c] = df[c].apply(clean_number) if c in df.columns else ""
            for c in ['분리희망학생_이름', '쌍생아_이름', '쌍생아반편성']: df[c] = df[c].apply(clean_text) if c in df.columns else ""
            if '곤란도점수' in df.columns: df['곤란도점수'] = pd.to_numeric(df['곤란도점수'], errors='coerce').fillna(0)
            else: df['곤란도점수'] = 0
            if '곤란도' in df.columns: df['곤란도'] = df['곤란도'].fillna("")
            else: df['곤란도'] = ""
            df['비고'] = df['비고'].fillna("") if '비고' in df.columns else ""
            df['is_transfer'] = df['비고'].str.contains('전출', na=False)
            df['Internal_ID'] = [f"ID_{i}" for i in range(len(df))]
            
            st.session_state['student_data'] = df
            st.session_state['uploaded_file_names'] = curr_files
            st.success(f"✅ {len(df)}명 로드 완료")

# --- 5. [v9.2] 3단계 우선순위 배정 ---
def run_assignment(df, class_names):
    df = df.copy()
    conflict_pairs, _, _ = build_conflict_map(df)
    classes = {c: {'students': [], 'score_sum': 0, 'm': 0, 'f': 0, 'conflict_ids': set(), 'reasons': {}} for c in class_names}
    conflict_counts = {id: 0 for id in df['Internal_ID']}
    for pair in conflict_pairs:
        for p in pair: conflict_counts[p] += 1
    df['conflict_degree'] = df['Internal_ID'].map(conflict_counts)
    
    transfer_mask = df['is_transfer'] == True
    high_score_mask = (df['곤란도점수'] > 0) & (~transfer_mask)
    regular_mask = (df['곤란도점수'] == 0) & (~transfer_mask)
    
    group_1 = df[high_score_mask].sort_values(by=['conflict_degree', '곤란도점수', '이름'], ascending=[False, False, True])
    for _, row in group_1.iterrows(): assign_with_priority(row, classes, conflict_pairs, "SCORE_BALANCE", df)
        
    group_2 = df[regular_mask].sort_values(by=['conflict_degree', '성별', '이름'], ascending=[False, True, True])
    for _, row in group_2.iterrows(): assign_with_priority(row, classes, conflict_pairs, "REAL_COUNT_BALANCE", df)
        
    group_3 = df[transfer_mask].sort_values(by=['conflict_degree'], ascending=[False])
    for _, row in group_3.iterrows(): assign_with_priority(row, classes, conflict_pairs, "CUSHION_BALANCE", df)
        
    for c_name, c_info in classes.items():
        for s_id in c_info['students']: df.loc[df['Internal_ID'] == s_id, '배정반'] = c_name
    return df

def assign_with_priority(row, classes, conflict_pairs, priority_mode, df):
    s_id = row['Internal_ID']; s_score = row['곤란도점수']; s_gender = row['성별']; s_reason = row['곤란도']
    my_enemies = set()
    for pair in conflict_pairs:
        if s_id in pair: my_enemies.update(pair)
            
    class_costs = []
    transfer_ids = set(df[df['is_transfer']].Internal_ID.values)

    for c_name, c_info in classes.items():
        cost = 0
        if not my_enemies.isdisjoint(c_info['conflict_ids']): cost += float('inf')
            
        if priority_mode == "SCORE_BALANCE":
            cost += (c_info['score_sum'] * 1000)
            if s_reason and s_reason in c_info['reasons']: cost += 500
            cost += (len(c_info['students']) * 10) 
        elif priority_mode == "REAL_COUNT_BALANCE":
            real_cnt = len([sid for sid in c_info['students'] if sid not in transfer_ids])
            cost += (real_cnt * 10000)
            g_cnt = c_info['m'] if s_gender == '남' else c_info['f']
            cost += (g_cnt * 1000)
        elif priority_mode == "CUSHION_BALANCE":
            cost += (len(c_info['students']) * 1000)
            g_cnt = c_info['m'] if s_gender == '남' else c_info['f']
            cost += (g_cnt * 500)
        class_costs.append((cost, c_name))
        
    class_costs.sort(key=lambda x: x[0])
    best_class = random.choice(list(classes.keys())) if class_costs[0][0] == float('inf') else class_costs[0][1]
        
    c = classes[best_class]
    c['students'].append(s_id); c['score_sum'] += s_score; c['conflict_ids'].add(s_id)
    if s_gender == '남': c['m'] += 1
    else: c['f'] += 1
    if s_reason: 
        if s_reason not in c['reasons']: c['reasons'][s_reason] = 0
        c['reasons'][s_reason] += 1

st.write("")
col_btn_start, _ = st.columns([1.5, 8.5]) 
with col_btn_start:
    if st.button("🚀 자동 반편성 시작", type="primary", use_container_width=False):
        if 'student_data' in st.session_state:
            st.session_state['assigned_data'] = run_assignment(st.session_state['student_data'], target_class_names)
        else: st.warning("파일을 업로드하세요.")

# --- 6. 결과 화면 ---
if 'assigned_data' in st.session_state:
    st.divider()
    df = st.session_state['assigned_data']
    conflict_pairs, separation_pairs, _ = build_conflict_map(df)
    current_map = df.set_index('Internal_ID')['배정반'].to_dict()
    df['gender_rank'] = df['성별'].map({'여': 1, '남': 2}).fillna(3)
    df['display_icon'] = ""
    
    for idx, row in df.iterrows():
        s_id = row['Internal_ID']; my_cls = row['배정반']; icon = ""
        is_separated_ok = False
        for pair in separation_pairs:
            if s_id in pair:
                others = [x for x in pair if x != s_id]
                if others and others[0] in current_map:
                    if current_map[others[0]] != my_cls: is_separated_ok = True
                    else: icon = "⚡"; is_separated_ok = False; break
        if is_separated_ok and icon != "⚡": icon = "✅" 
        for pair in conflict_pairs:
            if s_id in pair:
                others = [x for x in pair if x != s_id]
                if others and others[0] in current_map and current_map[others[0]] == my_cls: icon = "⚡"; break
        df.at[idx, 'display_icon'] = icon

    # 1. 시각화 보드
    col_h_1, col_h_2, col_h_3, col_h_spacer = st.columns([1.8, 1.5, 4.5, 4], gap="small")
    with col_h_1: st.markdown("<div class='header-title-text'>👀 학급별 구성</div>", unsafe_allow_html=True)
    with col_h_2:
        output = io.BytesIO()
        export_cols = ['배정반', '번호', '이름', '성별', '현재반', '비고', '곤란도', '쌍생아_이름', '분리희망학생_이름']
        save_df_full = df.sort_values(['배정반', 'gender_rank', 'is_transfer', '이름'])
        valid_cols = [c for c in export_cols if c in save_df_full.columns]
        final_save_df = save_df_full[valid_cols]
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_save_df.to_excel(writer, index=False, sheet_name='전체')
            for cls in target_class_names:
                cls_df = final_save_df[final_save_df['배정반'] == cls]
                cls_df.to_excel(writer, index=False, sheet_name=f'{cls}반')
            wb = writer.book
            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                for i, col in enumerate(final_save_df.columns): ws.set_column(i, i, 12)
        st.download_button("📥 엑셀 저장", output.getvalue(), "반편성_최종.xlsx", type="primary", use_container_width=False)
    with col_h_3:
        st.markdown("""<div style="margin-top: 10px; font-weight: 600; font-size: 13px; color: #555; white-space: nowrap;">
            <span style='display:inline-block; margin-right:5px;'>범례:</span>
            <span style='color:#C2185B; background-color:#FCE4EC; border:1px solid #EC407A; padding: 2px 4px; border-radius:4px;'>■ 여학생</span>
            <span style='color:#1565C0; background-color:#E3F2FD; border:1px solid #90CAF9; padding: 2px 4px; border-radius:4px; margin-left:3px;'>■ 남학생</span>
            <span style='color:#78909C; margin-left:5px; font-size:11px;'>*이름(숫자)는 이전 반</span>
            </div>""", unsafe_allow_html=True)
    with col_h_spacer: st.empty()

    n_classes = len(target_class_names)
    if n_classes == 1: content_cols = [st.columns([3,1,3])[1]]
    else: content_cols = st.columns(n_classes, gap="small")

    for i, cls in enumerate(target_class_names):
        c_df = df[df['배정반'] == cls]
        score = int(c_df['곤란도점수'].sum())
        m_total = len(c_df[c_df['성별']=='남']); f_total = len(c_df[c_df['성별']=='여'])
        m_real = len(c_df[(c_df['성별']=='남') & (~c_df['is_transfer'])])
        f_real = len(c_df[(c_df['성별']=='여') & (~c_df['is_transfer'])])
        transfer_cnt = len(c_df[c_df['is_transfer']])
        real_cnt = m_real + f_real 
        
        badges_html = ""
        if transfer_cnt > 0: badges_html += f"<span class='transfer-badge'>전출:{transfer_cnt}</span>"
        for reason, count in c_df[c_df['곤란도'] != ""]['곤란도'].value_counts().items():
            badges_html += f"<span class='stat-badge'>{reason}:{count}</span>"
        
        count_html = f"<div class='count-text'>여 {f_total}명 / 남 {m_total}명</div><div class='count-sub'>(전출제외: 여 {f_real} / 남 {m_real})</div>"

        with content_cols[i]:
            st.markdown(f"""<div class="class-header"><div class="class-title">{cls}반 <span class="real-count-tag">({real_cnt}명)</span></div><div class="score-text">{score}점</div>{count_html}<div class="badge-container">{badges_html}</div></div>""", unsafe_allow_html=True)
            
            f_rows = c_df[c_df['성별'] == '여'].sort_values(['is_transfer', '이름'])
            m_rows = c_df[c_df['성별'] == '남'].sort_values(['is_transfer', '이름'])
            
            max_len = max(len(f_rows), len(m_rows))
            cards_html = ""
            for j in range(max_len):
                if j < len(f_rows):
                    r = f_rows.iloc[j]
                    bg_class = "bg-male" if r['성별'] == '남' else "bg-female"
                    conflict = "card-conflict" if "⚡" in r['display_icon'] else ""
                    t_tag = "<span class='tag-transfer-front'>전출</span>" if r['is_transfer'] else ""
                    p_disp = f"<span class='prev-class'>({str(int(float(r['현재반'])))})</span>" if pd.notna(r['현재반']) and str(r['현재반']).strip() else ""
                    note = r['곤란도'] if r['곤란도'] else ""; sc = int(r['곤란도점수'])
                    if sc > 0: note += f"({sc})"
                    rem = str(r['비고']).replace("전출예정","").strip() if pd.notna(r['비고']) else ""
                    if rem: note = f"{note} {rem}" if note else rem
                    sep_mark = " 🔸" if pd.notna(r['분리희망학생_이름']) and str(r['분리희망학생_이름']).strip() != "" else ""
                    cards_html += f"""<div class="student-card {bg_class} {conflict}"><div class="std-name">{t_tag}{r['display_icon']} {r['이름']}{sep_mark}{p_disp}</div><span class="std-note">{note}</span></div>"""
                else: cards_html += """<div class="empty-card"></div>"""
                
                if j < len(m_rows):
                    r = m_rows.iloc[j]
                    bg_class = "bg-male" if r['성별'] == '남' else "bg-female"
                    conflict = "card-conflict" if "⚡" in r['display_icon'] else ""
                    t_tag = "<span class='tag-transfer-front'>전출</span>" if r['is_transfer'] else ""
                    p_disp = f"<span class='prev-class'>({str(int(float(r['현재반'])))})</span>" if pd.notna(r['현재반']) and str(r['현재반']).strip() else ""
                    note = r['곤란도'] if r['곤란도'] else ""; sc = int(r['곤란도점수'])
                    if sc > 0: note += f"({sc})"
                    rem = str(r['비고']).replace("전출예정","").strip() if pd.notna(r['비고']) else ""
                    if rem: note = f"{note} {rem}" if note else rem
                    sep_mark = " 🔸" if pd.notna(r['분리희망학생_이름']) and str(r['분리희망학생_이름']).strip() != "" else ""
                    cards_html += f"""<div class="student-card {bg_class} {conflict}"><div class="std-name">{t_tag}{r['display_icon']} {r['이름']}{sep_mark}{p_disp}</div><span class="std-note">{note}</span></div>"""
                else: cards_html += """<div class="empty-card"></div>"""
            st.markdown(f"""<div class="student-grid">{cards_html}</div>""", unsafe_allow_html=True)

    # 2. [NEW] 1:1 교환 및 이동 센터
    st.divider()
    st.subheader("🔀 1:1 학생 교환 및 이동 센터")
    
    if 'swap_source_class' not in st.session_state: st.session_state['swap_source_class'] = target_class_names[0]
    if 'swap_target_class' not in st.session_state: st.session_state['swap_target_class'] = target_class_names[1] if len(target_class_names) > 1 else target_class_names[0]

    col_swap_left, col_swap_action, col_swap_right = st.columns([1, 0.2, 1])

    with col_swap_left:
        st.markdown("**보내는 반 (Source)**")
        s_cls = st.selectbox("반 선택", target_class_names, key="s_cls_key")
        s_students_df = df[df['배정반'] == s_cls].sort_values(['이름'])
        s_std_name = st.selectbox("학생 선택", s_students_df['이름'].tolist(), key="s_std_key") if not s_students_df.empty else None
        if s_std_name:
            s_row = df[(df['배정반'] == s_cls) & (df['이름'] == s_std_name)].iloc[0]
            st.info(f"👤 {s_row['성별']} | 📊 {int(s_row['곤란도점수'])}점 | 📝 {s_row['곤란도']}")

    with col_swap_right:
        st.markdown("**받는 반 (Target)**")
        t_cls = st.selectbox("반 선택", target_class_names, index=1 if len(target_class_names)>1 else 0, key="t_cls_key")
        t_students_df = df[df['배정반'] == t_cls].sort_values(['이름'])
        t_student_list = ["(선택 안 함 - 이동만 하기)"] + t_students_df['이름'].tolist()
        t_std_name = st.selectbox("학생 선택 (교환 대상)", t_student_list, key="t_std_key")
        if t_std_name and t_std_name != "(선택 안 함 - 이동만 하기)":
            t_row = df[(df['배정반'] == t_cls) & (df['이름'] == t_std_name)].iloc[0]
            st.info(f"👤 {t_row['성별']} | 📊 {int(t_row['곤란도점수'])}점 | 📝 {t_row['곤란도']}")
        elif t_std_name == "(선택 안 함 - 이동만 하기)":
            st.success("👉 왼쪽 학생을 이 반으로 보냅니다.")

    with col_swap_action:
        st.write(""); st.write("") 
        if st.button("🔄 실행", type="primary", use_container_width=True):
            if s_cls == t_cls: st.warning("같은 반입니다.")
            elif not s_std_name: st.warning("학생을 선택하세요.")
            else:
                s_id = df[(df['배정반'] == s_cls) & (df['이름'] == s_std_name)]['Internal_ID'].values[0]
                if t_std_name and t_std_name != "(선택 안 함 - 이동만 하기)":
                    t_id = df[(df['배정반'] == t_cls) & (df['이름'] == t_std_name)]['Internal_ID'].values[0]
                    st.session_state['assigned_data'].loc[st.session_state['assigned_data']['Internal_ID'] == s_id, '배정반'] = t_cls
                    st.session_state['assigned_data'].loc[st.session_state['assigned_data']['Internal_ID'] == t_id, '배정반'] = s_cls
                    st.toast(f"🔄 {s_std_name} ↔ {t_std_name} 교환 완료!")
                else:
                    st.session_state['assigned_data'].loc[st.session_state['assigned_data']['Internal_ID'] == s_id, '배정반'] = t_cls
                    st.toast(f"👉 {s_std_name} 이동 완료!")
                time.sleep(0.5); st.rerun()

    # 3. 이동 작업대 (Expander로 숨김 처리)
    st.write("")
    with st.expander("📋 (구버전) 전체 명단 상세 편집 열기"):
        col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 1])
        with col_f1: search_name = st.text_input("🔍 이름 검색")
        with col_f2: 
            prev_classes = sorted([str(int(float(x))) for x in df['현재반'].unique() if pd.notna(x) and str(x).strip() != ""])
            filter_prev_cls = st.multiselect("이전 반", prev_classes)
        with col_f3: filter_gender = st.multiselect("성별", ["남", "여"])
        with col_f4: filter_new_cls = st.multiselect("새 학년 반", target_class_names)
        
        view_df = df.copy()
        mask_sep = view_df['분리희망학생_이름'].notna() & (view_df['분리희망학생_이름'].astype(str).str.strip() != "")
        view_df.loc[mask_sep, '이름'] = view_df.loc[mask_sep, '이름'] + " 🔸"

        if search_name: view_df = view_df[view_df['이름'].str.contains(search_name)]
        if filter_prev_cls: 
            view_df['temp_prev'] = view_df['현재반'].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).strip()!="" else "")
            view_df = view_df[view_df['temp_prev'].isin(filter_prev_cls)]
        if filter_gender: view_df = view_df[view_df['성별'].isin(filter_gender)]
        if filter_new_cls: view_df = view_df[view_df['배정반'].isin(filter_new_cls)]
        
        view_df = view_df.sort_values(['배정반', 'gender_rank', 'is_transfer', '이름'])
        
        editor_cols = ['현재반', '이름', 'display_icon', '성별', '배정반', '곤란도', '곤란도점수', '분리희망학생_이름', '분리희망학생_반', '비고', 'Internal_ID']
        
        edited_df = st.data_editor(
            view_df[editor_cols],
            key="main_editor",
            hide_index=True,
            column_config={
                "현재반": st.column_config.NumberColumn("이전 반", width="small", disabled=True, format="%d"),
                "이름": st.column_config.TextColumn("이름", width="small", disabled=True),
                "display_icon": st.column_config.TextColumn("분리상태", width="small", disabled=True),
                "성별": st.column_config.TextColumn("성별", width="small", disabled=True),
                "배정반": st.column_config.SelectboxColumn("배정반", width="small", options=target_class_names, required=True),
                "곤란도": st.column_config.TextColumn("곤란도", width="medium", disabled=True),
                "곤란도점수": st.column_config.NumberColumn("점수", width="small", disabled=True),
                "분리희망학생_이름": st.column_config.TextColumn("분리학생이름", width="medium", disabled=True),
                "분리희망학생_반": st.column_config.TextColumn("분리학생이전반", width="small", disabled=True),
                "비고": st.column_config.TextColumn("비고", width="medium", disabled=True),
                "Internal_ID": None
            },
            use_container_width=True,
            height=600
        )

        is_changed = False
        for idx, row in edited_df.iterrows():
            s_id = row['Internal_ID']
            new_val = row['배정반']
            old_val = df.loc[df['Internal_ID']==s_id, '배정반'].values[0]
            if new_val != old_val:
                st.session_state['assigned_data'].loc[st.session_state['assigned_data']['Internal_ID']==s_id, '배정반'] = new_val
                is_changed = True
        if is_changed: st.rerun()
