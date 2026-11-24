import pandas as pd
import streamlit as st

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.veritabani import veritabani_baglantisi_olustur


st.set_page_config(
    page_title="S&P 500 Sinyal Filtreleme",
    page_icon="📈",
    layout="wide",
)


MODEL_ADLARI = {
    "LOGISTIC_REGRESSION": "Logistic Regression",
    "DECISION_TREE": "Decision Tree",
    "RANDOM_FOREST": "Random Forest",
    "KNN": "K-Nearest Neighbors",
    "NAIVE_BAYES": "Gaussian Naive Bayes",
    "YAPAY_SINIR_AGI": "Yapay Sinir Ağı",
}

DONEM_ADLARI = {
    "DOGRULAMA": "Birinci Doğrulama",
    "IKINCIL_DOGRULAMA": "İkinci Doğrulama",
    "NIHAI_TEST": "Nihai Test",
}

YONTEM_ADLARI = {
    "FILTRESIZ": "Filtresiz",
    "KURAL_TABANLI": "Kural Tabanlı",
    "RANDOM_FOREST": "Random Forest",
    "AGIRLIKLI_ENSEMBLE": "Ağırlıklı Ensemble",
}

KARAR_ADLARI = {
    "AL": "AL – Görece Güçlü",
    "NOTR": "NÖTR – Belirsiz",
    "ALMA": "ALMA – Görece Zayıf",
}


@st.cache_data(ttl=300)
def sorgu_dataframe(sorgu, parametreler=None):
    """SQL sorgusunu çalıştırıp DataFrame döndürür."""

    baglanti = veritabani_baglantisi_olustur()
    imlec = baglanti.cursor()

    try:
        imlec.execute(
            sorgu,
            parametreler or (),
        )

        sutunlar = [
            aciklama[0]
            for aciklama in imlec.description
        ]

        return pd.DataFrame(
            imlec.fetchall(),
            columns=sutunlar,
        )

    finally:
        imlec.close()
        baglanti.close()


@st.cache_data(ttl=300)
def genel_sayilari_getir():
    """Projenin temel veri sayılarını getirir."""

    sorgu = """
        SELECT
            (
                SELECT COUNT(*)
                FROM menkul_kiymetler
            ) AS menkul_kiymet_sayisi,

            (
                SELECT COUNT(*)
                FROM ham_fiyat_verileri
            ) AS ham_veri_sayisi,

            (
                SELECT COUNT(*)
                FROM analiz_fiyat_verileri
            ) AS analiz_verisi_sayisi,

            (
                SELECT COUNT(*)
                FROM islem_sinyalleri
            ) AS toplam_sinyal_sayisi,

            (
                SELECT COUNT(*)
                FROM islem_sinyalleri
                WHERE doldurulmus_veri_var_mi = FALSE
            ) AS guvenilir_sinyal_sayisi,

            (
                SELECT COUNT(*)
                FROM ensemble_kararlari
            ) AS ensemble_sinyal_sayisi;
    """

    return sorgu_dataframe(sorgu).iloc[0]


@st.cache_data(ttl=300)
def yontem_sonuclarini_getir(donem):
    """Dört yöntemin performans sonuçlarını getirir."""

    sorgu = """
        SELECT *
        FROM genisletilmis_performans_sonuclari
        WHERE deney_donemi = %s;
    """

    return sorgu_dataframe(
        sorgu,
        (donem,),
    )


@st.cache_data(ttl=300)
def model_verisini_getir(donem):
    """Model tahminlerini ve gerçekleşen sonuçları getirir."""

    sorgu = """
        SELECT
            msk.model_kodu,
            msk.basari_olasiligi,
            msk.model_karari,
            iss.basarili_mi,
            iss.net_getiri

        FROM model_sinyal_kararlari msk

        INNER JOIN islem_sinyalleri iss
            ON iss.sinyal_id = msk.sinyal_id

        WHERE msk.deney_donemi = %s;
    """

    return sorgu_dataframe(
        sorgu,
        (donem,),
    )


