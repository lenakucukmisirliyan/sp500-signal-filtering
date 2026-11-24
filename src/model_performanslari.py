import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.makine_ogrenmesi_modeli import (
    HEDEF_ENGELLEME_ORANI,
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


def model_tahminlerini_uret(
    model,
    egitim_verisi,
    degerlendirme_verisi,
):
    """Modeli egitir ve degerlendirme donemi icin tahmin uretir."""

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
        degerlendirme_verisi["basarili_mi"]
        .astype(int)
    )

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi,
    )

    # Esik, degerlendirme doneminden bilgi sizmasini
    # engellemek icin yalnizca egitim verisinden bulunur.
    egitim_olasiliklari = model.predict_proba(
        egitim_ozellikleri
    )[:, 1]

    tahmin_esigi = np.quantile(
        egitim_olasiliklari,
        HEDEF_ENGELLEME_ORANI,
    )

    degerlendirme_olasiliklari = (
        model.predict_proba(
            degerlendirme_ozellikleri
        )[:, 1]
    )

    # 1: Model sinyale izin veriyor.
    # 0: Model sinyali engelliyor.
    tahminler = (
        degerlendirme_olasiliklari
        >= tahmin_esigi
    ).astype(int)

    return (
        degerlendirme_hedefi,
        degerlendirme_olasiliklari,
        tahminler,
        tahmin_esigi,
    )


def performansi_hesapla(
    gercek_sonuclar,
    tahmin_olasiliklari,
    tahminler,
):
    """Bir modelin siniflandirma metriklerini hesaplar."""

    dogru_negatif, yanlis_pozitif, \
        yanlis_negatif, dogru_pozitif = (
            confusion_matrix(
                gercek_sonuclar,
                tahminler,
                labels=[0, 1],
            ).ravel()
        )

    toplam_sinyal = len(
        gercek_sonuclar
    )

    engellenen_sinyal = int(
        (tahminler == 0).sum()
    )

    izin_verilen_sinyal = int(
        (tahminler == 1).sum()
    )

    return {
        "toplam_sinyal": toplam_sinyal,
        "izin_verilen_sinyal": izin_verilen_sinyal,
        "engellenen_sinyal": engellenen_sinyal,

        "accuracy": accuracy_score(
            gercek_sonuclar,
            tahminler,
        ),

        "precision": precision_score(
            gercek_sonuclar,
            tahminler,
            zero_division=0,
        ),

        "recall": recall_score(
            gercek_sonuclar,
            tahminler,
            zero_division=0,
        ),

        "f1": f1_score(
            gercek_sonuclar,
            tahminler,
            zero_division=0,
        ),

        "f1_macro": f1_score(
            gercek_sonuclar,
            tahminler,
            average="macro",
            zero_division=0,
        ),

        "roc_auc": roc_auc_score(
            gercek_sonuclar,
            tahmin_olasiliklari,
        ),

        "engelleme_orani": (
            engellenen_sinyal
            / toplam_sinyal
        ),

        "dogru_negatif": int(
            dogru_negatif
        ),

        "yanlis_pozitif": int(
            yanlis_pozitif
        ),

        "yanlis_negatif": int(
            yanlis_negatif
        ),

        "dogru_pozitif": int(
            dogru_pozitif
        ),
    }


def bir_modeli_degerlendir(
    model_kodu,
    donem_adi,
    egitim_verisi,
    degerlendirme_verisi,
):
    """Bir modeli bir dogrulama doneminde degerlendirir."""

    model = model_olustur(
        model_kodu
    )

    (
        gercek_sonuclar,
        tahmin_olasiliklari,
        tahminler,
        tahmin_esigi,
    ) = model_tahminlerini_uret(
        model=model,
        egitim_verisi=egitim_verisi,
        degerlendirme_verisi=degerlendirme_verisi,
    )

    sonuc = performansi_hesapla(
        gercek_sonuclar=gercek_sonuclar,
        tahmin_olasiliklari=(
            tahmin_olasiliklari
        ),
        tahminler=tahminler,
    )

    sonuc["model"] = (
        MODEL_ADLARI[model_kodu]
    )

    sonuc["donem"] = donem_adi
    sonuc["tahmin_esigi"] = tahmin_esigi

    return sonuc


