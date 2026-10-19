import streamlit as st

st.set_page_config(page_title="實驗室藥品與長晶備料系統", layout="wide")
st.title('🧪 實驗室藥品與長晶備料系統')
startup_notice = st.empty()

def startup_stage(label):
    print(f"LAB_STARTUP: {label}", flush=True)
    startup_notice.info(label)

startup_stage('1/4 程式已啟動，正在載入套件…')
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import chemparse
import json
import os   # 🌟 新增這行：用來檢查檔案是否存在

# ==========================================
# 1. 初始化與 Google Sheets 的連線 (支援本地與雲端)
# ==========================================
# 設定權限範圍
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# 保留本地 credentials.json／雲端 Secrets 雙環境自動切換。
startup_stage('2/4 正在讀取連線設定…')
try:
    if os.path.exists("credentials.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    else:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
except Exception as exc:
    print(f"LAB_STARTUP: credentials failed ({type(exc).__name__})", flush=True)
    startup_notice.error('無法讀取連線設定。請確認本地 credentials.json，或雲端 Secrets 的 gcp_service_account 設定。')
    st.caption(f'錯誤類型：{type(exc).__name__}。請勿公開貼上私密金鑰。')
    st.stop()

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1qLRCXilpTwH9LA3yTxL87gnPGfZg4NlBcMgL6NAAsqw/edit?usp=sharing"
try:
    startup_stage('3/4 正在連線 Google Sheets…')
    client = gspread.authorize(creds)
    # 每次試算表請求的連線／讀取逾時；不代表整段啟動流程的總時限。
    client.set_timeout((10, 30))
    sheet = client.open_by_url(SPREADSHEET_URL).sheet1
    startup_stage('4/4 已連上表單，正在讀取藥品庫存…')
    # 保留 get_all_values()，相容表單內重複的非必要欄位標題。
    raw_data = sheet.get_all_values()
    if not raw_data:
        startup_notice.error('表單為空，請先建立欄位標題。')
        st.stop()
    headers = raw_data[0]
    df = pd.DataFrame(raw_data[1:], columns=headers)
except Exception as exc:
    print(f"LAB_STARTUP: sheets failed ({type(exc).__name__})", flush=True)
    startup_notice.error('Google Sheets 連線或資料讀取失敗。請確認表單已分享給 Service Account、API 已啟用，並檢查網路連線。')
    st.caption(f'錯誤類型：{type(exc).__name__}')
    if st.button('重新嘗試連線'):
        st.rerun()
    st.stop()
startup_notice.empty()
print("LAB_STARTUP: inventory loaded", flush=True)

# 動態抓取重量欄位名稱
date_col = [col for col in df.columns if '2026' in col or '2025' in col] 
weight_col_name = date_col[0] if date_col else '重量紀錄 (g)' 
 
# ==========================================
# (下方接著原本的 2. 定義原子量字典...)

# ==========================================
# 2. 定義原子量字典 (完整版)
# ==========================================
ATOMIC_WEIGHTS = {
    'H': 1.008, 'He': 4.0026, 'Li': 6.94, 'Be': 9.0122, 'B': 10.81, 
    'C': 12.011, 'N': 14.007, 'O': 15.999, 'F': 18.998, 'Ne': 20.18, 
    'Na': 22.99, 'Mg': 24.305, 'Al': 26.982, 'Si': 28.085, 'P': 30.974, 
    'S': 32.06, 'Cl': 35.45, 'Ar': 39.95, 'K': 39.098, 'Ca': 40.078, 
    'Sc': 44.956, 'Ti': 47.867, 'V': 50.942, 'Cr': 51.996, 'Mn': 54.938, 
    'Fe': 55.845, 'Co': 58.933, 'Ni': 58.693, 'Cu': 63.546, 'Zn': 65.38, 
    'Ga': 69.723, 'Ge': 72.63, 'As': 74.922, 'Se': 78.971, 'Br': 79.904, 
    'Kr': 83.798, 'Rb': 85.468, 'Sr': 87.62, 'Y': 88.906, 'Zr': 91.224, 
    'Nb': 92.906, 'Mo': 95.95, 'Ru': 101.07, 'Rh': 102.91, 'Pd': 106.42, 
    'Ag': 107.87, 'Cd': 112.41, 'In': 114.82, 'Sn': 118.71, 'Sb': 121.76, 
    'Te': 127.6, 'I': 126.9, 'Xe': 131.29, 'Cs': 132.91, 'Ba': 137.33, 
    'La': 138.91, 'Ce': 140.12, 'Pr': 140.91, 'Nd': 144.24, 'Sm': 150.36, 
    'Eu': 151.96, 'Gd': 157.25, 'Tb': 158.93, 'Dy': 162.5, 'Ho': 164.93, 
    'Er': 167.26, 'Tm': 168.93, 'Yb': 173.05, 'Lu': 174.97, 'Hf': 178.49, 
    'Ta': 180.95, 'W': 183.84, 'Re': 186.21, 'Os': 190.23, 'Ir': 192.22, 
    'Pt': 195.08, 'Au': 196.97, 'Hg': 200.59, 'Tl': 204.38, 'Pb': 207.2, 
    'Bi': 208.98
}

# ==========================================
# 3. 原料、庫存與判定工具
# ==========================================
import math

STATUSES = ['存量充足', '存量不足', '待確認', '已耗盡/遺失']
LIGHTS = ['自動判定', '🟢 足夠', '🔵 待人工確認', '🔴 不足']
ALIASES = {'P': ['P', 'P (紅)', 'P(紅)', '紅磷', '赤磷'],
           'HgS': ['HgS', '硫化汞', '硫化汞 (HgS)', '硫化汞(HgS)']}


def numeric_weight(value):
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) and number >= 0 else None
    except (ValueError, TypeError):
        return None


