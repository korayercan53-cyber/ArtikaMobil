import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import numpy as np

# ==========================================
# AYARLAR
# ==========================================
DRIVE_KLASOR_ID = "1mTx-wY_D2W1QGgAV7_xYJMu4UQ3cYybY" 
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/2666/2666505.png"
# ==========================================

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="ArtikaPro Bulut", page_icon="🏗️", layout="wide")

# --- CSS TASARIMI ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem !important; margin-top: 0rem !important; }
    header {visibility: hidden;} 
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 8px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B; color: white; }

    /* KART TASARIMI */
    .material-card {
        background-color: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; border-left: 5px solid #FF4B4B;
    }
    .card-code { font-size: 11px; color: #94a3b8; font-weight: bold; margin-bottom: 4px; }
    .card-title { font-size: 16px; font-weight: 700; color: #1e293b; margin-bottom: 10px; line-height: 1.4; }
    .card-details { display: flex; gap: 8px; padding-top: 8px; border-top: 1px dashed #f1f5f9; font-size: 11px; color: #475569; }
    .detail-item { background-color: #f8fafc; padding: 4px 8px; border-radius: 4px; }
    .detail-val { font-weight: 700; color: #334155; }
    .card-price { 
        font-size: 18px; font-weight: 800; color: #dc2626; display: flex; justify-content: space-between; 
        align-items: center; margin-top: 12px; background-color: #fef2f2; padding: 10px; border-radius: 8px;
    }
    .card-unit { font-size: 12px; color: #64748b; font-weight: normal; }
    .card-desc { font-size: 11px; color: #94a3b8; margin-top: 8px; font-style: italic;}
    .header-card {
        background-color: #e3f2fd; color: #1565c0; padding: 15px; border-radius: 8px; margin-bottom: 20px;
        font-weight: 800; font-size: 18px; text-align: center; border: 1px solid #bbdefb;
        text-transform: uppercase; letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def clean_text(text):
    if text is None: return ""
    if pd.isna(text): return ""
    s = str(text).strip()
    if s.lower() in ['nan', 'none', '', 'null', 'nat']: return ""
    return s

def format_para_str(tutar):
    if pd.isna(tutar): return "0,00"
    try:
        val = float(tutar)
        return "{:,.2f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

# --- TABLE STYLER (Çözüm Fonksiyonu) ---
# --- TABLE STYLER (Çözüm Fonksiyonu) ---
def apply_table_style(df):
    df = df.copy()
    df = df.dropna(how='all')
    
    # 1. Sayısal Sütunları Belirle
    keywords = ["fiyat", "tutar", "toplam", "meblağ", "b.f", "iskonto", "kdv", "hakediş"]
    num_cols = []
    
    for col in df.columns:
        if any(k in str(col).lower() for k in keywords) or pd.api.types.is_numeric_dtype(df[col]):
            num_cols.append(col)
            # Veriyi sayıya çevir (Float)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0)
    
    num_cols = list(set(num_cols))

    # 2. Metin Sütunlarını Temizle (None, nan yazılarını sil)
    other_cols = [c for c in df.columns if c not in num_cols]
    for col in other_cols:
        df[col] = df[col].fillna("")
        df[col] = df[col].astype(str)
        df[col] = df[col].replace(r'(?i)^(nan|none|null)$', "", regex=True)
        df[col] = df[col].str.strip()

    # 3. Formatlayıcı (Görünmez 0 ve Binlik Ayıracı)
    def tr_formatter(x):
        if x == 0: return ""
        try: return "{:,.2f}".format(x).replace(",", "X").replace(".", ",").replace("X", ".")
        except: return ""

    # 4. Başlık Satırı ve Kırmızı Teklif Renklendirme
    def highlight_cells(row):
        styles = [''] * len(row)
        val = row.get('Birim', "")
        
        # A. Başlık Satırı Kontrolü (Mavi)
        if str(val).strip() == "":
            return ['background-color: #dbeafe; color: #1e3a8a; font-weight: bold'] * len(row)
        
        # B. Kırmızı Teklif Kontrolü (Tersten Kar Hesabı ile Kıyaslama)
        teklif_col = next((c for c in row.index if 'toplam teklif' in str(c).lower() or 'teklif tutarı' in str(c).lower()), None)
        maliyet_col = next((c for c in row.index if ('toplam maliyet' in str(c).lower() or 'maliyet' in str(c).lower()) and 'teklif' not in str(c).lower()), None)
        kar_col = next((c for c in row.index if 'kar' in str(c).lower()), None)
        
        if teklif_col and maliyet_col and kar_col:
            try:
                maliyet = float(row[maliyet_col])
                teklif = float(row[teklif_col])
                kar_str = str(row[kar_col]).replace('%', '').replace(',', '.')
                kar = float(kar_str)
                
                beklenen_teklif = maliyet * (1 + kar / 100)
                
                # Eğer matematik uymuyorsa (1 TL'den fazla fark varsa elle girilmiştir) yazıyı kırmızı yap
                if abs(beklenen_teklif - teklif) > 1.0:
                    idx = row.index.get_loc(teklif_col)
                    styles[idx] = 'color: #ef4444; font-weight: bold;'
            except:
                pass
                
        return styles

    styler = df.style.apply(highlight_cells, axis=1)

    # 5. Format ve Sağa Yaslama
    if num_cols:
        styler = styler.format(tr_formatter, subset=num_cols)
        styler = styler.set_properties(subset=num_cols, **{'text-align': 'right'})

    return styler

# --- DRIVE BAĞLANTISI ---
@st.cache_resource
def get_drive_service():
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    if "gcp_service_account" in st.secrets:
        try:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            st.error(f"Secrets hatası: {e}")
            return None
    st.error("Kimlik doğrulama anahtarı bulunamadı!")
    return None

@st.cache_data(ttl=600)
def list_files_in_folder(_service, folder_id): 
    query = f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed = false"
    try:
        results = _service.files().list(q=query, pageSize=50, fields="files(id, name, modifiedTime)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Klasör okuma hatası: {e}")
        return []

def load_excel_as_df(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file_stream.seek(0)
        df = pd.read_excel(file_stream)
        df.dropna(how='all', inplace=True)
        return df
    except Exception as e:
        st.error(f"Dosya indirme hatası: {e}")
        return None

def download_excel_bytes(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file_stream.getvalue()
    except Exception as e:
        st.error(f"Dosya indirme hatası: {e}")
        return None

# --- ANA PROGRAM ---
def main():
    service = get_drive_service()
    if not service: return

    with st.sidebar:
        st.image(LOGO_URL, width=50)
        st.write("---")
        if st.button("🔄 Önbelleği Temizle"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("""
        <div style="padding-top: 0px; padding-bottom: 10px;">
            <h1 style='margin: 0; padding: 0; font-size: 2.0rem; line-height: 1.2;'>ArtikaPro Bulut</h1>
            <p style='margin: 0; color: gray; font-size: 0.9rem;'>Saha ve Ofis Arasında Kesintisiz Veri Akışı</p>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Dosyalar taranıyor..."):
        files = list_files_in_folder(service, DRIVE_KLASOR_ID)
    
    if not files:
        st.warning("Klasörde Excel dosyası bulunamadı.")
        return

    malzeme_adaylari = [f for f in files if "malzeme" in f['name'].lower()]
    teklif_dosyalari = [f for f in files if "teklif" in f['name'].lower()]
    
    if malzeme_adaylari:
        malzeme_adaylari.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
        malzeme_dosyasi = malzeme_adaylari[0]
    else:
        malzeme_dosyasi = None

    tab_malzeme, tab_projeler = st.tabs(["🧱 Malzeme Kütüphanesi", "📋 Proje Teklifleri"])

    # ----------------------------------------
    # SEKME 1: MALZEME
    # ----------------------------------------
    with tab_malzeme:
        if malzeme_dosyasi:
            df = load_excel_as_df(service, malzeme_dosyasi['id'])
            
            if df is not None:
                if 'Malzeme Adı' in df.columns:
                     df = df[df['Malzeme Adı'].notna()]
                     df = df[df['Malzeme Adı'].astype(str).str.strip() != ""]

                search_term = st.text_input("🔍 Malzeme Ara:", placeholder="Ara...")
                if search_term:
                     df = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)]

                view = st.radio("Görünüm:", ["Kart Görünümü", "Liste Görünümü"], horizontal=True, label_visibility="collapsed")

                if view == "Kart Görünümü":
                    if df.empty:
                        st.warning("Sonuç yok.")
                    else:
                        cols = st.columns(3) 
                        for index, row in df.iterrows():
                            with cols[index % 3]:
                                ad = clean_text(row.get('Malzeme Adı'))
                                kod = clean_text(row.get('Kod'))
                                birim = clean_text(row.get('Birim'))
                                aciklama = clean_text(row.get('Açıklama'))
                                f_malzeme = row.get('Malzeme Birim Fiyat', 0)
                                f_iscilik = row.get('İşçilik Birim Fiyat', 0)
                                f_toplam = row.get('Toplam Birim Fiyat', 0)
                                para_birimi = clean_text(row.get('Para Birimi')) or "TL"
                                is_header = False
                                try: tutar_val = float(f_toplam)
                                except: tutar_val = 0
                                if tutar_val == 0 and birim == "": is_header = True
                                
                                if is_header:
                                    if ad: st.markdown(f'<div class="header-card">{ad}</div>', unsafe_allow_html=True)
                                else:
                                    birim_str = f"/ {birim}" if birim else ""
                                    kod_html = f'<div class="card-code">#{kod}</div>' if kod else ""
                                    str_malz = format_para_str(f_malzeme)
                                    str_isc = format_para_str(f_iscilik)
                                    str_top = format_para_str(f_toplam)
                                    html_content = f"""<div class="material-card">{kod_html}<div class="card-title">{ad}</div><div class="card-details"><div class="detail-item">🧱 Malz: <span class="detail-val">{str_malz} {para_birimi}</span></div><div class="detail-item">👷 İşç: <span class="detail-val">{str_isc} {para_birimi}</span></div></div><div class="card-price">{str_top} {para_birimi}<span class="card-unit">{birim_str}</span></div><div class="card-desc">{aciklama}</div></div>"""
                                    st.markdown(html_content, unsafe_allow_html=True)
                else:
                    rename_map = {"Malzeme Birim Fiyat": "Malzeme B.F", "İşçilik Birim Fiyat": "İşçilik B.F", "Toplam Birim Fiyat": "Toplam B.F", "Para Birimi": "P.B", "Tanım": "Tanım", "Poz No": "Poz No", "Birim": "Birim"}
                    df_display = df.rename(columns=rename_map)
                    
                    styled_df = apply_table_style(df_display)
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("Malzeme listesi yok.")

    # ----------------------------------------
    # SEKME 2: PROJELER
    # ----------------------------------------
    with tab_projeler:
        if teklif_dosyalari:
            isimler = [f['name'] for f in teklif_dosyalari]
            secim = st.selectbox("Proje Seç:", isimler)
            
            secilen_dosya = next(f for f in teklif_dosyalari if f['name'] == secim)
            
            if secilen_dosya:
                with st.spinner("Proje detayları yükleniyor..."):
                    file_bytes = download_excel_bytes(service, secilen_dosya['id'])
                    if file_bytes:
                        xls_proj = pd.ExcelFile(io.BytesIO(file_bytes))
                        sheet_names = xls_proj.sheet_names
                        
                        if "İcmal Tablosu" in sheet_names:
                            st.subheader("📊 İcmal Özeti")
                            df_icmal = pd.read_excel(xls_proj, "İcmal Tablosu")
                            
                            styled_icmal = apply_table_style(df_icmal)
                            st.dataframe(styled_icmal, use_container_width=True)
                            st.divider()
                        
                        detay_sayfalari = [s for s in sheet_names if s != "İcmal Tablosu"]
                        if detay_sayfalari:
                            sayfa = st.pills("Detay Sayfası:", detay_sayfalari, default=detay_sayfalari[0], key="pills_detay")
                            if sayfa:
                                df_detay = pd.read_excel(xls_proj, sayfa)
                                
                                styled_detay = apply_table_style(df_detay)
                                st.dataframe(styled_detay, use_container_width=True)
        else:
            st.info("Proje teklifi yok.")

if __name__ == "__main__":
    main()