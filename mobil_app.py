import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os

st.set_page_config(page_title="ArtikaPro Malzemeler", page_icon="🧱", layout="wide")

# --- DRIVE BAĞLANTISI ---
def get_drive_service():
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    json_file = 'credentials.json'
    if os.path.exists(json_file):
        return build('drive', 'v3', credentials=Credentials.from_service_account_file(json_file, scopes=scopes))
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
            return build('drive', 'v3', credentials=creds)
    except: pass
    st.error("Kimlik doğrulama yapılamadı.")
    return None

def load_material_list(service):
    # İsmi 'Malzeme_Listesi.xlsx' olan dosyayı bul
    query = "name = 'Malzeme_Listesi.xlsx' and trashed = false"
    results = service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if not files: return None
    
    file_id = files[0]['id']
    request = service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    file_stream.seek(0)
    return pd.read_excel(file_stream)

# --- ARAYÜZ ---
def main():
    st.title("🧱 ArtikaPro Malzeme Kütüphanesi")
    
    service = get_drive_service()
    if not service: return
    
    with st.spinner("Malzeme listesi güncelleniyor..."):
        df = load_material_list(service)
    
    if df is None:
        st.warning("Drive'da 'Malzeme_Listesi.xlsx' bulunamadı. Masaüstü uygulamasından bir malzeme güncelleyerek dosyanın oluşmasını sağlayın.")
        return

    # ARAMA MOTORU
    search = st.text_input("Malzeme Ara (Ad veya Kod):", "")
    
    if search:
        # Büyük/küçük harf duyarsız arama
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False)).any(axis=1)
        df_filtered = df[mask]
    else:
        df_filtered = df

    st.write(f"Toplam **{len(df_filtered)}** malzeme bulundu.")
    
    # TABLO GÖSTERİMİ
    st.dataframe(
        df_filtered, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Toplam Fiyat": st.column_config.NumberColumn(format="%.2f TL"),
            "Malzeme Fiyatı": st.column_config.NumberColumn(format="%.2f"),
            "İşçilik Fiyatı": st.column_config.NumberColumn(format="%.2f"),
        }
    )

if __name__ == "__main__":
    main()