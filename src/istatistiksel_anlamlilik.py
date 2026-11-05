import numpy as np

from scipy.stats import chi2_contingency
from scipy.stats import ttest_ind

from src.makine_ogrenmesi_modeli import (
    HEDEF_ENGELLEME_ORANI,
    OZELLIKLER,
    deney_donemlerini_olustur,
    model_olustur,
    veriyi_getir,
)


KURAL_ESIGI = -0.001


def donem_verisini_al(
    veri,
    donemler
):
    """Istenen deney donemlerinin satirlarini getirir."""

    return veri[
        veri["deney_donemi"].isin(
            donemler
        )
    ].copy()


def filtreyi_test_et(
    filtre_adi,
    hedef,
    getiriler,
    izin_verilenler
):
    """Izin verilen ve engellenen sinyalleri istatistiksel olarak karsilastirir."""

    izin_hedef = hedef[
        izin_verilenler
    ]

    engellenen_hedef = hedef[
        ~izin_verilenler
    ]

    izin_getiri = getiriler[
        izin_verilenler
    ]

    engellenen_getiri = getiriler[
        ~izin_verilenler
    ]

    izin_basarili = int(
        izin_hedef.sum()
    )

    izin_basarisiz = int(
        len(izin_hedef)
        - izin_basarili
    )

    engellenen_basarili = int(
        engellenen_hedef.sum()
    )

    engellenen_basarisiz = int(
        len(engellenen_hedef)
        - engellenen_basarili
    )

    basari_tablosu = np.array(
        [
            [
                izin_basarili,
                izin_basarisiz,
            ],
            [
                engellenen_basarili,
                engellenen_basarisiz,
            ],
        ]
    )

    _, basari_p_degeri, _, _ = (
        chi2_contingency(
            basari_tablosu
        )
    )

    _, getiri_p_degeri = ttest_ind(
        izin_getiri,
        engellenen_getiri,
        equal_var=False,
        alternative="greater"
    )

    izin_basari_orani = (
        izin_hedef.mean()
        * 100
    )

    engellenen_basari_orani = (
        engellenen_hedef.mean()
        * 100
    )

    izin_ortalama_getiri = (
        izin_getiri.mean()
        * 100
    )

    engellenen_ortalama_getiri = (
        engellenen_getiri.mean()
        * 100
    )

    engelleme_orani = (
        (~izin_verilenler).mean()
        * 100
    )

    print()
    print(f"Filtre: {filtre_adi}")

    print(
        f"Engelleme orani: "
        f"%{engelleme_orani:.2f}"
    )

    print(
        f"Izin verilen basari: "
        f"%{izin_basari_orani:.2f}"
    )

    print(
        f"Engellenen basari: "
        f"%{engellenen_basari_orani:.2f}"
    )

    print(
        f"Basari p-degeri: "
        f"{basari_p_degeri:.6f}"
    )

    print(
        f"Izin verilen ortalama getiri: "
        f"%{izin_ortalama_getiri:.4f}"
    )

    print(
        f"Engellenen ortalama getiri: "
        f"%{engellenen_ortalama_getiri:.4f}"
    )

    print(
        f"Getiri p-degeri: "
        f"{getiri_p_degeri:.6f}"
    )

    if basari_p_degeri < 0.05:
        print(
            "Basari farki istatistiksel olarak anlamli."
        )
    else:
        print(
            "Basari farki istatistiksel olarak anlamli degil."
        )

    if getiri_p_degeri < 0.05:
        print(
            "Getiri farki istatistiksel olarak anlamli."
        )
    else:
        print(
            "Getiri farki istatistiksel olarak anlamli degil."
        )


def bir_donemi_test_et(
    veri,
    egitim_donemleri,
    degerlendirme_donemi,
    donem_adi
):
    """Kural ve ML filtrelerini bir sonraki donemde test eder."""

    egitim_verisi = donem_verisini_al(
        veri,
        egitim_donemleri
    )

    degerlendirme_verisi = (
        donem_verisini_al(
            veri,
            [degerlendirme_donemi]
        )
    )

    egitim_ozellikleri = (
        egitim_verisi[OZELLIKLER]
        .astype(float)
    )

    egitim_hedefi = (
        egitim_verisi["basarili_mi"]
        .astype(int)
    )

    degerlendirme_ozellikleri = (
        degerlendirme_verisi[
            OZELLIKLER
        ]
        .astype(float)
    )

    hedef = (
        degerlendirme_verisi[
            "basarili_mi"
        ]
        .astype(int)
        .to_numpy()
    )

    getiriler = (
        degerlendirme_verisi[
            "net_getiri"
        ]
        .astype(float)
        .to_numpy()
    )

    model = model_olustur()

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi
    )

    egitim_olasiliklari = (
        model.predict_proba(
            egitim_ozellikleri
        )[:, 1]
    )

    ml_esigi = np.quantile(
        egitim_olasiliklari,
        HEDEF_ENGELLEME_ORANI
    )

    ml_olasiliklari = (
        model.predict_proba(
            degerlendirme_ozellikleri
        )[:, 1]
    )

    ml_izin_verilenler = (
        ml_olasiliklari
        >= ml_esigi
    )

    spy_getirisi = (
        degerlendirme_verisi[
            "spy_60dk_getiri"
        ]
        .astype(float)
    )

    kural_izin_verilenler = (
        spy_getirisi.isna()
        | (
            spy_getirisi
            >= KURAL_ESIGI
        )
    ).to_numpy()

    print()
    print("=" * 55)
    print(donem_adi)

    filtreyi_test_et(
        filtre_adi="Kural tabanli filtre",
        hedef=hedef,
        getiriler=getiriler,
        izin_verilenler=kural_izin_verilenler
    )

    filtreyi_test_et(
        filtre_adi="Random Forest",
        hedef=hedef,
        getiriler=getiriler,
        izin_verilenler=ml_izin_verilenler
    )


def testleri_calistir():
    """Uc walk-forward doneminde anlamlilik testlerini calistirir."""

    veri = veriyi_getir()

    veri = deney_donemlerini_olustur(
        veri
    )

    bir_donemi_test_et(
        veri=veri,
        egitim_donemleri=[
            "EGITIM",
        ],
        degerlendirme_donemi="DOGRULAMA",
        donem_adi="1. ADIM - Birinci dogrulama"
    )

    bir_donemi_test_et(
        veri=veri,
        egitim_donemleri=[
            "EGITIM",
            "DOGRULAMA",
        ],
        degerlendirme_donemi="IKINCIL_DOGRULAMA",
        donem_adi="2. ADIM - Ikinci dogrulama"
    )

    bir_donemi_test_et(
        veri=veri,
        egitim_donemleri=[
            "EGITIM",
            "DOGRULAMA",
            "IKINCIL_DOGRULAMA",
        ],
        degerlendirme_donemi="NIHAI_TEST",
        donem_adi="3. ADIM - Mart 2024 nihai test"
    )


if __name__ == "__main__":
    testleri_calistir()