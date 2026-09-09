# 2. ฟังก์ชันอ่านไฟล์อย่างปลอดภัย (แก้ไขเรียบร้อย)
def read_excel_safe(uploaded_file):
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith('.csv'):
        encodings = ['cp932', 'shift_jis', 'utf-8', 'utf-8-sig', 'tis-620', 'latin1']
        for enc in encodings:
            try:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, header=None, low_memory=False, encoding=enc)
            except Exception:
                continue
        # กรณีล้มเหลวทุก encoding ให้ข้ามอักขระแปลกปลอมด้วย encoding_errors='ignore'
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, header=None, low_memory=False, encoding='utf-8', encoding_errors='ignore')
    
    try:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file, header=None, engine='openpyxl')
    except Exception:
        try:
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, header=None, engine='xlrd')
        except Exception:
            uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, header=None)
