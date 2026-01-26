import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os

st.set_page_config(page_title="ArtikaPro Mobil", page_icon="🏗️", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b; color: white; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# AYARLAR (ID'Yİ BURAYA YAPIŞTIR)
# ==========================================
DRIVE_KLASOR_ID = "1mTx-wY_D2W1QGgAV7_xYJMu4UQ3cYybY" 
# ==========================================

# --- DRIVE BAĞLANTISI ---
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
    # ROBOT ARTIK DOĞRUDAN O KLASÖRE BAKACAK
    query = f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed = false"
    try:
        results = service.files().list(q=query, pageSize=50, fields="files(id, name, modifiedTime)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Klasör okuma hatası: {e}. Lütfen Klasör ID'sinin doğru olduğundan emin olun.")
        return []

def load_excel_by_id(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
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

# --- ARAYÜZ (MAIN) ---
def main():
    st.title("🏗️ ArtikaPro Bulut")
    
    service = get_drive_service()
    if not service: return

    # Belirtilen klasördeki dosyaları çek
    files = list_files_in_folder(service, DRIVE_KLASOR_ID)
    
    if not files:
        st.warning(f"Bu klasörde (ID: {DRIVE_KLASOR_ID}) hiç Excel dosyası bulunamadı.")
        return

    # --- AKILLI FİLTRELEME ---
    # 1. Malzeme dosyalarını bul
    malzeme_adaylari = [f for f in files if "malzeme_listesi" in f['name'].lower()]
    
    # Eğer birden fazla varsa, en son değiştirileni (en yeniyi) seç
    if malzeme_adaylari:
        # Tarihe göre sırala (Yeniden eskiye)
        malzeme_adaylari.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
        malzeme_dosyasi = malzeme_adaylari[0] # En tepedeki en yenisidir
    else:
        malzeme_dosyasi = None

    # 2. Teklif dosyalarını bul
    teklif_dosyalari = [f for f in files if "teklif" in f['name'].lower()]

    tab_malzeme, tab_projeler = st.tabs(["🧱 Malzeme Kütüphanesi", "📋 Proje Teklifleri"])

    # 1. SEKME: MALZEME
    with tab_malzeme:
        if malzeme_dosyasi:
            # Tarihi kullanıcı dostu formata çevirip gösterelim
            tarih_ham = malzeme_dosyasi.get('modifiedTime', '')
            tarih_guzel = tarih_ham[:16].replace('T', ' ') if tarih_ham else ""
            
            st.caption(f"📅 Son Güncelleme: {tarih_guzel} | Dosya: {malzeme_dosyasi['name']}")
            
            xls = load_excel_by_id(service, malzeme_dosyasi['id'])
            if xls:
                df = pd.read_excel(xls)
                
                # Arama Kutusu
                search_term = st.text_input("🔍 Malzeme Ara:", "")
                if search_term:
                    df = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)]
                
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz yüklenmiş bir malzeme listesi yok.")

    # 2. SEKME: PROJELER
    with tab_projeler:
        if teklif_dosyalari:
            isimler = [f['name'] for f in teklif_dosyalari]
            secim = st.selectbox("İncelenecek Proje:", isimler)
            
            secilen_dosya = next(f for f in teklif_dosyalari if f['name'] == secim)
            
            if secilen_dosya:
                with st.spinner("Proje açılıyor..."):
                    xls_proj = load_excel_by_id(service, secilen_dosya['id'])
                    if xls_proj:
                        sheet_names = xls_proj.sheet_names
                        if "İcmal Tablosu" in sheet_names:
                            st.subheader("📊 İcmal Özeti")
                            st.dataframe(pd.read_excel(xls_proj, "İcmal Tablosu"), use_container_width=True)
                            st.divider()
                        
                        detay_sayfalari = [s for s in sheet_names if s != "İcmal Tablosu"]
                        if detay_sayfalari:
                            sayfa = st.radio("Detay Sayfası:", detay_sayfalari, horizontal=True)
                            st.dataframe(pd.read_excel(xls_proj, sayfa), use_container_width=True)
        else:
            st.info("Bu klasörde isminde 'Teklif' geçen dosya bulunamadı.")

if __name__ == "__main__":
    main()