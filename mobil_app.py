import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="ArtikaPro Bulut", page_icon="🏗️", layout="wide")

# ==========================================
# 1. TASARIM KODLARI (Sadece Burası Yeni)
# ==========================================
st.markdown("""
<style>
    /* Sekme Tasarımı */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 8px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B; color: white; }

    /* KART TASARIMI (Mobil Uyumlu) */
    .material-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        border-left: 5px solid #FF4B4B;
    }
    .card-code { font-size: 11px; color: #94a3b8; font-weight: bold; letter-spacing: 0.5px; }
    .card-title { font-size: 16px; font-weight: 700; color: #1e293b; margin: 5px 0; line-height: 1.3; }
    .card-price { font-size: 18px; font-weight: 800; color: #dc2626; display: flex; align-items: center; justify-content: space-between; margin-top: 10px; }
    .card-unit { font-size: 12px; color: #64748b; font-weight: normal; }
    .card-desc { font-size: 12px; color: #64748b; margin-top: 8px; border-top: 1px solid #f1f5f9; padding-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# AYARLAR (Senin ID'n)
# ==========================================
DRIVE_KLASOR_ID = "1mTx-wY_D2W1QGgAV7_xYJMu4UQ3cYybY" 
# ==========================================

# --- DRIVE BAĞLANTISI (Senin Çalışan Fonksiyonların) ---
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

# --- KRİTİK DEĞİŞİKLİK: Caching hatasını önlemek için ExcelFile yerine DataFrame döndürüyoruz ---
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
        # Burayı değiştirdik: Direkt okuyup tablo olarak döndürüyoruz (Hatayı çözen kısım)
        return pd.read_excel(file_stream)
    except Exception as e:
        st.error(f"Dosya indirme hatası: {e}")
        return None

# Projeler için (Sayfalı okuma gerektiği için ExcelFile dönmeli, buna cache koymuyoruz)
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


# --- ARAYÜZ (MAIN) ---
def main():
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=60)
    with col_title:
        st.title("ArtikaPro Bulut")
        st.caption("Saha ve Ofis Arasında Kesintisiz Veri Akışı")
    
    service = get_drive_service()
    if not service: return

    with st.spinner("Dosyalar taranıyor..."):
        files = list_files_in_folder(service, DRIVE_KLASOR_ID)
    
    if not files:
        st.warning(f"Bu klasörde Excel dosyası bulunamadı.")
        return

    # Dosya Ayrıştırma
    malzeme_adaylari = [f for f in files if "malzeme" in f['name'].lower()]
    teklif_dosyalari = [f for f in files if "teklif" in f['name'].lower()]
    
    # En güncel malzeme dosyasını bul
    if malzeme_adaylari:
        malzeme_adaylari.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
        malzeme_dosyasi = malzeme_adaylari[0]
    else:
        malzeme_dosyasi = None

    # --- SEKMELER ---
    tab_malzeme, tab_projeler = st.tabs(["🧱 Malzeme Kütüphanesi", "📋 Proje Teklifleri"])

    # 1. SEKME: MALZEME (KART GÖRÜNÜMÜ EKLENDİ)
    with tab_malzeme:
        if malzeme_dosyasi:
            tarih_ham = malzeme_dosyasi.get('modifiedTime', '')
            tarih_guzel = tarih_ham[:10] if tarih_ham else ""
            
            st.info(f"📂 Liste: **{malzeme_dosyasi['name']}** (Tarih: {tarih_guzel})")
            
            # Veriyi yükle
            df = load_excel_as_df(service, malzeme_dosyasi['id'])
            
            if df is not None:
                # Arama
                search_term = st.text_input("🔍 Malzeme Ara:", placeholder="Profil, Alçı, Boya...")
                if search_term:
                     df = df[df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)]

                # GÖRÜNÜM SEÇİMİ (YENİ)
                view = st.radio("Görünüm:", ["Kart Görünümü", "Liste Görünümü"], horizontal=True, label_visibility="collapsed")

                if view == "Kart Görünümü":
                    if df.empty:
                        st.warning("Sonuç bulunamadı.")
                    else:
                        cols = st.columns(3) # Mobilde tekli, PC'de 3'lü
                        for index, row in df.iterrows():
                            with cols[index % 3]:
                                # Güvenli Veri Çekme
                                ad = row.get('Malzeme Adı', '-')
                                kod = row.get('Kod', '')
                                fiyat = row.get('Toplam Birim Fiyat', 0)
                                birim = row.get('Birim', 'Adet')
                                aciklama = row.get('Açıklama', '')

                                # Kart HTML
                                st.markdown(f"""
                                <div class="material-card">
                                    <div class="card-code">#{kod}</div>
                                    <div class="card-title">{ad}</div>
                                    <div class="card-price">{fiyat:,.2f} ₺ <span class="card-unit">/ {birim}</span></div>
                                    <div class="card-desc">{aciklama if pd.notna(aciklama) else ''}</div>
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    # Klasik Liste
                    st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Henüz yüklenmiş bir malzeme listesi yok.")

    # 2. SEKME: PROJELER (Senin Kodunun Aynısı)
    with tab_projeler:
        if teklif_dosyalari:
            isimler = [f['name'] for f in teklif_dosyalari]
            secim = st.selectbox("İncelenecek Proje:", isimler)
            
            secilen_dosya = next(f for f in teklif_dosyalari if f['name'] == secim)
            
            if secilen_dosya:
                with st.spinner("Proje açılıyor..."):
                    # Burada cache kullanmıyoruz, çünkü tüm Excel nesnesi lazım
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