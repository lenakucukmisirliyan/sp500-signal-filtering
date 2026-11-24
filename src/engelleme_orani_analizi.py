from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.makine_ogrenmesi_modeli import (
    OZELLIKLER,
    deney_donemlerini_olustur,
    donem_verisini_getir,
    model_olustur,
    veriyi_getir,
)


MODEL_ADLARI = {
    "LOGISTIC_REGRESSION": "Logistic Regression",
    "DECISION_TREE": "Decision Tree",
    "RANDOM_FOREST": "Random Forest",
    "KNN": "K-Nearest Neighbors",
    "NAIVE_BAYES": "Gaussian Naive Bayes",
    "YAPAY_SINIR_AGI": "Yapay Sinir Agi",
}


ENGELLEME_ORANLARI = [
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
]


PROJE_KLASORU = (
    Path(__file__).resolve().parent.parent
)

SONUC_KLASORU = (
    PROJE_KLASORU / "raporlar"
)

SONUC_DOSYASI = (
    SONUC_KLASORU
    / "engelleme_orani_analizi.csv"
)


def modeli_egit(
    model_kodu,
    egitim_verisi,
    degerlendirme_verisi,
):
    """Modeli egitir ve olasilik tahminlerini uretir."""

    model = model_olustur(
        model_kodu
    )

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

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi,
    )

    egitim_olasiliklari = (
        model.predict_proba(
            egitim_ozellikleri
        )[:, 1]
    )

    degerlendirme_olasiliklari = (
        model.predict_proba(
            degerlendirme_ozellikleri
        )[:, 1]
    )

    return (
        egitim_olasiliklari,
        degerlendirme_olasiliklari,
    )


def bir_orani_hesapla(
    model_adi,
    donem_adi,
    hedef_engelleme_orani,
    egitim_olasiliklari,
    degerlendirme_olasiliklari,
    degerlendirme_verisi,
):
    """Bir model ve engelleme orani icin sonuclari hesaplar."""

    gercek_sonuclar = (
        degerlendirme_verisi["basarili_mi"]
        .astype(int)
        .reset_index(drop=True)
    )

    getiriler = (
        degerlendirme_verisi["net_getiri"]
        .astype(float)
        .reset_index(drop=True)
    )

    # Esik yalnizca gecmis egitim verisinden bulunur.
    tahmin_esigi = np.quantile(
        egitim_olasiliklari,
        hedef_engelleme_orani,
    )

    # Esigin altindaki sinyaller engellenir.
    izin_verilenler = (
        degerlendirme_olasiliklari
        >= tahmin_esigi
    )

    tahminler = (
        izin_verilenler.astype(int)
    )

    engellenenler = (
        ~izin_verilenler
    )

    toplam_sinyal = len(
        gercek_sonuclar
    )

    gercek_engelleme_orani = (
        engellenenler.mean()
    )

    filtresiz_basari = (
        gercek_sonuclar.mean()
    )

    filtreli_basari = (
        gercek_sonuclar[
            izin_verilenler
        ].mean()
    )

    engellenen_basari = (
        gercek_sonuclar[
            engellenenler
        ].mean()
    )

    filtresiz_getiri = (
        getiriler.mean()
    )

    filtreli_getiri = (
        getiriler[
            izin_verilenler
        ].mean()
    )

    # Basarisiz sinyallerin ne kadarinin
    # dogru bicimde engellendigini gosterir.
    basarisiz_sinyaller = (
        gercek_sonuclar == 0
    )

    basarisiz_yakalama_orani = (
        (
            engellenenler
            & basarisiz_sinyaller
        ).sum()
        / basarisiz_sinyaller.sum()
    )

    return {
        "donem": donem_adi,
        "model": model_adi,

        "hedef_engelleme_yuzde": (
            hedef_engelleme_orani * 100
        ),

        "gercek_engelleme_yuzde": (
            gercek_engelleme_orani * 100
        ),

        "toplam_sinyal": toplam_sinyal,

        "izin_verilen_sinyal": int(
            izin_verilenler.sum()
        ),

        "engellenen_sinyal": int(
            engellenenler.sum()
        ),

        "tahmin_esigi": tahmin_esigi,

        "accuracy_yuzde": (
            accuracy_score(
                gercek_sonuclar,
                tahminler,
            )
            * 100
        ),

        "precision_yuzde": (
            precision_score(
                gercek_sonuclar,
                tahminler,
                zero_division=0,
            )
            * 100
        ),

        "recall_yuzde": (
            recall_score(
                gercek_sonuclar,
                tahminler,
                zero_division=0,
            )
            * 100
        ),

        "f1_yuzde": (
            f1_score(
                gercek_sonuclar,
                tahminler,
                zero_division=0,
            )
            * 100
        ),

        "f1_macro_yuzde": (
            f1_score(
                gercek_sonuclar,
                tahminler,
                average="macro",
                zero_division=0,
            )
            * 100
        ),

        "roc_auc_yuzde": (
            roc_auc_score(
                gercek_sonuclar,
                degerlendirme_olasiliklari,
            )
            * 100
        ),

        "basarisiz_yakalama_yuzde": (
            basarisiz_yakalama_orani
            * 100
        ),

        "filtresiz_basari_yuzde": (
            filtresiz_basari * 100
        ),

        "filtreli_basari_yuzde": (
            filtreli_basari * 100
        ),

        "basari_degisimi_puan": (
            (
                filtreli_basari
                - filtresiz_basari
            )
            * 100
        ),

        "engellenen_basari_yuzde": (
            engellenen_basari * 100
        ),

        "filtresiz_getiri_yuzde": (
            filtresiz_getiri * 100
        ),

        "filtreli_getiri_yuzde": (
            filtreli_getiri * 100
        ),

        "getiri_degisimi_puan": (
            (
                filtreli_getiri
                - filtresiz_getiri
            )
            * 100
        ),
    }


