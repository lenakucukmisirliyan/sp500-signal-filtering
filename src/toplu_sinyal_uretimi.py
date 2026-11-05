from src.temel_sinyal_uretimi import (
    bir_sembol_icin_sinyal_uret
)
from src.veritabani import (
    veritabani_baglantisi_olustur
)


# Ilk kontrolde yalnizca 5 sembol kullanilir.
# Tum hisseler icin daha sonra None yapilacak.
SEMBOL_SINIRI = None


def sembolleri_getir():
    """Analiz verisi bulunan hisse sembollerini getirir."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        imlec.execute(
            """
            SELECT DISTINCT
                mk.sembol
            FROM
                analiz_fiyat_verileri afv,
                menkul_kiymetler mk
            WHERE afv.menkul_kiymet_id =
                  mk.menkul_kiymet_id
              AND mk.sembol <> 'SPY'
            ORDER BY mk.sembol;
            """
        )

        return [
            satir[0]
            for satir in imlec.fetchall()
        ]

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def tum_sinyalleri_uret():
    """Analiz verisi bulunan hisseler icin sinyal uretir."""

    semboller = sembolleri_getir()

    if SEMBOL_SINIRI is not None:
        semboller = semboller[:SEMBOL_SINIRI]

    toplam_sembol = len(semboller)

    print(
        f"Sinyal uretilecek sembol sayisi: "
        f"{toplam_sembol}"
    )

    for sira, sembol in enumerate(
        semboller,
        start=1
    ):
        print()
        print(
            f"[{sira}/{toplam_sembol}] "
            f"{sembol}"
        )

        bir_sembol_icin_sinyal_uret(
            sembol
        )

    print()
    print("Toplu sinyal uretimi tamamlandi.")


if __name__ == "__main__":
    tum_sinyalleri_uret()