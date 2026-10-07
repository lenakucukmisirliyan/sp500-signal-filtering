from pathlib import Path

import pandas as pd


PROJE_KLASORU = Path(__file__).resolve().parent.parent

KAYNAK_DOSYA = (
    PROJE_KLASORU
    / "veriler"
    / "sp500_tarihsel_bilesenler_2024-04-08.csv"
)

CIKTI_DOSYA = (
    PROJE_KLASORU
    / "veriler"
    / "sp500_analiz_sembolleri.csv"
)


def sembolleri_ayir(sembol_metni):
    """Virgulle ayrilmis sembolleri bir kumeye donusturur."""

    return {
        sembol.strip()
        for sembol in sembol_metni.split(",")
        if sembol.strip()
    }


def tarihteki_sembolleri_bul(veri, hedef_tarih):
    """Hedef tarihte gecerli olan son endeks listesini bulur."""

    uygun_satirlar = veri[
        veri["date"] <= hedef_tarih
    ]

    if uygun_satirlar.empty:
        raise ValueError(
            f"{hedef_tarih.date()} tarihinden once liste bulunamadi."
        )

    son_satir = uygun_satirlar.iloc[-1]

    return sembolleri_ayir(
        son_satir["tickers"]
    )


def analiz_sembollerini_hazirla():
    """Analiz doneminde endekste bulunan tum sembolleri belirler."""

    baslangic_tarihi = pd.Timestamp("2023-01-03")
    bitis_tarihi = pd.Timestamp("2024-03-28")

    veri = pd.read_csv(KAYNAK_DOSYA)

    veri["date"] = pd.to_datetime(
        veri["date"],
        format="%Y-%m-%d"
    )

    veri = veri.sort_values("date")

    baslangic_sembolleri = tarihteki_sembolleri_bul(
        veri,
        baslangic_tarihi
    )

    bitis_sembolleri = tarihteki_sembolleri_bul(
        veri,
        bitis_tarihi
    )

    donem_satirlari = veri[
        (veri["date"] > baslangic_tarihi)
        & (veri["date"] <= bitis_tarihi)
    ]

    tum_semboller = set(baslangic_sembolleri)

    for sembol_metni in donem_satirlari["tickers"]:
        tum_semboller.update(
            sembolleri_ayir(sembol_metni)
        )

    eklenen_semboller = (
        bitis_sembolleri - baslangic_sembolleri
    )

    cikan_semboller = (
        baslangic_sembolleri - bitis_sembolleri
    )

    cikti = pd.DataFrame({
        "sembol": sorted(tum_semboller)
    })

    cikti.to_csv(
        CIKTI_DOSYA,
        index=False,
        encoding="utf-8"
    )

    print(
        f"2023-01-03 endeks sembolu: "
        f"{len(baslangic_sembolleri)}"
    )

    print(
        f"2024-03-28 endeks sembolu: "
        f"{len(bitis_sembolleri)}"
    )

    print(
        f"Donem boyunca gorulen toplam sembol: "
        f"{len(tum_semboller)}"
    )

    print(
        f"Baslangica gore eklenen sembol: "
        f"{len(eklenen_semboller)}"
    )

    print(
        f"Baslangica gore cikan sembol: "
        f"{len(cikan_semboller)}"
    )

    print(
        f"\nOlusturulan dosya: {CIKTI_DOSYA}"
    )


if __name__ == "__main__":
    analiz_sembollerini_hazirla()