def model_performanslarini_hesapla(veri):
    """Her modelin ikili filtreleme performansını hesaplar."""

    sonuclar = []

    for model_kodu, model_verisi in veri.groupby(
        "model_kodu"
    ):
        gercek = (
            model_verisi["basarili_mi"]
            .astype(bool)
            .astype(int)
        )

        # AL ve NÖTR kullanılır, ALMA engellenir.
        tahmin = (
            model_verisi["model_karari"]
            != "ALMA"
        ).astype(int)

        olasilik = (
            model_verisi["basari_olasiligi"]
            .astype(float)
        )

        roc_auc = roc_auc_score(
            gercek,
            olasilik,
        )

        izin_verilen = model_verisi[
            model_verisi["model_karari"]
            != "ALMA"
        ]

        sonuclar.append(
            {
                "Model": MODEL_ADLARI[model_kodu],
                "Model Kodu": model_kodu,
                "Accuracy (%)": (
                    accuracy_score(
                        gercek,
                        tahmin,
                    )
                    * 100
                ),
                "Precision (%)": (
                    precision_score(
                        gercek,
                        tahmin,
                        zero_division=0,
                    )
                    * 100
                ),
                "Recall (%)": (
                    recall_score(
                        gercek,
                        tahmin,
                        zero_division=0,
                    )
                    * 100
                ),
                "F1 (%)": (
                    f1_score(
                        gercek,
                        tahmin,
                        zero_division=0,
                    )
                    * 100
                ),
                "F1 Macro (%)": (
                    f1_score(
                        gercek,
                        tahmin,
                        average="macro",
                        zero_division=0,
                    )
                    * 100
                ),
                "ROC-AUC (%)": roc_auc * 100,
                "Engelleme (%)": (
                    (
                        model_verisi[
                            "model_karari"
                        ]
                        == "ALMA"
                    ).mean()
                    * 100
                ),
                "İzin Verilen Başarı (%)": (
                    izin_verilen[
                        "basarili_mi"
                    ]
                    .astype(float)
                    .mean()
                    * 100
                ),
            }
        )

    sonuc = pd.DataFrame(sonuclar)

    sayisal_sutunlar = sonuc.select_dtypes(
        include="number"
    ).columns

    sonuc[sayisal_sutunlar] = (
        sonuc[sayisal_sutunlar]
        .round(2)
    )

    return sonuc.sort_values(
        "F1 Macro (%)",
        ascending=False,
    )


@st.cache_data(ttl=300)
def model_karar_ozetini_getir(donem):
    """Model bazında AL, NÖTR ve ALMA sonuçlarını getirir."""

    sorgu = """
        SELECT
            msk.model_kodu,
            msk.model_karari,
            COUNT(*) AS sinyal_sayisi,

            ROUND(
                AVG(
                    iss.basarili_mi::INTEGER
                ) * 100,
                2
            ) AS basari_orani_yuzde,

            ROUND(
                AVG(iss.net_getiri) * 100,
                4
            ) AS ortalama_net_getiri_yuzde

        FROM model_sinyal_kararlari msk

        INNER JOIN islem_sinyalleri iss
            ON iss.sinyal_id =
               msk.sinyal_id

        WHERE msk.deney_donemi = %s

        GROUP BY
            msk.model_kodu,
            msk.model_karari

        ORDER BY
            msk.model_kodu,

            CASE msk.model_karari
                WHEN 'AL' THEN 1
                WHEN 'NOTR' THEN 2
                WHEN 'ALMA' THEN 3
            END;
    """

    return sorgu_dataframe(
        sorgu,
        (donem,),
    )


@st.cache_data(ttl=300)
def ensemble_ozetini_getir():
    """Ensemble kararlarının gerçekleşen sonuçlarını getirir."""

    sorgu = """
        SELECT
            ek.deney_donemi,
            ek.ensemble_karari,
            COUNT(*) AS sinyal_sayisi,

            ROUND(
                AVG(
                    iss.basarili_mi::INTEGER
                ) * 100,
                2
            ) AS basari_orani_yuzde,

            ROUND(
                AVG(iss.net_getiri) * 100,
                4
            ) AS ortalama_net_getiri_yuzde

        FROM ensemble_kararlari ek

        INNER JOIN islem_sinyalleri iss
            ON iss.sinyal_id =
               ek.sinyal_id

        GROUP BY
            ek.deney_donemi,
            ek.ensemble_karari;
    """

    return sorgu_dataframe(sorgu)


@st.cache_data(ttl=300)
def model_agirliklarini_getir(donem):
    """Seçilen dönemde kullanılan model ağırlıklarını getirir."""

    sorgu = """
        SELECT
            model_kodu,
            roc_auc,
            rastgele_ustu_puan,
            model_agirligi,
            agirlik_kaynagi

        FROM model_agirliklari

        WHERE uygulama_donemi = %s

        ORDER BY model_agirligi DESC;
    """

    return sorgu_dataframe(
        sorgu,
        (donem,),
    )


