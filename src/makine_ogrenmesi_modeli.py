import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from src.veritabani import (
    veritabani_baglantisi_olustur
)


OZELLIKLER = [
    "spy_sma20_farki_orani",
    "spy_60dk_getiri",
    "spy_60dk_volatilite",
    "spy_er12",
    "spy_ortalama_farki_orani",
    "hisse_15dk_getiri",
    "hisse_60dk_getiri",
    "hisse_60dk_volatilite",
    "hacim_orani_20",
    "hisse_ortalama_farki_orani",
    "goreceli_60dk_getiri",
    "gunun_dakikasi",
]

HEDEF_ENGELLEME_ORANI = 0.10


def veriyi_getir():
    """Makine ogrenmesi verilerini PostgreSQL'den getirir."""

    baglanti = veritabani_baglantisi_olustur()
    imlec = baglanti.cursor()

    try:
        imlec.execute(
            """
            SELECT
                sinyal_id,
                sinyal_zamani,
                veri_donemi,

                spy_sma20_farki_orani,
                spy_60dk_getiri,
                spy_60dk_volatilite,
                spy_er12,
                spy_ortalama_farki_orani,

                hisse_15dk_getiri,
                hisse_60dk_getiri,
                hisse_60dk_volatilite,
                hacim_orani_20,
                hisse_ortalama_farki_orani,
                goreceli_60dk_getiri,
                gunun_dakikasi,

                basarili_mi,
                net_getiri

            FROM makine_ogrenmesi_verileri

            ORDER BY sinyal_zamani;
            """
        )

        sutunlar = [
            "sinyal_id",
            "sinyal_zamani",
            "veri_donemi",

            "spy_sma20_farki_orani",
            "spy_60dk_getiri",
            "spy_60dk_volatilite",
            "spy_er12",
            "spy_ortalama_farki_orani",

            "hisse_15dk_getiri",
            "hisse_60dk_getiri",
            "hisse_60dk_volatilite",
            "hacim_orani_20",
            "hisse_ortalama_farki_orani",
            "goreceli_60dk_getiri",
            "gunun_dakikasi",

            "basarili_mi",
            "net_getiri",
        ]

        veri = pd.DataFrame(
            imlec.fetchall(),
            columns=sutunlar
        )

    finally:
        imlec.close()
        baglanti.close()

    veri["sinyal_zamani"] = pd.to_datetime(
        veri["sinyal_zamani"],
        utc=True
    )

    for ozellik in OZELLIKLER:
        veri[ozellik] = pd.to_numeric(
            veri[ozellik],
            errors="coerce"
        )

    veri["net_getiri"] = pd.to_numeric(
        veri["net_getiri"],
        errors="coerce"
    )

    veri["basarili_mi"] = (
        veri["basarili_mi"].astype(bool)
    )

    return veri


def deney_donemlerini_olustur(veri):
    """Test verisini ikincil dogrulama ve nihai teste ayirir."""

    veri = veri.copy()

    veri["deney_donemi"] = veri[
        "veri_donemi"
    ]

    ikincil_dogrulama = (
        (veri["veri_donemi"] == "TEST")
        & (
            veri["sinyal_zamani"]
            < pd.Timestamp(
                "2024-03-01",
                tz="UTC"
            )
        )
    )

    nihai_test = (
        (veri["veri_donemi"] == "TEST")
        & (
            veri["sinyal_zamani"]
            >= pd.Timestamp(
                "2024-03-01",
                tz="UTC"
            )
        )
    )

    veri.loc[
        ikincil_dogrulama,
        "deney_donemi"
    ] = "IKINCIL_DOGRULAMA"

    veri.loc[
        nihai_test,
        "deney_donemi"
    ] = "NIHAI_TEST"

    return veri