def analiz_donemlerini_hazirla(
    veri,
):
    """Iki zaman sirali dogrulama deneyini hazirlar."""

    return [
        (
            "BIRINCI_DOGRULAMA",

            donem_verisini_getir(
                veri,
                ["EGITIM"],
            ),

            donem_verisini_getir(
                veri,
                ["DOGRULAMA"],
            ),
        ),

        (
            "IKINCI_DOGRULAMA",

            donem_verisini_getir(
                veri,
                [
                    "EGITIM",
                    "DOGRULAMA",
                ],
            ),

            donem_verisini_getir(
                veri,
                ["IKINCIL_DOGRULAMA"],
            ),
        ),
    ]


def ozet_tablosunu_yazdir(
    sonuclar,
):
    """Karar vermek icin gerekli kisa tabloyu gosterir."""

    sutunlar = [
        "donem",
        "model",
        "hedef_engelleme_yuzde",
        "gercek_engelleme_yuzde",
        "basarisiz_yakalama_yuzde",
        "filtreli_basari_yuzde",
        "basari_degisimi_puan",
        "filtreli_getiri_yuzde",
        "getiri_degisimi_puan",
        "f1_macro_yuzde",
    ]

    print(
        "\n"
        + "=" * 80
    )

    print(
        "ENGELLEME ORANI ANALIZI"
    )

    print(
        sonuclar[
            sutunlar
        ].to_string(
            index=False,
            float_format=lambda deger: (
                f"{deger:.2f}"
            ),
        )
    )


def engelleme_oranlarini_karsilastir():
    """Alti model icin yuzde 5-30 oranlarini karsilastirir."""

    veri = veriyi_getir()

    veri = deney_donemlerini_olustur(
        veri
    )

    deneyler = (
        analiz_donemlerini_hazirla(
            veri
        )
    )

    sonuclar = []

    for model_kodu, model_adi in (
        MODEL_ADLARI.items()
    ):
        for (
            donem_adi,
            egitim_verisi,
            degerlendirme_verisi,
        ) in deneyler:

            print(
                f"{model_adi} | "
                f"{donem_adi} hesaplaniyor..."
            )

            (
                egitim_olasiliklari,
                degerlendirme_olasiliklari,
            ) = modeli_egit(
                model_kodu=model_kodu,
                egitim_verisi=egitim_verisi,
                degerlendirme_verisi=(
                    degerlendirme_verisi
                ),
            )

            for oran in ENGELLEME_ORANLARI:
                sonuc = bir_orani_hesapla(
                    model_adi=model_adi,
                    donem_adi=donem_adi,
                    hedef_engelleme_orani=oran,
                    egitim_olasiliklari=(
                        egitim_olasiliklari
                    ),
                    degerlendirme_olasiliklari=(
                        degerlendirme_olasiliklari
                    ),
                    degerlendirme_verisi=(
                        degerlendirme_verisi
                    ),
                )

                sonuclar.append(
                    sonuc
                )

    sonuc_tablosu = pd.DataFrame(
        sonuclar
    )

    ozet_tablosunu_yazdir(
        sonuc_tablosu
    )

    SONUC_KLASORU.mkdir(
        exist_ok=True
    )

    sonuc_tablosu.to_csv(
        SONUC_DOSYASI,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )

    print(
        f"\nTum sonuclar kaydedildi: "
        f"{SONUC_DOSYASI}"
    )


if __name__ == "__main__":
    engelleme_oranlarini_karsilastir()