@st.cache_data(ttl=300)
def sembolleri_getir():
    """Geçmiş karar kayıtlarındaki sembolleri getirir."""

    sorgu = """
        SELECT DISTINCT sembol
        FROM gecmis_sinyal_incelemesi
        ORDER BY sembol;
    """

    return sorgu_dataframe(
        sorgu
    )["sembol"].tolist()


@st.cache_data(ttl=300)
def tarihleri_getir(sembol):
    """Seçilen sembolün sinyal tarihlerini getirir."""

    sorgu = """
        SELECT DISTINCT
            sinyal_zamani_new_york::DATE
                AS tarih

        FROM gecmis_sinyal_incelemesi

        WHERE sembol = %s

        ORDER BY tarih;
    """

    return sorgu_dataframe(
        sorgu,
        (sembol,),
    )["tarih"].tolist()


@st.cache_data(ttl=300)
def gunun_sinyallerini_getir(sembol, tarih):
    """Seçilen gündeki sinyalleri getirir."""

    sorgu = """
        SELECT
            sinyal_id,
            sinyal_zamani_new_york

        FROM gecmis_sinyal_incelemesi

        WHERE sembol = %s
          AND sinyal_zamani_new_york::DATE = %s

        ORDER BY sinyal_zamani_new_york;
    """

    return sorgu_dataframe(
        sorgu,
        (
            sembol,
            tarih,
        ),
    )


@st.cache_data(ttl=300)
def tek_sinyali_getir(sinyal_id):
    """Bir sinyalin bütün karar ve sonuçlarını getirir."""

    sorgu = """
        SELECT
            gsi.*,
            fs.kural_izin_verdi_mi

        FROM gecmis_sinyal_incelemesi gsi

        LEFT JOIN filtre_sonuclari fs
            ON fs.sinyal_id =
               gsi.sinyal_id

        WHERE gsi.sinyal_id = %s;
    """

    return sorgu_dataframe(
        sorgu,
        (int(sinyal_id),),
    ).iloc[0]


