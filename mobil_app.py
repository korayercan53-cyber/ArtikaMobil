import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import datetime

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(page_title="ArtikaPro Bulut", page_icon="🏗️", layout="wide")

# Modern CSS (Kart Görünümü İçin)
st.markdown("""
<style>
    /* Sekme Tasarımı */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #f1f5f9; border-radius: 8px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B; color: white; }

    /* Malzeme Kartı Tasarımı */
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
# AYARLAR (ID'Yİ BURAYA YAPIŞTIR)
# ==========================================
DRIVE_KLASOR_ID = "1mTx-wY_D2W1QGgAV7_xYJMu4UQ3cYybY"
# ==========================================

# --- 2. DRIVE BAĞLANTISI (SENİN MOTORUN) ---
@st.cache_resource
def get_drive_service():
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    # GitHub Secrets'tan anahtarı okuyoruz
    if "gcp_service_account" in st.secrets:
        try:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            st.error(f"Secrets hatası: {e}")
            return None
    st.error("⚠️ 'gcp_service_account' secret bulunamadı! Lütfen Streamlit ayarlarını kontrol edin.")
    return None

def list_files_in_folder(service, folder_id):
    # Sadece Excel dosyalarını listeler
    query = f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and trashed = false"
    try:
        results = service.files().list(q=query, pageSize=50, fields="files(id, name, modifiedTime)").execute()
        return results.get('files', [])
    except Exception as e:
        st.error(f"Klasör okuma hatası: {e}")
        return []

@st.cache_data(ttl=600) # Veriyi 10 dk önbellekte tut
def load_excel_by_id(_service, file_id):
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

# --- 3. ANA UYGULAMA ---
def main():
    service = get_drive_service()
    if not service: return

    # Başlık Alanı
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=60)
    with col_title:
        st.title("ArtikaPro Bulut")
        st.caption("Saha ve Ofis Arasında Kesintisiz Veri Akışı")

    # Dosyaları Çek
    with st.spinner("Drive taranıyor..."):
        files = list_files_in_folder(service, DRIVE_KLASOR_ID)
    
    if not files:
        st.warning(f"Bu klasörde (ID: {DRIVE_KLASOR_ID}) Excel dosyası bulunamadı.")
        return

    # Dosyaları Sınıflandır
    # "malzeme" içerenler malzeme listesi, "teklif" içerenler proje dosyasıdır.
    malzeme_listeleri = [f for f in files if "malzeme" in f['name'].lower()]
    teklif_listeleri = [f for f in files if "teklif" in f['name'].lower()]

    # En güncel malzeme dosyasını bul
    malzeme_listeleri.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
    active_malzeme_file = malzeme_listeleri[0] if malzeme_listeleri else None

    # --- SEKMELER ---
    tab1, tab2 = st.tabs(["🧱 MALZEME KÜTÜPHANESİ", "📋 PROJE TEKLİFLERİ"])

    # ---------------------------------------------------------
    # SEKME 1: MALZEME KÜTÜPHANESİ (MODERN KART TASARIMI)
    # ---------------------------------------------------------
    with tab1:
        if active_malzeme_file:
            # Tarih Gösterimi
            tarih = active_malzeme_file.get('modifiedTime', '')[:10]
            st.info(f"📂 Aktif Liste: **{active_malzeme_file['name']}** (Güncelleme: {tarih})")
            
            xls = load_excel_by_id(service, active_malzeme_file['id'])
            if xls:
                df = pd.read_excel(xls)
                
                # Arama ve İstatistik
                col_search, col_stat = st.columns([3, 1])
                with col_search:
                    search = st.text_input("🔍 Hızlı Malzeme Ara", placeholder="Alçıpan, Profil, Boya...", key="search_mat")
                with col_stat:
                    st.metric("Toplam Kalem", f"{len(df)}")
                
                # Filtreleme
                if search:
                    df = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)]

                # GÖRÜNÜM SEÇİCİ
                view_mode = st.radio("Görünüm:", ["Kart (Mobil)", "Tablo (Detaylı)"], horizontal=True, label_visibility="collapsed")

                if view_mode == "Kart (Mobil)":
                    if df.empty:
                        st.warning("Sonuç bulunamadı.")
                    else:
                        cols = st.columns(3) # Geniş ekranda 3'lü, mobilde tekli
                        for index, row in df.iterrows():
                            with cols[index % 3]:
                                # Veri Güvenliği (Sütun isimleri Excel'e göre)
                                # 'Malzeme Adı' sütunu yoksa ilk sütunu alır
                                ad = row.get('Malzeme Adı', row.iloc[1] if len(row)>1 else '-')
                                kod = row.get('Kod', row.get('Poz No', ''))
                                fiyat = row.get('Toplam Birim Fiyat', row.get('Birim Fiyat', 0))
                                birim = row.get('Birim', 'Adet')
                                aciklama = row.get('Açıklama', '')
                                
                                # HTML Kart Bas
                                st.markdown(f"""
                                <div class="material-card">
                                    <div class="card-code">#{kod}</div>
                                    <div class="card-title">{ad}</div>
                                    <div class="card-price">
                                        {fiyat:,.2f} ₺
                                        <span class="card-unit">/ {birim}</span>
                                    </div>
                                    <div class="card-desc">{aciklama if pd.notna(aciklama) else ''}</div>
                                </div>
                                """, unsafe_allow_html=True)
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.warning("Klasörde 'malzeme' isimli bir dosya bulunamadı.")

    # ---------------------------------------------------------
    # SEKME 2: PROJE TEKLİFLERİ (DİNAMİK LİSTE)
    # ---------------------------------------------------------
    with tab2:
        if teklif_listeleri:
            col_sel, col_info = st.columns([3, 1])
            with col_sel:
                secilen_proje_adi = st.selectbox("📂 İncelemek İstediğiniz Projeyi Seçin:", [f['name'] for f in teklif_listeleri])
            
            secilen_dosya = next(f for f in teklif_listeleri if f['name'] == secilen_proje_adi)
            
            with col_info:
                st.caption(f"📅 {secilen_dosya.get('modifiedTime', '')[:10]}")

            # Dosyayı Yükle
            with st.spinner(f"'{secilen_proje_adi}' yükleniyor..."):
                xls_proj = load_excel_by_id(service, secilen_dosya['id'])
                
                if xls_proj:
                    # Sayfaları Listele (İcmal vs.)
                    sheet_names = xls_proj.sheet_names
                    
                    # Önce İcmal Tablosu Varsa Onu Göster
                    if "İcmal Tablosu" in sheet_names:
                        st.success("📊 Proje Özeti (İcmal)")
                        df_icmal = pd.read_excel(xls_proj, "İcmal Tablosu")
                        st.dataframe(df_icmal, use_container_width=True)
                        st.markdown("---")
                    
                    # Diğer Detay Sayfaları
                    detaylar = [s for s in sheet_names if s != "İcmal Tablosu"]
                    if detaylar:
                        secilen_sayfa = st.pills("Detay Sayfası Seçin:", detaylar, default=detaylar[0])
                        if secilen_sayfa:
                            df_detay = pd.read_excel(xls_proj, secilen_sayfa)
                            
                            # Detay Tablosunu Güzelleştir
                            st.dataframe(
                                df_detay, 
                                use_container_width=True,
                                height=500
                            )
        else:
            st.info("Henüz bir proje teklifi yüklenmemiş. (Dosya isminde 'teklif' geçmelidir)")

if __name__ == "__main__":
    main()