def model_olustur(
    model_adi="RANDOM_FOREST"
):
    """Istenen makine ogrenmesi modelini olusturur."""

    if model_adi == "LOGISTIC_REGRESSION":
        siniflandirici = LogisticRegression(
            max_iter=1000,
            random_state=42
        )

    elif model_adi == "DECISION_TREE":
        siniflandirici = DecisionTreeClassifier(
            max_depth=8,
            min_samples_leaf=100,
            random_state=42
        )

    elif model_adi == "RANDOM_FOREST":
        siniflandirici = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=100,
            random_state=42,
            n_jobs=-1
        )

    elif model_adi == "KNN":
        siniflandirici = KNeighborsClassifier(
            n_neighbors=25,
            weights="uniform",
            n_jobs=-1
        )

    elif model_adi == "NAIVE_BAYES":
        siniflandirici = GaussianNB()

    elif model_adi == "YAPAY_SINIR_AGI":
        siniflandirici = MLPClassifier(
            hidden_layer_sizes=(20,),
            activation="relu",
            solver="adam",
            max_iter=300,
            early_stopping=True,
            validation_fraction=0.10,
            random_state=42
        )

    else:
        raise ValueError(
            f"Bilinmeyen model: {model_adi}"
        )

    return Pipeline(
        steps=[
            (
                "eksik_deger",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True
                )
            ),
            (
                "olceklendirme",
                StandardScaler()
            ),
            (
                "model",
                siniflandirici
            ),
        ]
    )


def donem_verisini_getir(
    veri,
    donemler
):
    """Belirtilen donemlere ait verileri getirir."""

    return veri[
        veri["deney_donemi"].isin(
            donemler
        )
    ].copy()


def model_sonucunu_hesapla(
    model,
    egitim_verisi,
    degerlendirme_verisi
):
    """Modeli egitir ve degerlendirme sonuclarini hesaplar."""

    egitim_ozellikleri = egitim_verisi[
        OZELLIKLER
    ]

    egitim_hedefi = (
        egitim_verisi["basarili_mi"]
        .astype(int)
    )

    degerlendirme_ozellikleri = (
        degerlendirme_verisi[
            OZELLIKLER
        ]
    )

    degerlendirme_hedefi = (
        degerlendirme_verisi[
            "basarili_mi"
        ].astype(int)
    )

    degerlendirme_getirileri = (
        degerlendirme_verisi[
            "net_getiri"
        ].astype(float)
    )

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi
    )

    # Esik gelecekteki donemden degil,
    # yalnizca egitim verisinden belirlenir.
    egitim_olasiliklari = (
        model.predict_proba(
            egitim_ozellikleri
        )[:, 1]
    )

    olasilik_esigi = np.quantile(
        egitim_olasiliklari,
        HEDEF_ENGELLEME_ORANI
    )

    degerlendirme_olasiliklari = (
        model.predict_proba(
            degerlendirme_ozellikleri
        )[:, 1]
    )

    izin_verilenler = (
        degerlendirme_olasiliklari
        >= olasilik_esigi
    )

    auc = roc_auc_score(
        degerlendirme_hedefi,
        degerlendirme_olasiliklari
    )

    engelleme_orani = (
        (~izin_verilenler).mean() * 100
    )

    filtresiz_basari = (
        degerlendirme_hedefi.mean() * 100
    )

    filtreli_basari = (
        degerlendirme_hedefi[
            izin_verilenler
        ].mean() * 100
    )

    filtresiz_getiri = (
        degerlendirme_getirileri.mean()
        * 100
    )

    filtreli_getiri = (
        degerlendirme_getirileri[
            izin_verilenler
        ].mean()
        * 100
    )

    return {
        "egitim_sinyali": len(
            egitim_verisi
        ),
        "degerlendirme_sinyali": len(
            degerlendirme_verisi
        ),
        "esik": olasilik_esigi,
        "auc": auc,
        "engelleme_orani": engelleme_orani,
        "filtresiz_basari": filtresiz_basari,
        "filtreli_basari": filtreli_basari,
        "filtresiz_getiri": filtresiz_getiri,
        "filtreli_getiri": filtreli_getiri,
    }


