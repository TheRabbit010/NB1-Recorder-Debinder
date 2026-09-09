import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import io

# 1. ตั้งค่า Page Config
st.set_page_config(
    page_title="Recorder NB1 Debinder",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. บังคับ Dark Mode CSS
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

# 3. ชื่อโปรแกรม
st.title("🏭 Recorder NB1 Debinder")

# 4. ฟังก์ชันอ่านไฟล์ทีละบรรทัดและดึงคอลัมน์ตรงๆ
def parse_single_file(uploaded_file):
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    
    # ลอง Decode หาภาษาที่ถูกต้อง
    text_content = None
    for enc in ['cp932', 'shift_jis', 'utf-8', 'tis-620', 'latin1']:
        try:
            text_content = raw_bytes.decode(enc)
            break
        except Exception:
            continue
            
    if text_content is None:
        text_content = raw_bytes.decode('utf-8', errors='ignore')

    lines = text_content.splitlines()
    
    parsed_rows = []
    
    for line in lines:
        line_str = line.strip()
        # สนใจเฉพาะบรรทัดที่ขึ้นต้นด้วยปี ค.ศ. (เช่น 2026/07/13)
        if line_str.startswith("20") and "," in line_str:
            parts = [p.strip() for p in line_str.split(",")]
            
            # ต้องมีคอลัมน์อย่างน้อย 17 คอลัมน์ (Index 0 ถึง 16)
            if len(parts) >= 17:
                try:
                    dt_val = parts[0]
                    z1 = float(parts[4])   # TH_CH1Ave.
                    z2 = float(parts[7])   # TH_CH2Ave.
                    z3 = float(parts[10])  # TH_CH3Ave.
                    z4 = float(parts[13])  # TH_CH4Ave.
                    comb = float(parts[16]) # TH_CH5Ave.
                    
                    parsed_rows.append({
                        "DateTime": dt_val,
                        "Zone #1": z1,
                        "Zone #2": z2,
                        "Zone #3": z3,
                        "Zone #4": z4,
                        "Combustion Air Temp": comb
                    })
                except ValueError:
                    continue

    if not parsed_rows:
        return pd.DataFrame()

    df = pd.DataFrame(parsed_rows)
    df["DateTime"] = pd.to_datetime(df["DateTime"], errors="coerce")
    return df.dropna(subset=["DateTime"]).reset_index(drop=True)

def process_multiple_files(uploaded_files):
    combined_dfs = []
    for file in uploaded_files:
        df_single = parse_single_file(file)
        if not df_single.empty:
            combined_dfs.append(df_single)
            
    if not combined_dfs:
        return pd.DataFrame()

    full_df = pd.concat(combined_dfs, ignore_index=True)
    full_df = full_df.drop_duplicates(subset=["DateTime"]).sort_values("DateTime").reset_index(drop=True)
    return full_df

# 5. เมนู Sidebar
st.sidebar.header("📁 เมนูอัปโหลดข้อมูล")

if st.sidebar.button("🧹 เคลียร์ข้อมูลไฟล์เก่าทั้งหมด"):
    st.cache_data.clear()
    st.rerun()

uploaded_files = st.sidebar.file_uploader(
    "อัปโหลดไฟล์ CSV (.csv) ได้มากกว่า 1 ไฟล์", 
    type=["csv"],
    accept_multiple_files=True
)

# 6. แสดงผลกราฟ
if uploaded_files:
    raw_df = process_multiple_files(uploaded_files)
    
    if raw_df.empty:
        st.error("⚠️ ไม่สามารถอ่านข้อมูลจากไฟล์ที่อัปโหลดได้ กรุณาตรวจสอบว่าเป็นไฟล์ CSV จากเครื่อง Recorder หรือไม่")
    else:
        st.sidebar.success(f"รวมข้อมูลสำเร็จ {len(uploaded_files)} ไฟล์ ({len(raw_df)} แถว)")

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

        # สร้างกราฟ 2 แกน Y
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        zone_colors = ["#FF0000", "#008000", "#0000FF", "#8A2BE2"]

        # 1. Zone #1 - #4 (แกน Y ซ้ายมือ)
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

        # 2. Combustion Air Temp (แกน Y ขวามือ)
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
            # แกน X = Date & Time
            xaxis=dict(
                title=dict(text="Date & Time", font=dict(color="#FFFFFF", size=12)),
                tickfont=dict(color="#CCCCCC", size=10),
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="#555555",
                type="date"
            ),
            # แกน Y ซ้าย = Zone Temperature (°C)
            yaxis=dict(
                title=dict(text="Zone Temperature (°C)", font=dict(color="#FFFFFF", size=12)),
                tickfont=dict(color="#CCCCCC", size=10),
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                zeroline=False,
                linecolor="#555555",
                range=[0, 400]
            ),
            # แกน Y ขวา = Combustion Air Temp (°C)
            yaxis2=dict(
                title=dict(text="Combustion Air Temp (°C)", font=dict(color="#FFA500", size=12)),
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

else:
    st.info("👈 กรุณาเลือกอัปโหลดไฟล์ (.csv) ที่เมนูด้านซ้าย สามารถเลือกอัปโหลดได้มากกว่า 1 ไฟล์")
