import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# ==========================================
# AYARLAR
# ==========================================
DRIVE_KLASOR_ID = "1mTx-wY_D2W1QGgAV7_xYJMu4UQ3cYybY" 

# Logo Linki (Daha güvenilir bir sunucudan)
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/2666/2666505.png"
# ==========================================

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="ArtikaPro Bulut", page_icon="🏗️", layout="wide")

# --- CSS TASARIMI (BOŞLUK SİLME EKLENDİ) ---
st.markdown("""
<style>
    /* 1. SAYFA ÜSTÜNDEKİ BOŞLUĞU SİLME KODU */
    .block-container {
        padding-top: 1rem !important; /* Üst boşluğu 1 birime düşür */
        padding-bottom: 0rem !important;
        margin-top: 0rem !important;
    }
    header {visibility: hidden;} /* Üstteki renkli ince çizgiyi gizle (isteğe bağlı) */

    /* Sekme Tasarımı */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 8px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B; color: white; }

    /* KART TASARIMI */
    .material-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        border-left: 5px solid #FF4B4B;
        transition: transform 0.2s;
    }
    .material-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
    }
    .card-code { font-size: 11px; color: #94a3b8; font-weight: bold; letter-spacing: 0.5px; }
    .card-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 5px 0; line-height: 1.3; }
    
    /* Detay Satırı */
    .card-details {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px dashed #f1f5f9;
        font-size: 12px;
        color: #475569;
    }
    .detail-item { display: flex; align-items: center; gap: 4px; background-color: #f8fafc; padding: 2px 6px; border-radius: 4px; }
    .detail-val { font-weight: 700; color: #334155; }

    /* Fiyat Alanı */
    .card-price { 
        font-size: 18px; 
        font-weight: 800; 
        color: #dc2626; 
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        margin-top: 12px; 
        background-color: #fef2f2;
        padding: 8px;
        border-radius: 6px;
    }
    .card-unit { font-size: 12px; color: #64748b; font-weight: normal; }
    .card-desc { font-size: 12px; color: #94a3b8; margin-top: 8px; font-style: italic;}
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR ---
def tr_fmt(tutar):
    if pd.isna(tutar): return "0,00"
    try:
        val = float(tutar)
        return "{:,.2f}".format(val).replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

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

def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed = false"
    try:
        results = service.files().list(q=query, pageSize=50, fields="files(id, name, modifiedTime)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Klasör okuma hatası: {e}")
        return []

@st.cache_data(ttl=600)
def load_excel_as_df(_service, file_id):
    try:
        request = _service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file_stream.seek(0)
        return pd.read_excel(file_stream)
    except Exception as e:
        st.error(f"Dosya indirme hatası: {e}")
        return None

def load_excel_file_obj(_service, file_id):
    try:
        request = _service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        file_stream.seek(0)
        return pd.ExcelFile(file_stream)
    except Exception as e:
        st.error(f"Dosya indirme hatası: {e}")
        return None

# --- ANA PROGRAM ---
def main():
    service = get_drive_service()
    if not service: return

    # --- LOGO VE BAŞLIK (KLASİK VE GARANTİ YÖNTEM) ---
    # col1: Logo (Küçük), col2: Başlık (Geniş)
    # gap="small" ile aradaki boşluğu azaltıyoruz.
    col1, col2 = st.columns([1, 10], gap="small") 
    
    with col1:
        # st.image Streamlit'in kendi fonksiyonudur, en garantisidir.
        st.image(LOGO_URL, width=70) 
        
    with col2:
        # Başlığı ve alt başlığı HTML ile basarak üstteki boşlukları sıfırlıyoruz
        st.markdown("""
            <h1 style='margin-top: 0; padding-top: 0; font-size: 2.5rem;'>ArtikaPro Bulut</h1>
            <p style='margin-top: -10px; color: gray;'>Saha ve Ofis Arasında Kesintisiz Veri Akışı</p>
        """, unsafe_allow_html=True)

    # --- DOSYALARI ÇEK ---
    with st.spinner("Dosyalar taranıyor..."):
        files = list_files_in_folder(service, DRIVE_KLASOR_ID)
    
    if not files:
        st.warning(f"Bu klasörde Excel dosyası bulunamadı.")
        return

    malzeme_adaylari = [f for f in files if "malzeme" in f['name'].lower()]
    teklif_dosyalari = [f for f in files if "teklif" in f['name'].lower()]
    
    if malzeme_adaylari:
        malzeme_adaylari.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
        malzeme_dosyasi = malzeme_adaylari[0]
    else:
        malzeme_dosyasi = None

    # --- SEKMELER ---
    tab_malzeme, tab_projeler = st.tabs(["🧱 Malzeme Kütüphanesi", "📋 Proje Teklifleri"])

    # ----------------------------------------
    # SEKME 1: MALZEME
    # ----------------------------------------
    with tab_malzeme:
        if malzeme_dosyasi:
            tarih_ham = malzeme_dosyasi.get('modifiedTime', '')
            tarih_guzel = tarih_ham[:10] if tarih_ham else ""
            
            st.info(f"📂 Liste: **{malzeme_dosyasi['name']}** (Güncelleme: {tarih_guzel})")
            
            df = load_excel_as_df(service, malzeme_dosyasi['id'])
            
            if df is not None:
                search_term = st.text_input("🔍 Malzeme Ara:", placeholder="Profil, Alçı, Boya...")
                if search_term:
                     df = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)]

                view = st.radio("Görünüm:", ["Kart Görünümü", "Liste Görünümü"], horizontal=True, label_visibility="collapsed")

                if view == "Kart Görünümü":
                    if df.empty:
                        st.warning("Sonuç bulunamadı.")
                    else:
                        cols = st.columns(3) 
                        for index, row in df.iterrows():
                            with cols[index % 3]:
                                # Verileri Çek
                                ad = row.get('Malzeme Adı', '-')
                                kod = row.get('Kod', '')
                                f_malzeme = row.get('Malzeme Birim Fiyat', 0)
                                f_iscilik = row.get('İşçilik Birim Fiyat', 0)
                                f_toplam = row.get('Toplam Birim Fiyat', 0)
                                birim = row.get('Birim', 'Adet')
                                
                                para_birimi = row.get('Para Birimi', 'TL')
                                if pd.isna(para_birimi): para_birimi = "TL"

                                aciklama = row.get('Açıklama', '')

                                html_content = f"""
                                <div class="material-card">
                                    <div class="card-code">#{kod}</div>
                                    <div class="card-title">{ad}</div>
                                    <div class="card-details">
                                        <div class="detail-item">🧱 Malz: <span class="detail-val">{tr_fmt(f_malzeme)} {para_birimi}</span></div>
                                        <div class="detail-item">👷 İşç: <span class="detail-val">{tr_fmt(f_iscilik)} {para_birimi}</span></div>
                                    </div>
                                    <div class="card-price">
                                        {tr_fmt(f_toplam)} {para_birimi}
                                        <span class="card-unit">/ {birim}</span>
                                    </div>
                                    <div class="card-desc">{aciklama if pd.notna(aciklama) else ''}</div>
                                </div>
                                """
                                st.markdown(html_content, unsafe_allow_html=True)
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz yüklenmiş bir malzeme listesi yok.")

    # ----------------------------------------
    # SEKME 2: PROJELER
    # ----------------------------------------
    with tab_projeler:
        if teklif_dosyalari:
            isimler = [f['name'] for f in teklif_dosyalari]
            secim = st.selectbox("İncelenecek Proje:", isimler)
            
            secilen_dosya = next(f for f in teklif_dosyalari if f['name'] == secim)
            
            if secilen_dosya:
                with st.spinner("Proje açılıyor..."):
                    xls_proj = load_excel_file_obj(service, secilen_dosya['id'])
                    
                    if xls_proj:
                        sheet_names = xls_proj.sheet_names
                        if "İcmal Tablosu" in sheet_names:
                            st.subheader("📊 İcmal Özeti")
                            st.dataframe(pd.read_excel(xls_proj, "İcmal Tablosu"), use_container_width=True)
                            st.divider()
                        
                        detay_sayfalari = [s for s in sheet_names if s != "İcmal Tablosu"]
                        if detay_sayfalari:
                            sayfa = st.pills("Detay Sayfası:", detay_sayfalari, default=detay_sayfalari[0])
                            if sayfa:
                                st.dataframe(pd.read_excel(xls_proj, sayfa), use_container_width=True)
        else:
            st.info("Bu klasörde isminde 'Teklif' geçen dosya bulunamadı.")

if __name__ == "__main__":
    main()