def sonucu_yazdir(
    adim_adi,
    sonuc
):
    """Bir degerlendirme sonucunu terminalde gosterir."""

    basari_degisimi = (
        sonuc["filtreli_basari"]
        - sonuc["filtresiz_basari"]
    )

    getiri_degisimi = (
        sonuc["filtreli_getiri"]
        - sonuc["filtresiz_getiri"]
    )

    print(f"\n{adim_adi}")

    print(
        f"Egitim sinyali: "
        f"{sonuc['egitim_sinyali']:,}"
    )

    print(
        f"Degerlendirme sinyali: "
        f"{sonuc['degerlendirme_sinyali']:,}"
    )

    print(
        f"Tahmin esigi: "
        f"{sonuc['esik']:.4f}"
    )

    print(
        f"ROC-AUC: "
        f"{sonuc['auc']:.4f}"
    )

    print(
        f"Engelleme orani: "
        f"%{sonuc['engelleme_orani']:.2f}"
    )

    print(
        f"Filtresiz basari: "
        f"%{sonuc['filtresiz_basari']:.2f}"
    )

    print(
        f"Filtreli basari: "
        f"%{sonuc['filtreli_basari']:.2f}"
    )

    print(
        f"Basari degisimi: "
        f"{basari_degisimi:+.2f} puan"
    )

    print(
        f"Filtresiz ortalama getiri: "
        f"%{sonuc['filtresiz_getiri']:.4f}"
    )

    print(
        f"Filtreli ortalama getiri: "
        f"%{sonuc['filtreli_getiri']:.4f}"
    )

    print(
        f"Getiri degisimi: "
        f"{getiri_degisimi:+.4f} puan"
    )


def modelleri_karsilastir():
    """Alti modeli iki dogrulama doneminde karsilastirir."""

    veri = veriyi_getir()
    veri = deney_donemlerini_olustur(
        veri
    )

    model_adlari = {
        "LOGISTIC_REGRESSION":
            "Logistic Regression",

        "DECISION_TREE":
            "Decision Tree",

        "RANDOM_FOREST":
            "Random Forest",

        "KNN":
            "K-Nearest Neighbors",

        "NAIVE_BAYES":
            "Gaussian Naive Bayes",

        "YAPAY_SINIR_AGI":
            "Yapay Sinir Agi",
    }

    birinci_egitim = donem_verisini_getir(
        veri,
        ["EGITIM"]
    )

    birinci_dogrulama = (
        donem_verisini_getir(
            veri,
            ["DOGRULAMA"]
        )
    )

    ikinci_egitim = donem_verisini_getir(
        veri,
        [
            "EGITIM",
            "DOGRULAMA",
        ]
    )

    ikinci_dogrulama = (
        donem_verisini_getir(
            veri,
            ["IKINCIL_DOGRULAMA"]
        )
    )

    print(
        f"Toplam kullanilan sinyal: "
        f"{len(veri):,}"
    )

    print(
        "\nNihai test model karsilastirmasinda "
        "kullanilmayacaktir."
    )

    for model_kodu, model_adi in (
        model_adlari.items()
    ):
        print("\n" + "=" * 55)
        print(f"Model: {model_adi}")

        birinci_model = model_olustur(
            model_kodu
        )

        birinci_sonuc = (
            model_sonucunu_hesapla(
                model=birinci_model,
                egitim_verisi=birinci_egitim,
                degerlendirme_verisi=(
                    birinci_dogrulama
                )
            )
        )

        sonucu_yazdir(
            "1. ADIM - Birinci dogrulama",
            birinci_sonuc
        )

        ikinci_model = model_olustur(
            model_kodu
        )

        ikinci_sonuc = (
            model_sonucunu_hesapla(
                model=ikinci_model,
                egitim_verisi=ikinci_egitim,
                degerlendirme_verisi=(
                    ikinci_dogrulama
                )
            )
        )

        sonucu_yazdir(
            "2. ADIM - Ikinci dogrulama",
            ikinci_sonuc
        )


if __name__ == "__main__":
    modelleri_karsilastir()