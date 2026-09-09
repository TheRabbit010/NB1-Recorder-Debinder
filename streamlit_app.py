import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import re

# 1. ตั้งค่า Page Config และปรับแต่ง CSS ให้เห็นตัวหนังสือชัดเจน
st.set_page_config(
    page_title="Recorder NB1",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

        /* --- 1. ปรับสไตล์ปุ่มเคลียร์ข้อมูล --- */
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

        /* --- 2. ตกแต่งกล่อง File Uploader --- */
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

        /* --- 3. แก้ไขการ์ดไฟล์ที่อัปโหลดแล้ว (แก้ปัญหาการ์ดขาวตัวหนังสือกลืน) --- */
        [data-testid="stFileUploaderFileData"],
        [data-testid="stFileUploaderFileData"] > div,
        [data-testid="stFileUploaderFile"] {
            background-color: #21262d !important;
            border: 1px solid #F0B90B !important;
            border-radius: 6px !important;
        }
        /* บังคับสีตัวอักษรชื่อไฟล์และขนาดไฟล์ให้อ่านง่าย */
        [data-testid="stFileUploaderFileData"] *,
        [data-testid="stFileUploaderFile"] * {
            color: #ffffff !important;
            font-weight: bold !important;
        }
        /* ปุ่มลบไฟล์ (X) */
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

st.title("🏭 Recorder NB1")

# 2. ฟังก์ชันอ่านไฟล์อย่างปลอดภัย
def read_excel_safe(uploaded_file):
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.csv'):
        return pd.read_csv(uploaded_file, header=None, low_memory=False)
    
    try:
        return pd.read_excel(uploaded_file, header=None, engine='openpyxl')
    except Exception:
        try:
            return pd.read_excel(uploaded_file, header=None, engine='xlrd')
        except Exception:
            return pd.read_excel(uploaded_file, header=None)

# 3. ฟังก์ชันสแกนและดึงข้อมูลอัจฉริยะ
def parse_single_file(uploaded_file):
    raw_df = read_excel_safe(uploaded_file)

    data_start_row = 28
    for r in range(min(50, len(raw_df))):
        val_str = str(raw_df.iloc[r, 0])
        if re.search(r'\d{2,4}[-/]\d{1,2}[-/]\d{1,2}', val_str):
            data_start_row = r
            break

    header_df = raw_df.iloc[:data_start_row].copy()
    data_df = raw_df.iloc[data_start_row:].copy().reset_index(drop=True)

    def scan_channel_col(ch_num, custom_keywords=None):
        patterns = [re.compile(rf'\bCH0*{ch_num}\b', re.IGNORECASE)]
        if custom_keywords:
            for kw in custom_keywords:
                patterns.append(re.compile(re.escape(kw), re.IGNORECASE))

        matched_cols = []
        for col in range(2, header_df.shape[1]):
            col_cells = header_df[col].fillna('').astype(str).tolist()
            col_text = " ".join([str(cell) for cell in col_cells])
            
            if any(p.search(col_text) for p in patterns):
                matched_cols.append(col)
        
        if not matched_cols:
            return None
        
        if len(matched_cols) == 1:
            return matched_cols[0]
            
        for col in matched_cols:
            col_cells = header_df[col].fillna('').astype(str).tolist()
            col_text = " ".join([str(cell) for cell in col_cells]).upper()
            if "MAX" in col_text:
                return col
                
        return matched_cols[-1]

    df = pd.DataFrame()
    df["DateTime"] = pd.to_datetime(data_df[0].astype(str) + " " + data_df[1].astype(str), errors="coerce")

    def extract_series(col_idx, min_val=-150.0, max_val=15000.0):
        if col_idx is not None and col_idx < data_df.shape[1]:
            s = pd.to_numeric(data_df[col_idx], errors="coerce")
            s = s.apply(lambda x: x if (pd.notna(x) and min_val <= x <= max_val) else None)
            return s
        return pd.Series([None] * len(data_df))

    mapping_info = {}

    # CH001 - CH007: Top Zone #1 - #7
    for i in range(1, 8):
        c = scan_channel_col(i)
        df[f"Top Zone #{i}"] = extract_series(c, min_val=0.0, max_val=1500.0)
        mapping_info[f"Top Zone #{i}"] = f"Col {c}" if c is not None else "Not Found"

    # CH008 - CH014: Bottom Zone #1 - #7
    for i in range(1, 8):
        ch_num = 7 + i
        c = scan_channel_col(ch_num)
        df[f"Bottom Zone #{i}"] = extract_series(c, min_val=0.0, max_val=1500.0)
        mapping_info[f"Bottom Zone #{i}"] = f"Col {c}" if c is not None else "Not Found"

    # CH015: EXIT O2
    c15 = scan_channel_col(15)
    df["EXIT O2"] = extract_series(c15, min_val=0.0, max_val=2000.0)
    mapping_info["EXIT O2 (CH15)"] = f"Col {c15}" if c15 is not None else "Not Found"

    # CH016 & CH017: Dryer #1 & Dryer #2
    c16 = scan_channel_col(16)
    c17 = scan_channel_col(17)
    df["Dryer #1"] = extract_series(c16, min_val=0.0, max_val=1000.0)
    df["Dryer #2"] = extract_series(c17, min_val=0.0, max_val=1000.0)
    mapping_info["Dryer #1 (CH16)"] = f"Col {c16}" if c16 is not None else "Not Found"
    mapping_info["Dryer #2 (CH17)"] = f"Col {c17}" if c17 is not None else "Not Found"

    # CH018: N2 Flow
    c18 = scan_channel_col(18, custom_keywords=["N2 .1", "N2.1", "N2 Flow", "N2"])
    df["N2 Flow"] = extract_series(c18, min_val=0.0, max_val=20000.0)
    mapping_info["N2 Flow (CH18/N2.1)"] = f"Col {c18}" if c18 is not None else "Not Found"

    # CH019: ENTRANCE O2
    c19 = scan_channel_col(19)
    df["ENTRANCE O2"] = extract_series(c19, min_val=0.0, max_val=2000.0)
    mapping_info["ENTRANCE O2 (CH19)"] = f"Col {c19}" if c19 is not None else "Not Found"

    # CH020: DEW POINT
    c20 = scan_channel_col(20, custom_keywords=["DEW POINT", "DEW", "DP"])
    df["DEW POINT"] = extract_series(c20, min_val=-150.0, max_val=100.0)
    mapping_info["DEW POINT (CH20)"] = f"Col {c20}" if c20 is not None else "Not Found"

    return df.dropna(subset=["DateTime"]), mapping_info

# ฟังก์ชันประมวลผลหลายไฟล์
def process_multiple_files(uploaded_files):
    combined_dfs = []
    logs = {}
    for file in uploaded_files:
        single_df, mapping = parse_single_file(file)
        combined_dfs.append(single_df)
        logs[file.name] = mapping
    
    full_df = pd.concat(combined_dfs, ignore_index=True)
    full_df = full_df.drop_duplicates(subset=["DateTime"]).sort_values("DateTime").reset_index(drop=True)
    return full_df, logs

# 4. ฟังก์ชันตกแต่งสไตล์กราฟ
def apply_industrial_style(fig, y_title, y_range=None, is_dual_axis=False):
    layout_args = dict(
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
            x=1.02
        ),
        xaxis=dict(
            title=dict(text="Absolute Time [Date & Time]", font=dict(color="#FFFFFF", size=12)),
            tickfont=dict(color="#CCCCCC", size=10),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            linecolor="#555555",
            type="date",
        ),
        yaxis=dict(
            title=dict(text=y_title, font=dict(color="#FFFFFF", size=12)),
            tickfont=dict(color="#CCCCCC", size=10),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            zeroline=False,
            linecolor="#555555",
        ),
        height=420,
        margin=dict(l=60, r=180, t=30, b=40),
    )
    if y_range and not is_dual_axis:
        layout_args["yaxis"]["range"] = y_range
        
    fig.update_layout(**layout_args)

