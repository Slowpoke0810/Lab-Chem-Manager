import streamlit as st
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

# 🌟 終極智慧判斷邏輯：
# 如果同一個資料夾底下有 "credentials.json" (代表是你的本地電腦)，就直接用它！
if os.path.exists("credentials.json"):
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
else:
    # 如果找不到 json 檔 (代表是在 Streamlit 雲端上)，就去讀取 Secrets 保險箱
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except Exception as e:
        st.error(f"雲端金鑰讀取失敗，請確認 Secrets 設定。錯誤訊息: {e}")
        st.stop()

client = gspread.authorize(creds)

# 你的 Google Sheets 網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1qLRCXilpTwH9LA3yTxL87gnPGfZg4NlBcMgL6NAAsqw/edit?usp=sharing" 
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

# 取得資料並轉為 DataFrame
raw_data = sheet.get_all_values()
headers = raw_data[0] 
df = pd.DataFrame(raw_data[1:], columns=headers)

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
# 3. 網頁介面設計 (UI)
# ==========================================
st.set_page_config(page_title="實驗室藥品與長晶備料系統", layout="wide")
st.title("🧪 實驗室藥品與長晶備料系統")

# 新增了第三個分頁：庫存管理
tab1, tab2, tab3 = st.tabs(["📊 藥品庫存總覽", "⚖️ 長晶備料計算器", "📝 庫存管理 (新增/更新)"])

# --- 標籤頁 1：庫存總覽 ---
with tab1:
    st.subheader("目前的藥品庫存狀態")
    if date_col:
        display_cols = ['元素', '廠商/品牌', '純度(%)', '包裝規格 (g)', weight_col_name, '系統判定狀態']
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)

# --- 標籤頁 2：長晶計算與庫存比對 ---
with tab2:
    st.subheader("化合物重量計算與庫存檢查")
    col1, col2 = st.columns(2)
    with col1:
        formula_input = st.text_input("請輸入化合物化學式 (例: ZnIn2S4, ZrSnS3, InP)", value="ZrSnS3")
    with col2:
        target_weight = st.number_input("目標總重量 (g)", min_value=0.1, value=10.0, step=0.1)
        
    if st.button("開始計算與檢查", type="primary"):
        if formula_input:
            try:
                parsed = chemparse.parse_formula(formula_input)
                total_molar_mass = 0.0
                element_masses = {}
                for elem, count in parsed.items():
                    mass = count * ATOMIC_WEIGHTS[elem]
                    element_masses[elem] = mass
                    total_molar_mass += mass
                
                st.write(f"**{formula_input}** 總分子量: `{total_molar_mass:.4f}`")
                st.markdown("### 備料清單與庫存狀態")
                
                for elem, count in parsed.items():
                    req_weight = (element_masses[elem] / total_molar_mass) * target_weight
                    req_weight = round(req_weight, 4)
                    
                    # 💡 元素別名對照：讓系統知道 P 就是紅磷
                    search_targets = [elem]
                    if elem == 'P':
                        search_targets.extend(['紅磷', '赤磷'])
                    
                    inventory = df[df['元素'].astype(str).str.strip().isin(search_targets)]
                    if inventory.empty:
                        st.error(f"❌ **{elem}**: 需要 **{req_weight}g** ｜ 庫存: **未找到該藥品紀錄**")
                    else:
                        total_weight = 0.0
                        has_unquantified_sufficient = False
                        bottle_details = [] 
                        
                        for idx, row in inventory.iterrows():
                            # 抓取表格上實際寫的名稱，如果不是原始符號就用【】標註
                            actual_name = str(row.get('元素', '')).strip()
                            brand = str(row.get('廠商/品牌', '')).strip()
                            purity = str(row.get('純度(%)', '')).strip()
                            
                            prefix = f"【{actual_name}】" if actual_name != elem else ""
                            bottle_name = f"{prefix}{brand} ({purity})" if purity else f"{prefix}{brand}"
                            if not bottle_name.strip(): 
                                bottle_name = f"{prefix}第 {len(bottle_details)+1} 罐"
                                
                            current_weight_str = str(row.get(weight_col_name, '')).strip()
                            status = str(row.get('系統判定狀態', '')).strip()
                            
                            if current_weight_str.replace('.','',1).isdigit():
                                w = float(current_weight_str)
                                total_weight += w
                                bottle_details.append(f"  - 🍾 {bottle_name}: **{w} g**")
                            else:
                                if status == "存量充足":
                                    has_unquantified_sufficient = True
                                    bottle_details.append(f"  - 🍾 {bottle_name}: **存量充足** (無數字)")
                                elif status == "已耗盡/遺失":
                                    bottle_details.append(f"  - 🍾 {bottle_name}: 已耗盡")
                                else:
                                    bottle_details.append(f"  - 🍾 {bottle_name}: {status}")

                        details_str = "\n".join(bottle_details)
                        if total_weight >= req_weight:
                            st.success(f"✅ **{elem}**: 需要 **{req_weight}g** ｜ 總重量: **{total_weight:.4f}g** ｜ 狀態: **足夠**\n\n**庫存明細:**\n{details_str}")
                        elif has_unquantified_sufficient:
                            st.info(f"💡 **{elem}**: 需要 **{req_weight}g** ｜ 總重量: **{total_weight:.4f}g** (不足) ｜ **但有藥品顯示充足，請人工確認！**\n\n**庫存明細:**\n{details_str}")
                        else:
                            st.error(f"❌ **{elem}**: 需要 **{req_weight}g** ｜ 總重量: **{total_weight:.4f}g** ｜ 狀態: **重量不足！**\n\n**庫存明細:**\n{details_str}")
            except Exception as e:
                st.error(f"解析錯誤: {e}")