def recipe(formula, target, use_hgs=False):
    parsed = chemparse.parse_formula(formula.strip())
    if not parsed or any(e not in ATOMIC_WEIGHTS or not math.isfinite(n) or n <= 0
                         for e, n in parsed.items()):
        raise ValueError('請輸入有效且原子量字典支援的化學式。')
    molar = sum(ATOMIC_WEIGHTS[e] * n for e, n in parsed.items())
    moles = target / molar
    counts = dict(parsed)
    required = {}
    if use_hgs:
        hg = counts.get('Hg', 0)
        if hg <= 0:
            raise ValueError('使用 HgS 原料時，目標化學式必須含 Hg。')
        if counts.get('S', 0) < hg:
            raise ValueError('HgS 提供的硫會超過目標比例，無法以此配料模式計算。')
        required['HgS'] = hg * moles * (ATOMIC_WEIGHTS['Hg'] + ATOMIC_WEIGHTS['S'])
        counts.pop('Hg')
        counts['S'] -= hg
    for elem, count in counts.items():
        if count > 0:
            required[elem] = count * moles * ATOMIC_WEIGHTS[elem]
    return molar, required


def inventory_summary(frame, material, weight_column):
    matches = frame[frame['元素'].astype(str).str.strip().isin(ALIASES.get(material, [material]))]
    total, uncertain, details = 0.0, False, []
    for _, row in matches.iterrows():
        name = str(row['元素']).strip()
        brand = str(row.get('廠商/品牌', '')).strip()
        purity = str(row.get('純度(%)', '')).strip()
        status = str(row.get('系統判定狀態', '')).strip()
        raw = row.get(weight_column, '')
        weight = numeric_weight(raw)
        label = f"【{name}】{brand} ({purity})"
        if status == '已耗盡/遺失':
            details.append(f'{label}：已耗盡／遺失（不計入可用重量；原紀錄 {raw or "空白"}）')
            continue
        if weight is not None:
            total += weight
            details.append(f'{label}：{weight:g} g｜{status}')
        else:
            uncertain |= status == '存量充足'
            details.append(f'{label}：{raw or "未秤重"}｜{status or "待確認"}')
    return total, uncertain, details