def sonuc_tablosunu_hazirla(
    sonuclar,
):
    """Sonuclari okunabilir bir tabloya donusturur."""

    tablo = pd.DataFrame(
        sonuclar
    )

    sutunlar = [
        "donem",
        "model",
        "toplam_sinyal",
        "izin_verilen_sinyal",
        "engellenen_sinyal",
        "engelleme_orani",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "f1_macro",
        "roc_auc",
        "tahmin_esigi",
    ]

    return tablo[
        sutunlar
    ]


def karma_matrisi_yazdir(
    sonuc,
):
    """Confusion matrix degerlerini aciklar."""

    print(
        "\nConfusion matrix:"
    )

    print(
        "Dogru ALMA  "
        f"(basarisiz sinyal engellendi): "
        f"{sonuc['dogru_negatif']:,}"
    )

    print(
        "Yanlis AL   "
        f"(basarisiz sinyale izin verildi): "
        f"{sonuc['yanlis_pozitif']:,}"
    )

    print(
        "Yanlis ALMA "
        f"(basarili sinyal engellendi): "
        f"{sonuc['yanlis_negatif']:,}"
    )

    print(
        "Dogru AL    "
        f"(basarili sinyale izin verildi): "
        f"{sonuc['dogru_pozitif']:,}"
    )


def tum_modelleri_degerlendir():
    """Alti modeli iki dogrulama doneminde karsilastirir."""

    veri = veriyi_getir()

    veri = deney_donemlerini_olustur(
        veri
    )

    birinci_egitim = (
        donem_verisini_getir(
            veri,
            ["EGITIM"],
        )
    )

    birinci_dogrulama = (
        donem_verisini_getir(
            veri,
            ["DOGRULAMA"],
        )
    )

    ikinci_egitim = (
        donem_verisini_getir(
            veri,
            [
                "EGITIM",
                "DOGRULAMA",
            ],
        )
    )

    ikinci_dogrulama = (
        donem_verisini_getir(
            veri,
            ["IKINCIL_DOGRULAMA"],
        )
    )

    deneyler = [
        (
            "BIRINCI_DOGRULAMA",
            birinci_egitim,
            birinci_dogrulama,
        ),
        (
            "IKINCI_DOGRULAMA",
            ikinci_egitim,
            ikinci_dogrulama,
        ),
    ]

    sonuclar = []

    for model_kodu in MODEL_ADLARI:
        for (
            donem_adi,
            egitim_verisi,
            degerlendirme_verisi,
        ) in deneyler:

            print(
                "\n"
                + "=" * 60
            )

            print(
                f"Model: "
                f"{MODEL_ADLARI[model_kodu]}"
            )

            print(
                f"Donem: {donem_adi}"
            )

            sonuc = bir_modeli_degerlendir(
                model_kodu=model_kodu,
                donem_adi=donem_adi,
                egitim_verisi=egitim_verisi,
                degerlendirme_verisi=(
                    degerlendirme_verisi
                ),
            )

            sonuclar.append(
                sonuc
            )

            karma_matrisi_yazdir(
                sonuc
            )

    tablo = sonuc_tablosunu_hazirla(
        sonuclar
    )

    yuzde_sutunlari = [
        "engelleme_orani",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "f1_macro",
        "roc_auc",
    ]

    tablo[yuzde_sutunlari] = (
        tablo[yuzde_sutunlari]
        * 100
    )

    print(
        "\n"
        + "=" * 60
    )

    print(
        "MODEL PERFORMANS OZETI"
    )

    print(
        tablo.to_string(
            index=False,
            float_format=lambda deger: (
                f"{deger:.2f}"
            ),
        )
    )


if __name__ == "__main__":
    tum_modelleri_degerlendir()