# --- 標籤頁 3：庫存管理 (新增/更新) ---
with tab3:
    st.header("📝 藥品庫存管理")
    
    # 區塊 1：更新現有藥品重量
    st.subheader("1. 更新現有藥品重量")
    options = []
    # 建立選單選項，並記錄對應在 Google Sheet 的行號 (DataFrame index + 2)
    for i, row in df.iterrows():
        elem = str(row.get('元素', '')).strip()
        if not elem: continue
        brand = str(row.get('廠商/品牌', '')).strip()
        weight = str(row.get(weight_col_name, '')).strip()
        options.append(f"{elem} | {brand} | 目前重量: {weight} (行號: {i+2})")
        
    selected_option = st.selectbox("選擇要更新的藥品", options)
    new_w = st.text_input("輸入最新重量 (g)")
    
    if st.button("更新重量"):
        try:
            row_idx = int(selected_option.split("(行號: ")[1].replace(")", ""))
            col_idx = headers.index(weight_col_name) + 1
            sheet.update_cell(row_idx, col_idx, new_w)
            st.success("✅ 更新成功！請按 F5 重新整理網頁。")
        except Exception as e:
            st.error(f"更新失敗: {e}")

    st.divider()

    # 區塊 2：新增藥品
    st.subheader("2. 新增藥品")
    colA, colB, colC, colD = st.columns(4)
    with colA: new_elem = st.text_input("元素符號 (如: Ga)")
    with colB: new_brand = st.text_input("廠商/品牌")
    with colC: new_purity = st.text_input("純度(%)")
    with colD: new_weight_add = st.text_input("重量 (g)")
    
    if st.button("新增此藥品"):
        if new_elem:
            try:
                new_row = [""] * len(headers)
                new_row[headers.index('元素')] = new_elem
                new_row[headers.index('廠商/品牌')] = new_brand
                new_row[headers.index('純度(%)')] = new_purity
                new_row[headers.index(weight_col_name)] = new_weight_add
                new_row[headers.index('系統判定狀態')] = "存量充足" # 預設狀態
                sheet.append_row(new_row)
                st.success("✅ 新增成功！請按 F5 重新整理網頁。")
            except Exception as e:
                st.error(f"新增失敗: {e}")
        else:
            st.warning("請至少輸入「元素符號」！")