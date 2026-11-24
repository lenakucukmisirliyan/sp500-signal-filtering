import pandas as pd
import streamlit as st

from sklearn.metrics import (
    accuracy_score,
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

KARAR_ACIKLAMALARI = {
    "AL": "Görece güçlü sinyal",
    "NOTR": "Belirsiz sinyal",
    "ALMA": "Görece zayıf sinyal",
}


@st.cache_data(ttl=300)
def sorgu_dataframe(sorgu, parametreler=None):
    """SQL sorgusunu çalıştırarak DataFrame döndürür."""

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
def model_verisini_getir(donem):
    """Seçilen dönemin model kararlarını ve sonuçlarını getirir."""

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
    """Model kararlarından sınıflandırma ölçülerini hesaplar."""

    sonuclar = []

    for model_kodu, model_verisi in veri.groupby(
        "model_kodu"
    ):
        gercek = (
            model_verisi["basarili_mi"]
            .astype(bool)
            .astype(int)
        )

        # ALMA dışındaki sinyallere izin verildiği kabul edilir.
        tahmin = (
            model_verisi["model_karari"] != "ALMA"
        ).astype(int)

        olasilik = (
            model_verisi["basari_olasiligi"]
            .astype(float)
        )

        if gercek.nunique() > 1:
            roc_auc = roc_auc_score(
                gercek,
                olasilik,
            )
        else:
            roc_auc = 0.0

        izin_verilen = model_verisi[
            model_verisi["model_karari"] != "ALMA"
        ]

        engellenen = model_verisi[
            model_verisi["model_karari"] == "ALMA"
        ]

        sonuclar.append(
            {
                "Model": MODEL_ADLARI[model_kodu],
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
                    len(engellenen)
                    / len(model_verisi)
                    * 100
                ),
                "İzin Verilen Başarı (%)": (
                    izin_verilen["basarili_mi"]
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
        sonuc[sayisal_sutunlar].round(2)
    )

    return sonuc.sort_values(
        "F1 Macro (%)",
        ascending=False,
    )


@st.cache_data(ttl=300)
def ensemble_ozetini_getir():
    """Ensemble kararlarının dönemsel sonuçlarını getirir."""

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
            ) AS basari_orani,

            ROUND(
                AVG(iss.net_getiri) * 100,
                4
            ) AS ortalama_net_getiri_yuzde

        FROM ensemble_kararlari ek

        INNER JOIN islem_sinyalleri iss
            ON iss.sinyal_id = ek.sinyal_id

        GROUP BY
            ek.deney_donemi,
            ek.ensemble_karari

        ORDER BY
            ek.deney_donemi,

            CASE ek.ensemble_karari
                WHEN 'AL' THEN 1
                WHEN 'NOTR' THEN 2
                WHEN 'ALMA' THEN 3
            END;
    """

    return sorgu_dataframe(sorgu)


@st.cache_data(ttl=300)
def sembolleri_getir():
    """Geçmiş karar görünümündeki sembolleri getirir."""

    sorgu = """
        SELECT DISTINCT sembol
        FROM gecmis_sinyal_incelemesi
        ORDER BY sembol;
    """

    return sorgu_dataframe(sorgu)["sembol"].tolist()


@st.cache_data(ttl=300)
def tarihleri_getir(sembol):
    """Seçilen sembol için sinyal bulunan tarihleri getirir."""

    sorgu = """
        SELECT DISTINCT
            sinyal_zamani_new_york::DATE AS tarih

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
    """Seçilen sembol ve tarihteki sinyalleri getirir."""

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
    """Seçilen sinyalin bütün karar bilgilerini getirir."""

    sorgu = """
        SELECT *
        FROM gecmis_sinyal_incelemesi
        WHERE sinyal_id = %s;
    """

    return sorgu_dataframe(
        sorgu,
        (int(sinyal_id),),
    ).iloc[0]


def genel_bakis_sayfasi():
    """Projenin genel veri özetini gösterir."""

    st.header("Proje Genel Bakışı")

    st.write(
        "Bu çalışma, S&P 500 hisselerinde teknik analizle "
        "üretilen alım sinyallerini piyasa ve hisse "
        "koşullarına göre sınıflandıran bir karar destek "
        "sistemidir."
    )

    sayilar = genel_sayilari_getir()

    birinci_satir = st.columns(3)

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

    ikinci_satir = st.columns(3)

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

    karar_tablosu = pd.DataFrame(
        [
            {
                "Karar": "AL",
                "Açıklama": "Modellerin görece güçlü bulduğu sinyal",
            },
            {
                "Karar": "NÖTR",
                "Açıklama": "Modellerin yeterince ayrıştıramadığı sinyal",
            },
            {
                "Karar": "ALMA",
                "Açıklama": "Modellerin görece zayıf bulduğu sinyal",
            },
        ]
    )

    st.dataframe(
        karar_tablosu,
        hide_index=True,
        use_container_width=True,
    )

    st.warning(
        "Model kararları kesin getiri tahmini veya yatırım "
        "tavsiyesi değildir. Kararlar sinyallerin geçmiş "
        "verilere göre göreli kalite sınıflandırmasını gösterir."
    )


def model_karsilastirma_sayfasi():
    """Altı modelin performans ölçülerini gösterir."""

    st.header("Makine Öğrenmesi Model Karşılaştırması")

    donem = st.selectbox(
        "Değerlendirme dönemi",
        options=list(DONEM_ADLARI.keys()),
        format_func=lambda kod: DONEM_ADLARI[kod],
    )

    veri = model_verisini_getir(donem)
    performans = model_performanslarini_hesapla(veri)

    st.dataframe(
        performans,
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "Accuracy genel doğru karar oranını, precision izin "
        "verilen sinyallerin başarı oranını, recall başarılı "
        "sinyallerin ne kadarının korunduğunu, F1 precision ile "
        "recall dengesini ve ROC-AUC modelin sıralama gücünü "
        "gösterir."
    )

    grafik_verisi = (
        performans[
            [
                "Model",
                "F1 Macro (%)",
                "ROC-AUC (%)",
            ]
        ]
        .set_index("Model")
    )

    st.bar_chart(grafik_verisi)


def ensemble_sayfasi():
    """Ensemble kararlarının sonuçlarını gösterir."""

    st.header("Ağırlıklı Ensemble Sonuçları")

    veri = ensemble_ozetini_getir().copy()

    veri["Dönem"] = veri[
        "deney_donemi"
    ].map(DONEM_ADLARI)

    veri["Karar"] = veri[
        "ensemble_karari"
    ].map(KARAR_ACIKLAMALARI)

    gosterilecek = veri[
        [
            "Dönem",
            "Karar",
            "sinyal_sayisi",
            "basari_orani",
            "ortalama_net_getiri_yuzde",
        ]
    ].rename(
        columns={
            "sinyal_sayisi": "Sinyal Sayısı",
            "basari_orani": "Başarı Oranı (%)",
            "ortalama_net_getiri_yuzde": (
                "Ortalama Net Getiri (%)"
            ),
        }
    )

    st.dataframe(
        gosterilecek,
        hide_index=True,
        use_container_width=True,
    )

    donem = st.selectbox(
        "Grafikte gösterilecek dönem",
        options=list(DONEM_ADLARI.keys()),
        format_func=lambda kod: DONEM_ADLARI[kod],
        key="ensemble_donem",
    )

    grafik = veri[
        veri["deney_donemi"] == donem
    ][
        [
            "Karar",
            "basari_orani",
        ]
    ].set_index("Karar")

    st.bar_chart(grafik)

    st.info(
        "Başarı oranlarının AL > NÖTR > ALMA şeklinde "
        "sıralanması, ensemble yönteminin sinyal kalitesini "
        "ayırt edebildiğini gösterir. Ortalama getiri aynı "
        "sıralamayı izlemeyebilir."
    )


def gecmis_sinyal_sayfasi():
    """Seçilen geçmiş sinyalin kararlarını gösterir."""

    st.header("Geçmiş Sinyal İncelemesi")

    st.write(
        "Bir sembol ve sinyal tarihi seçerek modellerin o anda "
        "verdiği kararları ve 60 dakika sonra gerçekleşen sonucu "
        "inceleyebilirsiniz."
    )

    semboller = sembolleri_getir()

    sembol = st.selectbox(
        "Sembol",
        options=semboller,
    )

    tarihler = tarihleri_getir(sembol)

    tarih = st.selectbox(
        "Sinyal tarihi (New York)",
        options=tarihler,
        format_func=lambda deger: deger.strftime(
            "%d.%m.%Y"
        ),
    )

    sinyaller = gunun_sinyallerini_getir(
        sembol,
        tarih,
    )

    sinyal_secimleri = {
        (
            f"{satir.sinyal_zamani_new_york:%H:%M}"
            f" | Sinyal No: {satir.sinyal_id}"
        ): satir.sinyal_id
        for satir in sinyaller.itertuples()
    }

    secilen_etiket = st.selectbox(
        "Sinyal saati",
        options=list(sinyal_secimleri.keys()),
    )

    sinyal_id = sinyal_secimleri[
        secilen_etiket
    ]

    sinyal = tek_sinyali_getir(sinyal_id)

    st.subheader("Ensemble kararı")

    karar_sutunu, al_sutunu, notr_sutunu, alma_sutunu = (
        st.columns(4)
    )

    karar_sutunu.metric(
        "Nihai Karar",
        sinyal["ensemble_karari"],
    )

    al_sutunu.metric(
        "AL Ağırlığı",
        f"%{float(sinyal['al_oy_agirligi']) * 100:.2f}",
    )

    notr_sutunu.metric(
        "NÖTR Ağırlığı",
        f"%{float(sinyal['notr_oy_agirligi']) * 100:.2f}",
    )

    alma_sutunu.metric(
        "ALMA Ağırlığı",
        f"%{float(sinyal['alma_oy_agirligi']) * 100:.2f}",
    )

    model_satirlari = [
        {
            "Model": "Logistic Regression",
            "Karar": sinyal[
                "logistic_regression_karari"
            ],
            "Başarı Olasılığı (%)": (
                float(
                    sinyal[
                        "logistic_regression_olasiligi"
                    ]
                )
                * 100
            ),
        },
        {
            "Model": "Decision Tree",
            "Karar": sinyal["decision_tree_karari"],
            "Başarı Olasılığı (%)": (
                float(
                    sinyal["decision_tree_olasiligi"]
                )
                * 100
            ),
        },
        {
            "Model": "Random Forest",
            "Karar": sinyal["random_forest_karari"],
            "Başarı Olasılığı (%)": (
                float(
                    sinyal["random_forest_olasiligi"]
                )
                * 100
            ),
        },
        {
            "Model": "K-Nearest Neighbors",
            "Karar": sinyal["knn_karari"],
            "Başarı Olasılığı (%)": (
                float(sinyal["knn_olasiligi"])
                * 100
            ),
        },
        {
            "Model": "Gaussian Naive Bayes",
            "Karar": sinyal["naive_bayes_karari"],
            "Başarı Olasılığı (%)": (
                float(
                    sinyal["naive_bayes_olasiligi"]
                )
                * 100
            ),
        },
        {
            "Model": "Yapay Sinir Ağı",
            "Karar": sinyal[
                "yapay_sinir_agi_karari"
            ],
            "Başarı Olasılığı (%)": (
                float(
                    sinyal[
                        "yapay_sinir_agi_olasiligi"
                    ]
                )
                * 100
            ),
        },
    ]

    model_tablosu = pd.DataFrame(model_satirlari)
    model_tablosu["Başarı Olasılığı (%)"] = (
        model_tablosu[
            "Başarı Olasılığı (%)"
        ].round(2)
    )

    st.subheader("Model kararları")

    st.dataframe(
        model_tablosu,
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Sonradan gerçekleşen sonuç")

    sonuc_sutunlari = st.columns(4)

    sonuc_sutunlari[0].metric(
        "Giriş Fiyatı",
        f"{float(sinyal['giris_fiyati']):.4f}",
    )

    sonuc_sutunlari[1].metric(
        "Çıkış Fiyatı",
        f"{float(sinyal['cikis_fiyati']):.4f}",
    )

    sonuc_sutunlari[2].metric(
        "Net Getiri",
        f"%{float(sinyal['net_getiri']) * 100:.4f}",
    )

    sonuc_sutunlari[3].metric(
        "Gerçekleşen Sonuç",
        (
            "Başarılı"
            if sinyal["basarili_mi"]
            else "Başarısız"
        ),
    )

    st.caption(
        f"Giriş zamanı: {sinyal['giris_zamani']} | "
        f"Çıkış zamanı: {sinyal['cikis_zamani']}"
    )


st.title("S&P 500 Sinyal Filtreleme ve Karar Destek Sistemi")

sayfa = st.sidebar.radio(
    "Sayfa",
    options=[
        "Genel Bakış",
        "Model Karşılaştırması",
        "Ensemble Analizi",
        "Geçmiş Sinyal İncelemesi",
    ],
)

if sayfa == "Genel Bakış":
    genel_bakis_sayfasi()

elif sayfa == "Model Karşılaştırması":
    model_karsilastirma_sayfasi()

elif sayfa == "Ensemble Analizi":
    ensemble_sayfasi()

else:
    gecmis_sinyal_sayfasi()