# ส่วน Sidebar อัปโหลดไฟล์
st.sidebar.header("📁 เมนูอัปโหลดข้อมูล")

if st.sidebar.button("🧹 เคลียร์ข้อมูลไฟล์เก่าทั้งหมด"):
    st.cache_data.clear()
    st.rerun()

uploaded_files = st.sidebar.file_uploader(
    "อัปโหลดไฟล์ Yokogawa (.csv, .xlsx, .xls) ได้มากกว่า 1 ไฟล์", 
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# 5. ส่วนแสดงผลหลัก
if uploaded_files:
    try:
        raw_df, channel_logs = process_multiple_files(uploaded_files)
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

        st.sidebar.subheader("📊 เลือกกลุ่มกราฟ")
        show_g1 = st.sidebar.checkbox("1. Top Zone Temp (CH1-7)", value=True)
        show_g2 = st.sidebar.checkbox("2. Bottom Zone Temp (CH8-14)", value=True)
        show_g3 = st.sidebar.checkbox("3. Dryer Temp (CH16-17)", value=True)
        show_g4 = st.sidebar.checkbox("4. O2 & N2 Flow (CH15, CH18, CH19)", value=True)
        show_g5 = st.sidebar.checkbox("5. Dew Point (CH20)", value=True)

        # 1. Top Zone Temp (Scale: 550 - 650 °C)
        if show_g1:
            st.subheader("1. Brazing zone Top #1-#7 (CH001-CH007)")
            fig1 = go.Figure()
            top_colors = ["#FF0000", "#008000", "#0000FF", "#8A2BE2", "#A52A2A", "#FFA500", "#9ACD32"]
            for i in range(1, 8):
                fig1.add_trace(go.Scatter(
                    x=df["DateTime"], 
                    y=df[f"Top Zone #{i}"], 
                    name=f"Top Z#{i} (CH{i:03d})", 
                    mode="lines", 
                    line=dict(color=top_colors[i-1], width=2)
                ))
            apply_industrial_style(fig1, "Temperature (°C)", y_range=[550, 650])
            st.plotly_chart(fig1, use_container_width=True)

        # 2. Bottom Zone Temp (Scale: 550 - 650 °C)
        if show_g2:
            st.subheader("2. Brazing zone Bottom #1-#7 (CH008-CH014)")
            fig2 = go.Figure()
            bottom_colors = ["#E0FFFF", "#FF1493", "#808080", "#00FF00", "#008000", "#0000FF", "#8A2BE2"]
            for i in range(1, 8):
                ch_num = 7 + i
                fig2.add_trace(go.Scatter(
                    x=df["DateTime"], 
                    y=df[f"Bottom Zone #{i}"], 
                    name=f"Bottom Z#{i} (CH{ch_num:03d})", 
                    mode="lines", 
                    line=dict(color=bottom_colors[i-1], width=2)
                ))
            apply_industrial_style(fig2, "Temperature (°C)", y_range=[550, 650])
            st.plotly_chart(fig2, use_container_width=True)

        # 3. Dryer Temp (Scale: 150 - 350 °C)
        if show_g3:
            st.subheader("3. Dryer #1 & #2 (CH016 & CH017)")
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df["DateTime"], y=df["Dryer #1"], name="Dryer #1 (CH016)", mode="lines", line=dict(color="#FFA500", width=2)))
            fig3.add_trace(go.Scatter(x=df["DateTime"], y=df["Dryer #2"], name="Dryer #2 (CH017)", mode="lines", line=dict(color="#9ACD32", width=2)))
            apply_industrial_style(fig3, "Temperature (°C)", y_range=[150, 350])
            st.plotly_chart(fig3, use_container_width=True)

        # 4. O2 & N2 Flow Rate
        if show_g4:
            st.subheader("4. ppmO2 Entry/Exit & N2 Flow (CH015, CH018, CH019)")
            fig4 = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig4.add_trace(go.Scatter(x=df["DateTime"], y=df["ENTRANCE O2"], name="ENTRANCE O2 (CH019)", mode="lines", line=dict(color="#FF80FF", width=2)), secondary_y=False)
            fig4.add_trace(go.Scatter(x=df["DateTime"], y=df["EXIT O2"], name="EXIT O2 (CH015)", mode="lines", line=dict(color="#A52A2A", width=2)), secondary_y=False)
            fig4.add_trace(go.Scatter(x=df["DateTime"], y=df["N2 Flow"], name="N2 Flow (CH018/N2.1)", mode="lines", line=dict(color="#ADD8E6", width=2)), secondary_y=True)
            
            apply_industrial_style(fig4, "Oxygen Level (ppm)", is_dual_axis=True)
            fig4.update_layout(
                yaxis=dict(
                    title=dict(text="Oxygen Level (ppm) [0-200]", font=dict(color="#FFFFFF", size=12)),
                    range=[0, 200],
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.08)"
                ),
                yaxis2=dict(
                    title=dict(text="N2 Flow Rate (Free Scale)", font=dict(color="#ADD8E6", size=12)),
                    tickfont=dict(color="#ADD8E6", size=10),
                    showgrid=False,
                    overlaying="y",
                    side="right",
                    linecolor="#ADD8E6",
                    autorange=True
                )
            )
            st.plotly_chart(fig4, use_container_width=True)

        # 5. Dew Point (Scale: -100 ถึง 10 °Cdp)
        if show_g5:
            st.subheader("5. Dew point 'Cdp (CH020)")
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=df["DateTime"], 
                y=df["DEW POINT"], 
                name="Dew Point (CH020)", 
                mode="lines", 
                line=dict(color="#00ecff", width=2)
            ))
            apply_industrial_style(fig5, "Dew Point (°Cdp)", y_range=[-100, 10])
            st.plotly_chart(fig5, use_container_width=True)

        with st.expander("📋 ตรวจสอบและดาวน์โหลดตารางข้อมูลรวมเรียงตามเวลา"):
            st.dataframe(df)
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 ดาวน์โหลดข้อมูลที่รวมกันแล้วเป็น CSV",
                data=csv_data,
                file_name="combined_furnace_data.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")

else:
    st.info("👈 กรุณาเลือกอัปโหลดไฟล์ (.csv หรือ .xlsx) ที่เมนูด้านซ้าย สามารถเลือกอัปโหลดได้มากกว่า 1 ไฟล์")
