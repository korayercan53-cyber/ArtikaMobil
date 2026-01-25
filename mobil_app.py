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

    # 2. SEKME: PROJELER (Aynı kalıyor)
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