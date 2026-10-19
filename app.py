import streamlit as st

st.set_page_config(page_title="實驗室藥品與長晶備料系統", layout="wide")

print("LAB_APP_STARTED", flush=True)
st.info("程式已開始執行，正在載入套件與連線 Google Sheets…")

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
if not raw_data:
    st.error("表單為空，請先建立欄位標題。")
    st.stop()
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