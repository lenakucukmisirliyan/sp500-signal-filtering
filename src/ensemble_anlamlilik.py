import numpy as np
import pandas as pd

from scipy.stats import (
    chi2_contingency,
    mannwhitneyu,
    norm,
)

from src.veritabani import veritabani_baglantisi_olustur


DONEMLER = [
    (
        "DOGRULAMA",
        "Birinci dogrulama",
    ),
    (
        "IKINCIL_DOGRULAMA",
        "Ikinci dogrulama",
    ),
    (
        "NIHAI_TEST",
        "Nihai test",
    ),
]

ANLAMLILIK_DUZEYI = 0.05


def veriyi_getir():
    """Ensemble kararlarını ve gerçekleşen sonuçları getirir."""

    baglanti = veritabani_baglantisi_olustur()
    imlec = baglanti.cursor()

    try:
        imlec.execute(
            """
            SELECT
                ek.deney_donemi,
                ek.ensemble_karari,
                iss.basarili_mi,
                iss.net_getiri

            FROM ensemble_kararlari ek

            INNER JOIN islem_sinyalleri iss
                ON iss.sinyal_id =
                   ek.sinyal_id

            ORDER BY
                ek.deney_donemi,
                ek.sinyal_id;
            """
        )

        sutunlar = [
            "deney_donemi",
            "ensemble_karari",
            "basarili_mi",
            "net_getiri",
        ]

        return pd.DataFrame(
            imlec.fetchall(),
            columns=sutunlar,
        )

    finally:
        imlec.close()
        baglanti.close()


def oran_farki_testi(
    birinci_basari,
    birinci_toplam,
    ikinci_basari,
    ikinci_toplam,
):
    """
    Birinci grubun başarı oranının ikinci gruptan
    yüksek olup olmadığını tek yönlü z testiyle sınar.
    """

    birinci_oran = (
        birinci_basari
        / birinci_toplam
    )

    ikinci_oran = (
        ikinci_basari
        / ikinci_toplam
    )

    ortak_oran = (
        (
            birinci_basari
            + ikinci_basari
        )
        / (
            birinci_toplam
            + ikinci_toplam
        )
    )

    standart_hata = np.sqrt(
        ortak_oran
        * (1 - ortak_oran)
        * (
            1 / birinci_toplam
            + 1 / ikinci_toplam
        )
    )

    if standart_hata == 0:
        return 0.0, 1.0

    z_degeri = (
        birinci_oran
        - ikinci_oran
    ) / standart_hata

    # Tek yönlü test:
    # Birinci grubun oranı ikinci gruptan yüksek mi?
    p_degeri = norm.sf(z_degeri)

    return z_degeri, p_degeri


def karar_gruplari_testi(donem_verisi):
    """
    AL, NÖTR ve ALMA kararları ile gerçekleşen başarı
    arasında ilişki olup olmadığını ki-kare testiyle sınar.
    """

    karar_sirasi = [
        "AL",
        "NOTR",
        "ALMA",
    ]

    tablo = []

    for karar in karar_sirasi:
        karar_verisi = donem_verisi[
            donem_verisi[
                "ensemble_karari"
            ] == karar
        ]

        basarili = int(
            karar_verisi[
                "basarili_mi"
            ].sum()
        )

        basarisiz = (
            len(karar_verisi)
            - basarili
        )

        tablo.append(
            [
                basarili,
                basarisiz,
            ]
        )

    ki_kare, p_degeri, _, _ = (
        chi2_contingency(tablo)
    )

    return ki_kare, p_degeri