def automatic_light(total, uncertain, needed):
    if total >= needed or math.isclose(total, needed, rel_tol=1e-12, abs_tol=1e-12):
        return '🟢 足夠'
    return '🔵 待人工確認' if uncertain else '🔴 不足'


# 保留重複標題的讀取方式；僅要求程式實際使用的欄位唯一。
required_headers = ['元素', '廠商/品牌', '純度(%)', '系統判定狀態', weight_col_name]
invalid_headers = [h for h in required_headers if headers.count(h) != 1]
if invalid_headers:
    st.error('下列必要欄位缺少或重複，請先確認表單：' + '、'.join(invalid_headers))
    st.stop()


if 'save_notice' in st.session_state:
    st.success(st.session_state.pop('save_notice'))
tab1, tab2, tab3 = st.tabs(['📊 藥品庫存總覽', '⚖️ 長晶備料計算器', '📝 庫存管理 (新增/更新)'])

with tab1:
    st.subheader('目前的藥品庫存狀態')
    display_cols = ['元素', '廠商/品牌', '純度(%)', '包裝規格 (g)', weight_col_name, '系統判定狀態']
    st.dataframe(df[[c for c in display_cols if c in df.columns]], use_container_width=True)

with tab2:
    st.subheader('化合物重量計算與庫存檢查')
    formula = st.text_input('目標化學式', value='ZrSnS3').strip()
    target = st.number_input('目標總重量 (g)', min_value=0.1, value=10.0, step=0.1)
    use_hgs = st.checkbox('以 HgS（硫化汞）作為汞來源')
    st.caption('勾選後，HgS 同時供應 Hg 與 S；其餘所需硫另由 S 供應。此為理論元素質量平衡，不代表已驗證的合成條件。純度僅供顯示，未做純度校正。')
    signature = (formula, target, use_hgs)
    if st.button('開始計算與檢查', type='primary'):
        # 每次重新計算清除舊的人工覆寫，避免沿用到新一輪備料。
        for key in list(st.session_state):
            if key.startswith('light_override_'):
                del st.session_state[key]
        st.session_state['active_recipe'] = signature
    if st.session_state.get('active_recipe') == signature:
        try:
            molar, requirements = recipe(formula, target, use_hgs)
        except Exception as exc:
            st.error(f'解析或配料錯誤：{exc}')
        else:
            st.write(f'**{formula}** 摩爾質量：**{molar:.4f} g/mol**')
            st.caption('人工燈號僅用於本次頁面工作階段，不寫入 Google Sheets，也不扣除庫存。更換配方／重量／來源後請重新計算。')
            for material, needed in requirements.items():
                total, uncertain, details = inventory_summary(df, material, weight_col_name)
                auto = automatic_light(total, uncertain, needed)
                st.markdown(f'### {material}｜需要 {needed:.4f} g')
                override = st.selectbox('本次備料燈號', LIGHTS, key=f'light_override_{material}')
                effective = auto if override == '自動判定' else override
                render = {'🟢 足夠': st.success, '🔵 待人工確認': st.info, '🔴 不足': st.error}[effective]
                origin = '自動判定' if override == '自動判定' else '人工指定'
                render(f'{effective}（{origin}）｜已知可用重量：{total:.4f} g')
                if override != '自動判定':
                    st.caption(f'依原始庫存資料自動判定：{auto}。人工指定不會改變實際重量。')
                if details:
                    for detail in details:
                        st.write('🍾 ' + detail)
                else:
                    st.write('未找到該原料的庫存紀錄。')
    elif 'active_recipe' in st.session_state:
        st.info('輸入已變更，請按「開始計算與檢查」更新結果。')

