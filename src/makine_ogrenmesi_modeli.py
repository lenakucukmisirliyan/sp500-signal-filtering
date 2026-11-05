import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.veritabani import veritabani_baglantisi_olustur


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

        veri["sinyal_zamani"] = pd.to_datetime(
            veri["sinyal_zamani"],
            utc=True
        )

        return veri

    finally:
        imlec.close()
        baglanti.close()


def deney_donemlerini_olustur(veri):
    """Verileri dort kronolojik doneme ayirir."""

    veri = veri.copy()

    veri["deney_donemi"] = (
        veri["veri_donemi"]
    )

    mart_baslangici = pd.Timestamp(
        "2024-03-01",
        tz="UTC"
    )

    test_satirlari = (
        veri["veri_donemi"] == "TEST"
    )

    veri.loc[
        test_satirlari
        & (
            veri["sinyal_zamani"]
            < mart_baslangici
        ),
        "deney_donemi"
    ] = "IKINCIL_DOGRULAMA"

    veri.loc[
        test_satirlari
        & (
            veri["sinyal_zamani"]
            >= mart_baslangici
        ),
        "deney_donemi"
    ] = "NIHAI_TEST"

    return veri


def donemleri_birlestir(
    veri,
    donemler
):
    """Bir veya daha fazla donemin verilerini birlestirir."""

    donem_verisi = veri[
        veri["deney_donemi"].isin(
            donemler
        )
    ].copy()

    ozellikler = (
        donem_verisi[OZELLIKLER]
        .astype(float)
    )

    hedef = (
        donem_verisi["basarili_mi"]
        .astype(int)
    )

    getiriler = (
        donem_verisi["net_getiri"]
        .astype(float)
    )

    return ozellikler, hedef, getiriler


def model_olustur():
    """Random Forest model ve veri hazirlama adimlarini olusturur."""

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
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    min_samples_leaf=100,
                    random_state=42,
                    n_jobs=-1
                )
            ),
        ]
    )


def sonuclari_goster(
    hedef,
    getiriler,
    olasiliklar,
    esik
):
    """Filtresiz ve filtreli sonuclari gosterir."""

    izin_verilenler = (
        olasiliklar >= esik
    )

    engelleme_orani = (
        (~izin_verilenler).mean()
        * 100
    )

    filtresiz_basari = (
        hedef.mean()
        * 100
    )

    filtreli_basari = (
        hedef[
            izin_verilenler
        ].mean()
        * 100
    )

    filtresiz_getiri = (
        getiriler.mean()
        * 100
    )

    filtreli_getiri = (
        getiriler[
            izin_verilenler
        ].mean()
        * 100
    )

    print(
        f"Gercek engelleme orani: "
        f"%{engelleme_orani:.2f}"
    )

    print(
        f"Filtresiz basari: "
        f"%{filtresiz_basari:.2f}"
    )

    print(
        f"Filtreli basari: "
        f"%{filtreli_basari:.2f}"
    )

    print(
        f"Basari degisimi: "
        f"{filtreli_basari - filtresiz_basari:+.2f} puan"
    )

    print(
        f"Filtresiz ortalama getiri: "
        f"%{filtresiz_getiri:.4f}"
    )

    print(
        f"Filtreli ortalama getiri: "
        f"%{filtreli_getiri:.4f}"
    )

    print(
        f"Getiri degisimi: "
        f"{filtreli_getiri - filtresiz_getiri:+.4f} puan"
    )


def walk_forward_adimi(
    veri,
    egitim_donemleri,
    degerlendirme_donemi,
    adim_adi
):
    """Modeli gecmis donemlerle egitir ve sonraki donemde degerlendirir."""

    (
        egitim_ozellikleri,
        egitim_hedefi,
        _
    ) = donemleri_birlestir(
        veri,
        egitim_donemleri
    )

    (
        degerlendirme_ozellikleri,
        degerlendirme_hedefi,
        degerlendirme_getirileri
    ) = donemleri_birlestir(
        veri,
        [degerlendirme_donemi]
    )

    model = model_olustur()

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi
    )

    # Esik yalnizca gecmis egitim verisindeki
    # tahmin olasiliklarindan belirlenir.
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

    auc = roc_auc_score(
        degerlendirme_hedefi,
        degerlendirme_olasiliklari
    )

    print()
    print("=" * 50)
    print(adim_adi)

    print(
        "Egitim donemleri: "
        + ", ".join(egitim_donemleri)
    )

    print(
        f"Egitim sinyali: "
        f"{len(egitim_ozellikleri):,}"
    )

    print(
        f"Degerlendirme sinyali: "
        f"{len(degerlendirme_ozellikleri):,}"
    )

    print(
        f"Gecmis veriden belirlenen esik: "
        f"{olasilik_esigi:.4f}"
    )

    print(
        f"ROC-AUC: "
        f"{auc:.4f}"
    )

    sonuclari_goster(
        hedef=degerlendirme_hedefi,
        getiriler=degerlendirme_getirileri,
        olasiliklar=degerlendirme_olasiliklari,
        esik=olasilik_esigi
    )


def modeli_calistir():
    """Uc adimli walk-forward degerlendirmesini calistirir."""

    veri = veriyi_getir()

    veri = deney_donemlerini_olustur(
        veri
    )

    print(
        f"Toplam kullanilan sinyal: "
        f"{len(veri):,}"
    )

    walk_forward_adimi(
        veri=veri,
        egitim_donemleri=[
            "EGITIM",
        ],
        degerlendirme_donemi="DOGRULAMA",
        adim_adi="1. ADIM - Birinci dogrulama"
    )

    walk_forward_adimi(
        veri=veri,
        egitim_donemleri=[
            "EGITIM",
            "DOGRULAMA",
        ],
        degerlendirme_donemi="IKINCIL_DOGRULAMA",
        adim_adi="2. ADIM - Ikinci dogrulama"
    )

    walk_forward_adimi(
        veri=veri,
        egitim_donemleri=[
            "EGITIM",
            "DOGRULAMA",
            "IKINCIL_DOGRULAMA",
        ],
        degerlendirme_donemi="NIHAI_TEST",
        adim_adi="3. ADIM - Mart 2024 nihai test"
    )


if __name__ == "__main__":
    modeli_calistir()