def donemi_degerlendir(
    veri,
    donem_kodu,
    donem_adi,
):
    """Bir dönemin ensemble anlamlılık sonuçlarını gösterir."""

    donem_verisi = veri[
        veri["deney_donemi"]
        == donem_kodu
    ].copy()

    donem_verisi["basarili_mi"] = (
        donem_verisi["basarili_mi"]
        .astype(bool)
    )

    donem_verisi["net_getiri"] = (
        donem_verisi["net_getiri"]
        .astype(float)
    )

    # AL ve NÖTR sinyalleri kullanılır.
    izin_verilen = donem_verisi[
        donem_verisi[
            "ensemble_karari"
        ] != "ALMA"
    ]

    # ALMA sinyalleri engellenir.
    engellenen = donem_verisi[
        donem_verisi[
            "ensemble_karari"
        ] == "ALMA"
    ]

    izin_basari_sayisi = int(
        izin_verilen[
            "basarili_mi"
        ].sum()
    )

    engellenen_basari_sayisi = int(
        engellenen[
            "basarili_mi"
        ].sum()
    )

    izin_basari_orani = (
        izin_verilen[
            "basarili_mi"
        ].mean()
        * 100
    )

    engellenen_basari_orani = (
        engellenen[
            "basarili_mi"
        ].mean()
        * 100
    )

    z_degeri, basari_p_degeri = (
        oran_farki_testi(
            birinci_basari=(
                izin_basari_sayisi
            ),
            birinci_toplam=len(
                izin_verilen
            ),
            ikinci_basari=(
                engellenen_basari_sayisi
            ),
            ikinci_toplam=len(
                engellenen
            ),
        )
    )

    # İzin verilen sinyallerin getirisi daha yüksek mi?
    _, getiri_p_degeri = mannwhitneyu(
        izin_verilen["net_getiri"],
        engellenen["net_getiri"],
        alternative="greater",
    )

    izin_getiri = (
        izin_verilen[
            "net_getiri"
        ].mean()
        * 100
    )

    engellenen_getiri = (
        engellenen[
            "net_getiri"
        ].mean()
        * 100
    )

    ki_kare, karar_p_degeri = (
        karar_gruplari_testi(
            donem_verisi
        )
    )

    print()
    print("=" * 60)
    print(donem_adi.upper())

    print()
    print("ENSEMBLE FILTRE SONUCU")
    print(
        f"Izin verilen sinyal: "
        f"{len(izin_verilen):,}"
    )
    print(
        f"Engellenen sinyal: "
        f"{len(engellenen):,}"
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
        f"Basari farki: "
        f"{izin_basari_orani - engellenen_basari_orani:+.2f} "
        f"puan"
    )
    print(
        f"Z degeri: "
        f"{z_degeri:.4f}"
    )
    print(
        f"Basari p-degeri: "
        f"{basari_p_degeri:.6f}"
    )

    if basari_p_degeri < ANLAMLILIK_DUZEYI:
        print(
            "Izin verilen sinyallerin basari orani "
            "anlamli bicimde daha yuksek."
        )
    else:
        print(
            "Basari orani farki istatistiksel "
            "olarak anlamli degil."
        )

    print()
    print("GETIRI SONUCU")
    print(
        f"Izin verilen ortalama getiri: "
        f"%{izin_getiri:.4f}"
    )
    print(
        f"Engellenen ortalama getiri: "
        f"%{engellenen_getiri:.4f}"
    )
    print(
        f"Getiri p-degeri: "
        f"{getiri_p_degeri:.6f}"
    )

    if getiri_p_degeri < ANLAMLILIK_DUZEYI:
        print(
            "Izin verilen sinyallerin getirisi "
            "anlamli bicimde daha yuksek."
        )
    else:
        print(
            "Getiri iyilesmesi istatistiksel "
            "olarak anlamli degil."
        )

    print()
    print("AL - NOTR - ALMA ILISKISI")
    print(
        f"Ki-kare degeri: "
        f"{ki_kare:.4f}"
    )
    print(
        f"Karar gruplari p-degeri: "
        f"{karar_p_degeri:.6f}"
    )

    if karar_p_degeri < ANLAMLILIK_DUZEYI:
        print(
            "Ensemble karari ile gerceklesen basari "
            "arasinda anlamli bir iliski var."
        )
    else:
        print(
            "Ensemble karari ile gerceklesen basari "
            "arasinda anlamli bir iliski bulunamadi."
        )


def ensemble_anlamliligini_hesapla():
    """Bütün dönemler için ensemble testlerini çalıştırır."""

    veri = veriyi_getir()

    for donem_kodu, donem_adi in DONEMLER:
        donemi_degerlendir(
            veri=veri,
            donem_kodu=donem_kodu,
            donem_adi=donem_adi,
        )


if __name__ == "__main__":
    ensemble_anlamliligini_hesapla()