with tab3:
    st.header('📝 藥品庫存管理')
    st.caption('狀態會永久儲存到表單。「已耗盡/遺失」不計入可用庫存；其餘有數字重量者仍依實際重量判定，未秤重且「存量充足」者可觸發藍燈。')
    st.subheader('1. 更新現有藥品重量／狀態')
    indices = [i for i, row in df.iterrows() if str(row['元素']).strip()]
    if indices:
        def option_label(i):
            row = df.loc[i]
            return f"{row['元素']} | {row['廠商/品牌']} | {row['純度(%)']} | {row[weight_col_name]} g (行號: {i+2})"
        selected = st.selectbox('選擇要更新的藥品', indices, format_func=option_label)
        row = df.loc[selected]
        current_status = str(row['系統判定狀態']).strip()
        status_options = STATUSES if current_status in STATUSES else [current_status] + STATUSES
        with st.form(f'edit_bottle_{selected}'):
            edit_weight = st.checkbox('同時更新重量', value=False)
            weight_text = st.text_input('最新重量 (g)，可留白或填 OL', value=str(row[weight_col_name]))
            new_status = st.selectbox('庫存狀態', status_options, index=status_options.index(current_status))
            submitted = st.form_submit_button('儲存重量／狀態')
        if submitted:
            weight_text = weight_text.strip()
            if edit_weight and weight_text not in ('', 'OL') and numeric_weight(weight_text) is None:
                st.error('重量請填非負數字、OL，或留白。')
            else:
                try:
                    # 再讀一次，避免畫面停留期間插列／排序後寫到其他罐。
                    if sheet.get_all_values() != raw_data:
                        st.error('表單資料已變更，請重新整理後再儲存。')
                    else:
                        changes = [{'range': gspread.utils.rowcol_to_a1(selected + 2, headers.index('系統判定狀態') + 1), 'values': [[new_status]]}]
                        if edit_weight:
                            changes.append({'range': gspread.utils.rowcol_to_a1(selected + 2, headers.index(weight_col_name) + 1), 'values': [[weight_text]]})
                        sheet.batch_update(changes, value_input_option='RAW')
                        st.session_state['save_notice'] = '✅ 更新成功！'
                        st.rerun()
                except Exception as exc:
                    st.error(f'更新失敗：{exc}')
    else:
        st.info('目前沒有可更新的藥品，請先新增。')

    st.divider()
    st.subheader('2. 新增藥品（元素／化合物）')
    st.caption('硫化汞請填 HgS；既有名稱「硫化汞」也可被計算器辨識。每罐請分開新增。')
    with st.form('add_bottle', clear_on_submit=False):
        new_elem = st.text_input('元素符號／化合物化學式（例如 Ga、HgS）')
        new_brand = st.text_input('廠商/品牌')
        new_purity = st.text_input('純度(%)')
        new_weight = st.text_input('重量 (g)，可留白或填 OL')
        new_status = st.selectbox('初始庫存狀態', STATUSES)
        add = st.form_submit_button('新增此藥品')
    if add:
        material, weight = new_elem.strip(), new_weight.strip()
        if not material:
            st.warning('請輸入元素符號或化合物化學式。')
        elif weight not in ('', 'OL') and numeric_weight(weight) is None:
            st.error('重量請填非負數字、OL，或留白。')
        else:
            if material in ALIASES['HgS']:
                material = 'HgS'
            try:
                if sheet.row_values(1) != headers:
                    st.error('表單欄位已變更，請重新整理後再新增。')
                else:
                    new_row = [''] * len(headers)
                    for column, value in [('元素', material), ('廠商/品牌', new_brand.strip()),
                                          ('純度(%)', new_purity.strip()), (weight_col_name, weight),
                                          ('系統判定狀態', new_status)]:
                        new_row[headers.index(column)] = value
                    sheet.append_row(new_row, value_input_option='RAW')
                    st.session_state['save_notice'] = f'✅ 已新增 {material}！'
                    st.rerun()
            except Exception as exc:
                st.error(f'新增失敗：{exc}')
