from src.analiz_verisi_hazirla import (
    bir_sembolu_hazirla
)
from src.veritabani import (
    veritabani_baglantisi_olustur
)


def bekleyen_sembolleri_getir():
    """Analiz verisi eksik veya henuz hazirlanmamis sembolleri getirir."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        imlec.execute(
            """
            WITH beklenen_satirlar AS (
                SELECT
                    mk.menkul_kiymet_id,
                    mk.sembol,

                    SUM(
                        pt.beklenen_bar_sayisi
                    ) AS beklenen_satir_sayisi

                FROM menkul_kiymetler mk

                INNER JOIN gunluk_veri_kalitesi gvk
                    ON gvk.menkul_kiymet_id =
                        mk.menkul_kiymet_id

                INNER JOIN piyasa_takvimi pt
                    ON pt.islem_tarihi =
                        gvk.islem_tarihi

                WHERE gvk.nihai_kalite_durumu IN (
                    'TUTULDU',
                    'DOLDURULACAK'
                )

                GROUP BY
                    mk.menkul_kiymet_id,
                    mk.sembol
            ),

            mevcut_satirlar AS (
                SELECT
                    menkul_kiymet_id,
                    COUNT(*) AS mevcut_satir_sayisi

                FROM analiz_fiyat_verileri

                GROUP BY menkul_kiymet_id
            )

            SELECT
                bs.sembol,
                bs.beklenen_satir_sayisi,
                COALESCE(
                    ms.mevcut_satir_sayisi,
                    0
                ) AS mevcut_satir_sayisi

            FROM beklenen_satirlar bs

            LEFT JOIN mevcut_satirlar ms
                ON ms.menkul_kiymet_id =
                    bs.menkul_kiymet_id

            WHERE COALESCE(
                ms.mevcut_satir_sayisi,
                0
            ) <> bs.beklenen_satir_sayisi

            ORDER BY bs.sembol;
            """
        )

        return imlec.fetchall()

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


if __name__ == "__main__":
    bekleyen_semboller = (
        bekleyen_sembolleri_getir()
    )

    toplam_sembol = len(
        bekleyen_semboller
    )

    if toplam_sembol == 0:
        print(
            "Hazirlanmasi gereken sembol bulunamadi."
        )

    else:
        print(
            f"Hazirlanacak sembol sayisi: "
            f"{toplam_sembol}"
        )

        for sira, (
            sembol,
            beklenen_satir,
            mevcut_satir
        ) in enumerate(
            bekleyen_semboller,
            start=1
        ):
            print()
            print(
                f"[{sira}/{toplam_sembol}] "
                f"{sembol}"
            )

            print(
                f"Beklenen satir: "
                f"{beklenen_satir:,} | "
                f"Mevcut satir: "
                f"{mevcut_satir:,}"
            )

            bir_sembolu_hazirla(
                sembol
            )

        print()
        print(
            "Toplu analiz verisi hazirlama "
            "calismasi tamamlandi."
        )