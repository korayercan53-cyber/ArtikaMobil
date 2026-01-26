import streamlit as st
import pandas as pd

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ArtikaPro Bulut",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. PREMIUM TASARIM (CSS) ---
st.markdown("""
<style>
    /* Arka plan ve genel font */
    .main { background-color: #f8f9fa; }
    
    /* KART TASARIMI */
    .material-card {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eef2f6;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .material-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        border-color: #FF4B4B;
    }
    
    /* Sol taraftaki renkli şerit */
    .card-strip {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 6px;
        background: linear-gradient(180deg, #FF4B4B 0%, #FF8F8F 100%);
    }

    /* İçerik Stilleri */
    .card-code {
        font-size: 12px;
        color: #9ca3af;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .card-title {
        font-size: 18px;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 10px;
        line-height: 1.4;
        height: 50px; /* İsimler uzunsa hizayı bozmasın */
        overflow: hidden;
    }
    .card-price-box {
        background-color: #fff1f2;
        color: #be123c;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 20px;
        display: inline-block;
        margin-top: 10px;
    }
    .card-unit {
        font-size: 12px;
        color: #be123c;
        margin-left: 2px;
    }
    .card-desc {
        font-size: 13px;
        color: #6b7280;
        margin-top: 12px;
        border-top: 1px solid #f3f4f6;
        padding-top: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* İstatistik Kutuları */
    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e5e7eb;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. VERİ YÜKLEME (GOOGLE DRIVE'DAN CANLI) ---
@st.cache_data(ttl=600) # Veriyi 10 dakikada bir yeniler (Hız için)
def load_data():
    # BURAYA O UZUN DRIVE ID'Yİ YAPIŞTIR
    DRIVE_FILE_ID = "1mTx-wY_D2W1QGgAV7_xYJMu4UQ3cYybY" 
    
    # Drive indirme bağlantısını oluşturuyoruz
    url = f'https://drive.google.com/uc?id={DRIVE_FILE_ID}'
    
    try:
        # Doğrudan internetten okuyoruz
        df = pd.read_excel(url)
        return df
    except Exception as e:
        st.error(f"Veri Drive'dan çekilemedi: {e}")
        return None

df = load_data()

# --- 4. YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=70)
    st.title("ArtikaPro Bulut")
    st.caption("Dijital Malzeme Kataloğu")
    st.divider()
    
    # Arama
    search = st.text_input("🔍 Hızlı Arama", placeholder="Alçıpan, Boya...")
    
    # Sıralama
    sort_opt = st.radio("Sıralama", ["İsme Göre (A-Z)", "Fiyata Göre (Artan)", "Fiyata Göre (Azalan)"])
    
    st.divider()
    if df is not None:
        st.info(f"📅 Toplam {len(df)} kalem malzeme listeleniyor.")
    else:
        st.error("Excel dosyası bulunamadı.")

# --- 5. ANA EKRAN ---
if df is not None:
    # --- Veri Filtreleme ve Sıralama ---
    filtered_df = df.copy()
    
    # Arama
    if search:
        search = search.lower()
        filtered_df = filtered_df[
            filtered_df['Malzeme Adı'].astype(str).str.lower().str.contains(search) | 
            filtered_df['Kod'].astype(str).str.lower().str.contains(search)
        ]
    
    # Sıralama Mantığı
    if sort_opt == "İsme Göre (A-Z)":
        filtered_df = filtered_df.sort_values('Malzeme Adı')
    elif sort_opt == "Fiyata Göre (Artan)":
        filtered_df = filtered_df.sort_values('Toplam Birim Fiyat')
    else:
        filtered_df = filtered_df.sort_values('Toplam Birim Fiyat', ascending=False)

    # --- ÜST BİLGİ PANELİ (METRICS) ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Listelenen Ürün", f"{len(filtered_df)}")
    with col2:
        avg = filtered_df['Toplam Birim Fiyat'].mean()
        st.metric("Ortalama Fiyat", f"{avg:,.2f} ₺")
    with col3:
        max_p = filtered_df['Toplam Birim Fiyat'].max()
        st.metric("En Pahalı", f"{max_p:,.2f} ₺")
    with col4:
        min_p = filtered_df['Toplam Birim Fiyat'].min()
        st.metric("En Ucuz", f"{min_p:,.2f} ₺")
        
    st.divider()

    # --- GÖRÜNÜM SEÇENEKLERİ (SEKMELER) ---
    tab_card, tab_list = st.tabs(["🪟 Kart Görünümü (Mobil)", "📋 Liste Görünümü (Detaylı)"])

    # --- TAB 1: KART GÖRÜNÜMÜ ---
    with tab_card:
        if filtered_df.empty:
            st.warning("Aradığınız kriterlere uygun malzeme bulunamadı.")
        else:
            # 3'lü kolon sistemi (Telefonda otomatik tek kolona düşer)
            cols = st.columns(3)
            
            for index, row in filtered_df.iterrows():
                # Her satır için bir kart oluştur
                with cols[index % 3]:
                    # Verileri güvenli çek
                    kod = row.get('Kod', '-')
                    ad = row.get('Malzeme Adı', 'İsimsiz')
                    fiyat = row.get('Toplam Birim Fiyat', 0)
                    birim = row.get('Birim', 'Adet')
                    aciklama = row.get('Açıklama', '-')
                    if pd.isna(aciklama): aciklama = ""

                    # HTML Kart
                    html = f"""
                    <div class="material-card">
                        <div class="card-strip"></div>
                        <div class="card-code">#{kod}</div>
                        <div class="card-title">{ad}</div>
                        <div class="card-price-box">
                            {fiyat:,.2f} <span class="card-unit">₺ / {birim}</span>
                        </div>
                        <div class="card-desc">
                            ℹ️ {aciklama}
                        </div>
                    </div>
                    """
                    st.markdown(html, unsafe_allow_html=True)

    # --- TAB 2: LİSTE GÖRÜNÜMÜ ---
    with tab_list:
        # Tabloyu daha şık göstermek için konfigürasyon
        st.dataframe(
            filtered_df,
            column_config={
                "Toplam Birim Fiyat": st.column_config.NumberColumn(
                    "Birim Fiyat",
                    format="%.2f ₺",
                ),
                "Malzeme Adı": st.column_config.TextColumn(
                    "Malzeme Adı",
                    width="medium"
                ),
                "Malzeme Birim Fiyat": st.column_config.NumberColumn(format="%.2f ₺"),
                "İşçilik Birim Fiyat": st.column_config.NumberColumn(format="%.2f ₺"),
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )

else:
    st.error("⚠️ 'Malzeme_Listesi.xlsx' dosyası bulunamadı. Lütfen GitHub deponuza bu dosyayı yükleyin.")