def genel_bakis_sayfasi():
    """Genel proje özetini gösterir."""

    st.header("Proje Genel Bakışı")

    st.write(
        "Bu çalışma, S&P 500 hisselerinde teknik analizle "
        "üretilen alım sinyallerini piyasa ve hisse "
        "koşullarına göre sınıflandıran bir karar destek "
        "sistemidir."
    )

    sayilar = genel_sayilari_getir()

    birinci_satir = st.columns(3)
    ikinci_satir = st.columns(3)

    birinci_satir[0].metric(
        "Menkul Kıymet",
        f"{int(sayilar['menkul_kiymet_sayisi']):,}",
    )

    birinci_satir[1].metric(
        "Ham Fiyat Kaydı",
        f"{int(sayilar['ham_veri_sayisi']):,}",
    )

    birinci_satir[2].metric(
        "Temiz Analiz Kaydı",
        f"{int(sayilar['analiz_verisi_sayisi']):,}",
    )

    ikinci_satir[0].metric(
        "Üretilen Sinyal",
        f"{int(sayilar['toplam_sinyal_sayisi']):,}",
    )

    ikinci_satir[1].metric(
        "Güvenilir Sinyal",
        f"{int(sayilar['guvenilir_sinyal_sayisi']):,}",
    )

    ikinci_satir[2].metric(
        "Ensemble Değerlendirmesi",
        f"{int(sayilar['ensemble_sinyal_sayisi']):,}",
    )

    st.subheader("Kararların anlamı")

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Karar": "AL",
                    "Anlamı": (
                        "Modellerin görece güçlü "
                        "bulduğu sinyal"
                    ),
                },
                {
                    "Karar": "NÖTR",
                    "Anlamı": (
                        "Modellerin yeterince "
                        "ayrıştıramadığı sinyal"
                    ),
                },
                {
                    "Karar": "ALMA",
                    "Anlamı": (
                        "Modellerin görece zayıf "
                        "bulduğu sinyal"
                    ),
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.warning(
        "Kararlar kesin getiri tahmini veya yatırım tavsiyesi "
        "değildir. Geçmiş verilere dayalı göreli sinyal "
        "kalitesini gösterir."
    )


def yontem_karsilastirma_sayfasi():
    """Dört temel yöntemi karşılaştırır."""

    st.header("Yöntem Karşılaştırması")

    donem = st.selectbox(
        "Değerlendirme dönemi",
        options=list(DONEM_ADLARI),
        format_func=lambda kod: DONEM_ADLARI[kod],
        key="yontem_donem",
    )

    veri = yontem_sonuclarini_getir(
        donem
    ).copy()

    veri["Yöntem"] = veri[
        "yontem"
    ].map(YONTEM_ADLARI)

    tablo = veri[
        [
            "Yöntem",
            "toplam_sinyal_sayisi",
            "kullanilan_sinyal_sayisi",
            "engelleme_orani_yuzde",
            "basari_orani_yuzde",
            "ortalama_net_getiri_yuzde",
            "medyan_net_getiri_yuzde",
            "getiri_standart_sapmasi_yuzde",
            "en_kotu_yuzde_5_ortalama_getiri",
        ]
    ].rename(
        columns={
            "toplam_sinyal_sayisi": "Toplam Sinyal",
            "kullanilan_sinyal_sayisi": "Kullanılan Sinyal",
            "engelleme_orani_yuzde": "Engelleme (%)",
            "basari_orani_yuzde": "Başarı (%)",
            "ortalama_net_getiri_yuzde": (
                "Ortalama Net Getiri (%)"
            ),
            "medyan_net_getiri_yuzde": (
                "Medyan Net Getiri (%)"
            ),
            "getiri_standart_sapmasi_yuzde": (
                "Standart Sapma (%)"
            ),
            "en_kotu_yuzde_5_ortalama_getiri": (
                "En Kötü %5 Ortalaması (%)"
            ),
        }
    )

    st.dataframe(
        tablo,
        hide_index=True,
        use_container_width=True,
    )

    sol, sag = st.columns(2)

    basari_grafigi = tablo[
        [
            "Yöntem",
            "Başarı (%)",
            "Engelleme (%)",
        ]
    ].set_index("Yöntem")

    sol.subheader("Başarı ve engelleme")
    sol.bar_chart(basari_grafigi)

    getiri_grafigi = tablo[
        [
            "Yöntem",
            "Ortalama Net Getiri (%)",
        ]
    ].set_index("Yöntem")

    sag.subheader("Ortalama net getiri")
    sag.bar_chart(getiri_grafigi)

    if donem == "NIHAI_TEST":
        st.info(
            "Nihai testte ağırlıklı ensemble en yüksek başarı "
            "oranına ulaşmıştır. Ancak ortalama net getiri "
            "pozitif değildir ve filtresiz sonuca göre çok az "
            "daha kötüdür."
        )


def model_karsilastirma_sayfasi():
    """Altı modelin ayrıntılı performansını gösterir."""

    st.header("Model Performansları")

    donem = st.selectbox(
        "Değerlendirme dönemi",
        options=list(DONEM_ADLARI),
        format_func=lambda kod: DONEM_ADLARI[kod],
        key="model_donem",
    )

    veri = model_verisini_getir(donem)
    performans = model_performanslarini_hesapla(
        veri
    )

    gosterilecek = performans.drop(
        columns=["Model Kodu"]
    )

    st.dataframe(
        gosterilecek,
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "Precision izin verilen sinyallerin başarı oranını, "
        "recall başarılı sinyallerin ne kadarının korunduğunu, "
        "F1 bu iki ölçünün dengesini ve ROC-AUC modelin başarılı "
        "sinyalleri sıralama gücünü gösterir."
    )

    grafik = performans[
        [
            "Model",
            "F1 Macro (%)",
            "ROC-AUC (%)",
        ]
    ].set_index("Model")

    st.bar_chart(grafik)

    st.subheader("Confusion matrix")

    secilen_model = st.selectbox(
        "Model",
        options=list(MODEL_ADLARI),
        format_func=lambda kod: MODEL_ADLARI[kod],
    )

    model_verisi = veri[
        veri["model_kodu"] == secilen_model
    ]

    gercek = (
        model_verisi["basarili_mi"]
        .astype(bool)
        .astype(int)
    )

    tahmin = (
        model_verisi["model_karari"]
        != "ALMA"
    ).astype(int)

    matris = confusion_matrix(
        gercek,
        tahmin,
        labels=[0, 1],
    )

    matris_tablosu = pd.DataFrame(
        matris,
        index=[
            "Gerçek Başarısız",
            "Gerçek Başarılı",
        ],
        columns=[
            "Tahmin ALMA",
            "Tahmin İzin Ver",
        ],
    )

    st.dataframe(
        matris_tablosu,
        use_container_width=True,
    )

    st.subheader("Üçlü karar performansı")

    karar_ozeti = model_karar_ozetini_getir(
        donem
    )

    karar_ozeti["Model"] = karar_ozeti[
        "model_kodu"
    ].map(MODEL_ADLARI)

    karar_ozeti["Karar"] = karar_ozeti[
        "model_karari"
    ].map(KARAR_ADLARI)

    karar_tablosu = karar_ozeti[
        [
            "Model",
            "Karar",
            "sinyal_sayisi",
            "basari_orani_yuzde",
            "ortalama_net_getiri_yuzde",
        ]
    ].rename(
        columns={
            "sinyal_sayisi": "Sinyal Sayısı",
            "basari_orani_yuzde": "Başarı (%)",
            "ortalama_net_getiri_yuzde": (
                "Ortalama Net Getiri (%)"
            ),
        }
    )

    st.dataframe(
        karar_tablosu,
        hide_index=True,
        use_container_width=True,
    )


def ensemble_sayfasi():
    """Ağırlıklı ensemble yapısını gösterir."""

    st.header("Ağırlıklı Ensemble Analizi")

    donem = st.selectbox(
        "Değerlendirme dönemi",
        options=list(DONEM_ADLARI),
        format_func=lambda kod: DONEM_ADLARI[kod],
        key="ensemble_donem",
    )

    st.subheader("Model ağırlıkları")

    agirliklar = model_agirliklarini_getir(
        donem
    ).copy()

    agirliklar["Model"] = agirliklar[
        "model_kodu"
    ].map(MODEL_ADLARI)

    agirliklar["ROC-AUC (%)"] = (
        agirliklar["roc_auc"]
        .astype(float)
        * 100
    ).round(2)

    agirliklar["Ağırlık (%)"] = (
        agirliklar["model_agirligi"]
        .astype(float)
        * 100
    ).round(2)

    agirlik_tablosu = agirliklar[
        [
            "Model",
            "ROC-AUC (%)",
            "Ağırlık (%)",
            "agirlik_kaynagi",
        ]
    ].rename(
        columns={
            "agirlik_kaynagi": "Ağırlık Kaynağı",
        }
    )

    st.dataframe(
        agirlik_tablosu,
        hide_index=True,
        use_container_width=True,
    )

    st.bar_chart(
        agirlik_tablosu[
            [
                "Model",
                "Ağırlık (%)",
            ]
        ].set_index("Model")
    )

    st.subheader("Ensemble karar sonuçları")

    ensemble = ensemble_ozetini_getir()
    ensemble = ensemble[
        ensemble["deney_donemi"] == donem
    ].copy()

    ensemble["Karar"] = ensemble[
        "ensemble_karari"
    ].map(KARAR_ADLARI)

    ensemble_tablosu = ensemble[
        [
            "Karar",
            "sinyal_sayisi",
            "basari_orani_yuzde",
            "ortalama_net_getiri_yuzde",
        ]
    ].rename(
        columns={
            "sinyal_sayisi": "Sinyal Sayısı",
            "basari_orani_yuzde": "Başarı (%)",
            "ortalama_net_getiri_yuzde": (
                "Ortalama Net Getiri (%)"
            ),
        }
    )

    st.dataframe(
        ensemble_tablosu,
        hide_index=True,
        use_container_width=True,
    )

    st.bar_chart(
        ensemble_tablosu[
            [
                "Karar",
                "Başarı (%)",
            ]
        ].set_index("Karar")
    )

    st.info(
        "Ağırlıklar yalnızca ilgili değerlendirme döneminden "
        "önce elde edilen doğrulama performanslarından "
        "hesaplanmıştır. Nihai test sonuçları ağırlık "
        "belirlemek için kullanılmamıştır."
    )


def gecmis_sinyal_sayfasi():
    """Geçmiş bir sinyalin karar ve sonucunu gösterir."""

    st.header("Geçmiş Sinyal İncelemesi")

    st.write(
        "Bir sembol ve tarih seçerek modellerin sinyal anındaki "
        "kararlarını ve daha sonra gerçekleşen sonucu "
        "inceleyebilirsiniz."
    )

    sembol = st.selectbox(
        "Sembol",
        options=sembolleri_getir(),
    )

    tarih = st.selectbox(
        "Sinyal tarihi – New York",
        options=tarihleri_getir(sembol),
        format_func=lambda deger: (
            deger.strftime("%d.%m.%Y")
        ),
    )

    sinyaller = gunun_sinyallerini_getir(
        sembol,
        tarih,
    )

    secenekler = {
        (
            f"{satir.sinyal_zamani_new_york:%H:%M}"
            f" | Sinyal No: {satir.sinyal_id}"
        ): satir.sinyal_id
        for satir in sinyaller.itertuples()
    }

    secilen = st.selectbox(
        "Sinyal saati",
        options=list(secenekler),
    )

    sinyal = tek_sinyali_getir(
        secenekler[secilen]
    )

    kural_karari = (
        "İZİN VER"
        if sinyal["kural_izin_verdi_mi"]
        else "ENGELLE"
    )

    ust_satir = st.columns(3)

    ust_satir[0].metric(
        "Kural Tabanlı Karar",
        kural_karari,
    )

    ust_satir[1].metric(
        "Ensemble Kararı",
        sinyal["ensemble_karari"],
    )

    ust_satir[2].metric(
        "Gerçekleşen Sonuç",
        (
            "Başarılı"
            if sinyal["basarili_mi"]
            else "Başarısız"
        ),
    )

    oylar = st.columns(3)

    oylar[0].metric(
        "AL Ağırlığı",
        f"%{float(sinyal['al_oy_agirligi']) * 100:.2f}",
    )

    oylar[1].metric(
        "NÖTR Ağırlığı",
        f"%{float(sinyal['notr_oy_agirligi']) * 100:.2f}",
    )

    oylar[2].metric(
        "ALMA Ağırlığı",
        f"%{float(sinyal['alma_oy_agirligi']) * 100:.2f}",
    )

    model_satirlari = [
        (
            "Logistic Regression",
            "logistic_regression_karari",
            "logistic_regression_olasiligi",
        ),
        (
            "Decision Tree",
            "decision_tree_karari",
            "decision_tree_olasiligi",
        ),
        (
            "Random Forest",
            "random_forest_karari",
            "random_forest_olasiligi",
        ),
        (
            "K-Nearest Neighbors",
            "knn_karari",
            "knn_olasiligi",
        ),
        (
            "Gaussian Naive Bayes",
            "naive_bayes_karari",
            "naive_bayes_olasiligi",
        ),
        (
            "Yapay Sinir Ağı",
            "yapay_sinir_agi_karari",
            "yapay_sinir_agi_olasiligi",
        ),
    ]

    model_tablosu = pd.DataFrame(
        [
            {
                "Model": model_adi,
                "Karar": sinyal[karar_sutunu],
                "Başarı Olasılığı (%)": round(
                    float(
                        sinyal[olasilik_sutunu]
                    )
                    * 100,
                    2,
                ),
            }
            for (
                model_adi,
                karar_sutunu,
                olasilik_sutunu,
            ) in model_satirlari
        ]
    )

    st.subheader("Model kararları")

    st.dataframe(
        model_tablosu,
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Sonradan gerçekleşen işlem")

    sonuc = st.columns(4)

    sonuc[0].metric(
        "Giriş Fiyatı",
        f"{float(sinyal['giris_fiyati']):.4f}",
    )

    sonuc[1].metric(
        "Çıkış Fiyatı",
        f"{float(sinyal['cikis_fiyati']):.4f}",
    )

    sonuc[2].metric(
        "Net Getiri",
        f"%{float(sinyal['net_getiri']) * 100:.4f}",
    )

    sonuc[3].metric(
        "Veri Dönemi",
        DONEM_ADLARI.get(
            sinyal["veri_donemi"],
            sinyal["veri_donemi"],
        ),
    )

    st.caption(
        f"Sinyal zamanı: "
        f"{sinyal['sinyal_zamani_new_york']} | "
        f"Giriş: {sinyal['giris_zamani']} | "
        f"Çıkış: {sinyal['cikis_zamani']}"
    )


st.title(
    "S&P 500 Sinyal Filtreleme ve Karar Destek Sistemi"
)

sayfa = st.sidebar.radio(
    "Sayfa",
    options=[
        "Genel Bakış",
        "Yöntem Karşılaştırması",
        "Model Performansları",
        "Ensemble Analizi",
        "Geçmiş Sinyal İncelemesi",
    ],
)

if sayfa == "Genel Bakış":
    genel_bakis_sayfasi()

elif sayfa == "Yöntem Karşılaştırması":
    yontem_karsilastirma_sayfasi()

elif sayfa == "Model Performansları":
    model_karsilastirma_sayfasi()

elif sayfa == "Ensemble Analizi":
    ensemble_sayfasi()

else:
    gecmis_sinyal_sayfasi()