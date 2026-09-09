import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import re
import io

# 1. ตั้งค่า Page Config เป็นบรรทัดแรกสุด
st.set_page_config(
    page_title="Recorder NB1 Debinder",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ฉีด CSS บังคับ Dark Mode
st.markdown("""
    <style>
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background-color: #0e1117 !important;
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] {
            background-color: #161b22 !important;
        }
        .stMarkdown, h1, h2, h3, p, span, label {
            color: #ffffff !important;
        }

        /* ปุ่มเคลียร์ข้อมูล */
        [data-testid="stSidebar"] div.stButton > button {
            background-color: #21262d !important;
            color: #ffffff !important;
            border: 1px solid #F0B90B !important;
            font-weight: bold !important;
            width: 100% !important;
            padding: 8px 16px !important;
        }
        [data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #F0B90B !important;
            color: #000000 !important;
        }

        /* กล่อง File Uploader */
        [data-testid="stFileUploader"] {
            background-color: #161b22 !important;
            border: 1.5px solid #F0B90B !important;
            border-radius: 8px !important;
            padding: 10px !important;
        }
        [data-testid="stFileUploader"] section {
            background-color: #1c2128 !important;
            border: 1px dashed #F0B90B !important;
            border-radius: 6px !important;
        }
        [data-testid="stFileUploader"] section div, 
        [data-testid="stFileUploader"] section span,
        [data-testid="stFileUploader"] section small {
            color: #e6edf3 !important;
        }

        /* การ์ดไฟล์ที่อัปโหลดแล้ว */
        [data-testid="stFileUploaderFileData"],
        [data-testid="stFileUploaderFileData"] > div,
        [data-testid="stFileUploaderFile"] {
            background-color: #21262d !important;
            border: 1px solid #F0B90B !important;
            border-radius: 6px !important;
        }
        [data-testid="stFileUploaderFileData"] *,
        [data-testid="stFileUploaderFile"] * {
            color: #ffffff !important;
            font-weight: bold !important;
        }
        [data-testid="stFileUploaderFile"] button,
        [data-testid="stFileUploaderFileData"] button {
            background-color: transparent !important;
            color: #F0B90B !important;
        }
        [data-testid="stFileUploaderFile"] button:hover {
            color: #ff4b4b !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. แสดงชื่อโปรแกรมหลักเสมอ
st.title("🏭 Recorder NB1 Debinder")

# 4. ฟังก์ชันอ่าน CSV อย่างปลอดภัย
def read_csv_safe(uploaded_file):
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    
    text_content = None
    encodings = ['cp932', 'shift_jis', 'utf-8-sig', 'utf-8', 'tis-620', 'latin1']
    
    for enc in encodings:
        try:
            text_content = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
            
    if text_content is None:
        text_content = raw_bytes.decode('utf-8', errors='ignore')

    string_io = io.StringIO(text_content)
    return pd.read_csv(string_io, header=None, low_memory=False, on_bad_lines='skip')

# 5. ฟังก์ชันสแกนและดึงข้อมูลอัจฉริยะ (ปรับแก้การอ่าน Header และ DateTime)
def parse_single_file(uploaded_file):
    raw_df = read_csv_safe(uploaded_file)

    data_start_row = 0
    header_row_idx = None
    date_pattern = re.compile(r'\d{2,4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}:\d{2}')

    # ค้นหาแถวที่เป็น Header และแถวเริ่มต้นข้อมูล
    for r in range(len(raw_df)):
        row_str = " ".join(raw_df.iloc[r].fillna('').astype(str))
        
        if "#EndHeader" in row_str or "TH_CH1" in row_str:
            header_row_idx = r
            
        first_cell = str(raw_df.iloc[r, 0]).strip()
        if date_pattern.search(first_cell):
            data_start_row = r
            break

    # หากหาแถวไม่เจอ ให้กำหนดค่าเริ่มต้นความปลอดภัย
    if data_start_row == 0:
        data_start_row = header_row_idx + 1 if header_row_idx is not None else 1

    header_df = raw_df.iloc[:data_start_row].copy()
    data_df = raw_df.iloc[data_start_row:].copy().reset_index(drop=True)

    # ฟังก์ชันค้นหาคอลัมน์จาก Header
    def scan_channel_col(ch_num):
        patterns = [
            re.compile(rf'TH_CH{ch_num}Ave', re.IGNORECASE),
            re.compile(rf'TH_CH{ch_num}Max', re.IGNORECASE),
            re.compile(rf'\bCH0*{ch_num}\b', re.IGNORECASE),
            re.compile(rf'ZONE\s*0*{ch_num}\b', re.IGNORECASE)
        ]

        # รวมข้อความในแต่ละคอลัมน์ช่วง Header
        for col in range(1, header_df.shape[1]):
            col_cells = header_df[col].fillna('').astype(str).tolist()
            col_text = " ".join(col_cells)
            
            for p in patterns:
                if p.search(col_text):
                    return col
        return None

    df = pd.DataFrame()

    # แปลง DateTime จาก คอลัมน์ 0 (รองรับ 'YYYY/MM/DD HH:MM:SS')
    col0_cleaned = data_df[0].astype(str).str.extract(r'(\d{2,4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}:\d{2})')[0]
    df["DateTime"] = pd.to_datetime(col0_cleaned, errors="coerce")

    def extract_series(col_idx, min_val=-50.0, max_val=2000.0):
        if col_idx is not None and col_idx < data_df.shape[1]:
            s = pd.to_numeric(data_df[col_idx], errors="coerce")
            s = s.apply(lambda x: x if (pd.notna(x) and min_val <= x <= max_val) else None)
            return s
        return pd.Series([None] * len(data_df))

    mapping_info = {}

    # Map Zone 1 - 4
    for i in range(1, 5):
        c = scan_channel_col(i)
        df[f"Zone #{i}"] = extract_series(c, min_val=0.0, max_val=1000.0)
        mapping_info[f"Zone #{i}"] = f"Col {c}" if c is not None else "Not Found"

    # Map Combustion Air Temp (CH 5)
    c5 = scan_channel_col(5)
    df["Combustion Air Temp"] = extract_series(c5, min_val=0.0, max_val=500.0)
    mapping_info["Combustion Air Temp"] = f"Col {c5}" if c5 is not None else "Not Found"

    valid_df = df.dropna(subset=["DateTime"]).reset_index(drop=True)
    return valid_df, mapping_info

def process_multiple_files(uploaded_files):
    combined_dfs = []
    logs = {}
    for file in uploaded_files:
        single_df, mapping = parse_single_file(file)
        if not single_df.empty:
            combined_dfs.append(single_df)
        logs[file.name] = mapping
    
    if not combined_dfs:
        return pd.DataFrame(), logs

    full_df = pd.concat(combined_dfs, ignore_index=True)
    full_df = full_df.drop_duplicates(subset=["DateTime"]).sort_values("DateTime").reset_index(drop=True)
    return full_df, logs

# 6. เมนู Sidebar
st.sidebar.header("📁 เมนูอัปโหลดข้อมูล")

if st.sidebar.button("🧹 เคลียร์ข้อมูลไฟล์เก่าทั้งหมด"):
    st.cache_data.clear()
    st.rerun()

uploaded_files = st.sidebar.file_uploader(
    "อัปโหลดไฟล์ CSV (.csv) ได้มากกว่า 1 ไฟล์", 
    type=["csv"],
    accept_multiple_files=True
)

# 7. ส่วนแสดงผลกราฟ
if uploaded_files:
    try:
        raw_df, channel_logs = process_multiple_files(uploaded_files)
        
        if raw_df.empty:
            st.error("⚠️ ไม่พบข้อมูลวันเวลา (DateTime) ที่ถูกต้องในไฟล์ที่อัปโหลด กรุณาตรวจสอบรูปแบบไฟล์ CSV")
            with st.sidebar.expander("🔍 ตรวจสอบการสแกนจับคู่คอลัมน์"):
                st.json(channel_logs)
        else:
            st.sidebar.success(f"รวมข้อมูลสำเร็จ {len(uploaded_files)} ไฟล์ ({len(raw_df)} แถว)")

            with st.sidebar.expander("🔍 ตรวจสอบการสแกนจับคู่คอลัมน์"):
                st.json(channel_logs)

            st.sidebar.markdown("---")
            st.sidebar.header("🎛️ Dynamic Controls")
            
            min_time = raw_df["DateTime"].min().to_pydatetime()
            max_time = raw_df["DateTime"].max().to_pydatetime()
            
            selected_time = st.sidebar.slider(
                "⏱️ ช่วงเวลา:",
                min_value=min_time,
                max_value=max_time,
                value=(min_time, max_time),
                format="MM-DD HH:mm"
            )
            
            df = raw_df[(raw_df["DateTime"] >= selected_time[0]) & (raw_df["DateTime"] <= selected_time[1])].copy()

            st.subheader("📊 Debinder Temperature & Combustion Air Monitor")

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            zone_colors = ["#FF0000", "#008000", "#0000FF", "#8A2BE2"]

            for i in range(1, 5):
                fig.add_trace(
                    go.Scatter(
                        x=df["DateTime"],
                        y=df[f"Zone #{i}"],
                        name=f"Zone #{i}",
                        mode="lines",
                        line=dict(color=zone_colors[i-1], width=2)
                    ),
                    secondary_y=False
                )

            fig.add_trace(
                go.Scatter(
                    x=df["DateTime"],
                    y=df["Combustion Air Temp"],
                    name="Combustion Air Temp",
                    mode="lines",
                    line=dict(color="#FFA500", width=2, dash="dash")
                ),
                secondary_y=True
            )

            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="#161b22",
                paper_bgcolor="#0e1117",
                hovermode="x unified",
                showlegend=True,
                legend=dict(
                    font=dict(color="#FFFFFF", size=12, family="Arial Bold"),
                    bgcolor="rgba(27, 31, 36, 0.95)",
                    bordercolor="#F0B90B",
                    borderwidth=1.5,
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.05
                ),
                xaxis=dict(
                    title=dict(text="Absolute Time [Date & Time]", font=dict(color="#FFFFFF", size=12)),
                    tickfont=dict(color="#CCCCCC", size=10),
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.08)",
                    linecolor="#555555",
                    type="date"
                ),
                yaxis=dict(
                    title=dict(text="Zone Temperature (°C) [0 - 400°C]", font=dict(color="#FFFFFF", size=12)),
                    tickfont=dict(color="#CCCCCC", size=10),
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.08)",
                    zeroline=False,
                    linecolor="#555555",
                    range=[0, 400]
                ),
                yaxis2=dict(
                    title=dict(text="Combustion Air Temp (°C) [0 - 150°C]", font=dict(color="#FFA500", size=12)),
                    tickfont=dict(color="#FFA500", size=10),
                    showgrid=False,
                    overlaying="y",
                    side="right",
                    linecolor="#FFA500",
                    range=[0, 150]
                ),
                height=500,
                margin=dict(l=60, r=180, t=30, b=40)
            )

            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📋 ตรวจสอบและดาวน์โหลดตารางข้อมูลรวมเรียงตามเวลา"):
                st.dataframe(df)
                csv_data = df.to_csv(index=False).encode('utf-8', errors='ignore')
                st.download_button(
                    label="📥 ดาวน์โหลดข้อมูลที่รวมกันแล้วเป็น CSV",
                    data=csv_data,
                    file_name="combined_debinder_data.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")

else:
    st.info("👈 กรุณาเลือกอัปโหลดไฟล์ (.csv) ที่เมนูด้านซ้าย สามารถเลือกอัปโหลดได้มากกว่า 1 ไฟล์")
