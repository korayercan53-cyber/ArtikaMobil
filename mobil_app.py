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
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/2666/2666505.png"
# ==========================================

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="ArtikaPro Bulut", page_icon="🏗️", layout="wide")

# --- CSS TASARIMI (TAMİR EDİLDİ) ---
st.markdown("""
<style>
    /* Üst Boşluk Ayarı (Yazının kesilmesini önlemek için margin artırıldı) */
    .block-container {
        padding-top: 2rem !important; 
        margin-top: 0rem !important;
    }
    
    /* Sekme Tasarımı */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 8px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B; color: white; }

    /* --- NORMAL MALZEME KARTI --- */
    .material-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        border-left: 5px solid #FF4B4B;
    }
    .card-code { 
        font-size: 11px; 
        color: #94a3b8; 
        font-weight: bold; 
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .card-title { 
        font-size: 16px; 
        font-weight: 700; 
        color: #1e293b; 
        margin-bottom: 10px; 
        line-height: 1.4; 
    }
    
    .card-details {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding-top: 8px;
        border-top: 1px dashed #f1f5f9;
        font-size: 11px;
        color: #475569;
    }
    .detail-item { 
        display: flex; 
        align-items: center; 
        gap: 4px; 
        background-color: #f8fafc; 
        padding: 4px 8px; 
        border-radius: 4px; 
    }
    .detail-val { font-weight: 700; color: #334155; }

    .card-price { 
        font-size: 18px; 
        font-weight: 800; 
        color: #dc2626; 
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        margin-top: 12px; 
        background-color: #fef2f2;
        padding: 10px;
        border-radius: 8px;
    }
    .card-unit { font-size: 12px; color: #64748b; font-weight: normal; }
    .card-desc { font-size: 11px; color: #94a3b8; margin-top: 8px; font-style: italic;}

    /* --- MAVİ BAŞLIK KARTI (KATEGORİLER İÇİN) --- */
    .header-card {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-weight: 800;
        font-size: 18px;
        text-align: center;
        border: 1px solid #bbdefb;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# --- YARDIMCI FONKSİYONLAR (GÜÇLENDİRİLDİ) ---
def clean_text(text):
    """None, nan, boşluk temizler."""
    if text is None: return ""
    s = str(text).strip()
    if s.lower() in ['nan', 'none', '', 'null']: return ""
    return s

def format_para(tutar):
    """
    Sayıyı TR formatına (1.234,56) çevirir.
    Gelen veri string olsa bile temizleyip sayıya çevirir.
    """
    if pd.isna(tutar): return "0,00"
    
    # Temizleme: Eğer string ise içindeki 'TL', boşluk vs temizle
    if isinstance(tutar, str):
        tutar = tutar.replace('TL', '').replace(' ', '').strip()
        if tutar == '': return "0,00"
        
    try:
        val = float(tutar)
        if val == 0: return "0,00"
        
        # Formatlama: {:,.2f} -> 1,234.56 yapar
        formatted = "{:,.2f}".format(val)
        
        # Yer değiştirme: 1,234.56 -> 1.234,56
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
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

    # --- HEADER (Yazı kesilmesini önleyen yeni stil) ---
    col1, col2 = st.columns([1, 10], gap="small")
    with col1:
        st.image(LOGO_URL, width=70)
    with col2:
        # line-height ve padding ile yazının kesilmesini engelliyoruz
        st.markdown("""
            <div style="padding-top: 5px;">
                <h1 style='margin: 0; padding: 0; font-size: 2.2rem; line-height: 1.2;'>ArtikaPro Bulut</h1>
                <p style='margin: 0; color: gray; font-size: 1rem;'>Saha ve Ofis Arasında Kesintisiz Veri Akışı</p>
            </div>
        """, unsafe_allow_html=True)

    # --- DOSYA TARAMA ---
    with st.spinner("Veriler yükleniyor..."):
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

    # --- SEKMELER ---
    tab_malzeme, tab_projeler = st.tabs(["🧱 Malzeme Kütüphanesi", "📋 Proje Teklifleri"])

    # ----------------------------------------
    # SEKME 1: MALZEME LİSTESİ
    # ----------------------------------------
    with tab_malzeme:
        if malzeme_dosyasi:
            tarih_ham = malzeme_dosyasi.get('modifiedTime', '')
            tarih_guzel = tarih_ham[:10] if tarih_ham else ""
            st.info(f"📂 Liste: **{malzeme_dosyasi['name']}** (Güncelleme: {tarih_guzel})")
            
            df = load_excel_as_df(service, malzeme_dosyasi['id'])
            
            if df is not None:
                search_term = st.text_input("🔍 Malzeme Ara:", placeholder="Ürün adı, kod veya kategori...")
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
                                # --- VERİLERİ TEMİZLE VE AL ---
                                ad = clean_text(row.get('Malzeme Adı'))
                                kod = clean_text(row.get('Kod'))
                                birim = clean_text(row.get('Birim'))
                                aciklama = clean_text(row.get('Açıklama'))
                                
                                # Fiyatları ve Para Birimini Al
                                f_malzeme = row.get('Malzeme Birim Fiyat', 0)
                                f_iscilik = row.get('İşçilik Birim Fiyat', 0)
                                f_toplam = row.get('Toplam Birim Fiyat', 0)
                                para_birimi = clean_text(row.get('Para Birimi'))
                                if not para_birimi: para_birimi = "TL"

                                # --- BAŞLIK SATIRI TESPİTİ ---
                                # Eğer 'Malzeme Birim Fiyat' boşsa veya 0 ise ve 'Birim' boşsa BAŞLIKTIR
                                is_header = False
                                try:
                                    tutar_kontrol = float(f_toplam)
                                except:
                                    tutar_kontrol = 0
                                
                                if tutar_kontrol == 0 and birim == "":
                                    is_header = True
                                
                                # --- KART BASIMI ---
                                if is_header:
                                    # MAVİ BAŞLIK (Sadece isim yazar, 'None' yazmaz)
                                    if ad: # Ad boş değilse bas
                                        st.markdown(f"""
                                        <div class="header-card">
                                            {ad}
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    # NORMAL KART
                                    birim_str = f"/ {birim}" if birim else ""
                                    kod_html = f'<div class="card-code">#{kod}</div>' if kod else ""
                                    
                                    # Formatlanmış Fiyatlar (1.250,00 Şeklinde)
                                    str_malz = format_para(f_malzeme)
                                    str_isc = format_para(f_iscilik)
                                    str_top = format_para(f_toplam)

                                    html_content = f"""
                                    <div class="material-card">
                                        {kod_html}
                                        <div class="card-title">{ad}</div>
                                        
                                        <div class="card-details">
                                            <div class="detail-item">🧱 Malz: <span class="detail-val">{str_malz} {para_birimi}</span></div>
                                            <div class="detail-item">👷 İşç: <span class="detail-val">{str_isc} {para_birimi}</span></div>
                                        </div>
                                        
                                        <div class="card-price">
                                            {str_top} {para_birimi}
                                            <span class="card-unit">{birim_str}</span>
                                        </div>
                                        
                                        <div class="card-desc">{aciklama}</div>
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
            st.info("Henüz proje teklifi bulunamadı.")

if __name__ == "__main__":
    main()