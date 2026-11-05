from datetime import datetime, timezone

import pandas as pd
from psycopg2.extras import execute_values

from src.alpaca_verisi import fiyat_verisi_indir
from src.veritabani import veritabani_baglantisi_olustur


BASLANGIC_TARIHI = datetime(
    2023,
    1,
    3,
    tzinfo=timezone.utc
)

BITIS_TARIHI = datetime(
    2024,
    4,
    1,
    tzinfo=timezone.utc
)

GRUP_BUYUKLUGU = 20
ZAMAN_ARALIGI_DAKIKA = 5


def sonraki_ayin_ilk_gunu(tarih):
    """Verilen tarihten sonraki ayin ilk gununu bulur."""

    if tarih.month == 12:
        return datetime(
            tarih.year + 1,
            1,
            1,
            tzinfo=timezone.utc
        )

    return datetime(
        tarih.year,
        tarih.month + 1,
        1,
        tzinfo=timezone.utc
    )


def aylik_tarih_araliklarini_olustur():
    """Analiz donemini aylik parcalara ayirir."""

    tarih_araliklari = []
    parca_baslangici = BASLANGIC_TARIHI

    while parca_baslangici < BITIS_TARIHI:
        parca_bitisi = min(
            sonraki_ayin_ilk_gunu(
                parca_baslangici
            ),
            BITIS_TARIHI
        )

        tarih_araliklari.append(
            (
                parca_baslangici,
                parca_bitisi
            )
        )

        parca_baslangici = parca_bitisi

    return tarih_araliklari


def menkul_kiymetleri_getir():
    """Veritabanindaki menkul kiymetleri getirir."""

    baglanti = veritabani_baglantisi_olustur()
    imlec = baglanti.cursor()

    imlec.execute(
        """
        SELECT
            menkul_kiymet_id,
            sembol
        FROM menkul_kiymetler
        ORDER BY sembol;
        """
    )

    menkul_kiymetler = imlec.fetchall()

    imlec.close()
    baglanti.close()

    return menkul_kiymetler


def gruplara_ayir(liste):
    """Listeyi 20'serli gruplara ayirir."""

    gruplar = []

    for baslangic in range(
        0,
        len(liste),
        GRUP_BUYUKLUGU
    ):
        gruplar.append(
            liste[
                baslangic:
                baslangic + GRUP_BUYUKLUGU
            ]
        )

    return gruplar


def fiyat_verilerini_hazirla(
    veri,
    sembol_idleri
):
    """Alpaca verilerini PostgreSQL kayitlarina donusturur."""

    kayitlar = []

    for satir in veri.itertuples(index=False):
        menkul_kiymet_id = sembol_idleri[
            satir.symbol
        ]

        kayitlar.append(
            (
                menkul_kiymet_id,
                satir.timestamp.to_pydatetime(),
                ZAMAN_ARALIGI_DAKIKA,
                float(satir.open),
                float(satir.high),
                float(satir.low),
                float(satir.close),
                int(satir.volume),
                (
                    int(satir.trade_count)
                    if not pd.isna(
                        satir.trade_count
                    )
                    else None
                ),
                (
                    float(satir.vwap)
                    if not pd.isna(satir.vwap)
                    else None
                ),
                "ALPACA_SIP",
                "ALL"
            )
        )

    return kayitlar


def fiyat_verilerini_kaydet(kayitlar):
    """Hazirlanan fiyat kayitlarini PostgreSQL'e ekler."""

    if not kayitlar:
        return 0

    baglanti = veritabani_baglantisi_olustur()
    imlec = baglanti.cursor()

    try:
        execute_values(
            imlec,
            """
            INSERT INTO ham_fiyat_verileri (
                menkul_kiymet_id,
                bar_zamani,
                zaman_araligi_dakika,
                acilis,
                en_yuksek,
                en_dusuk,
                kapanis,
                hacim,
                islem_sayisi,
                hacim_agirlikli_ortalama_fiyat,
                veri_kaynagi,
                fiyat_duzeltmesi
            )
            VALUES %s
            ON CONFLICT (
                menkul_kiymet_id,
                bar_zamani,
                zaman_araligi_dakika
            )
            DO NOTHING;
            """,
            kayitlar,
            page_size=5000
        )

        baglanti.commit()

        return len(kayitlar)

    except Exception:
        baglanti.rollback()
        raise

    finally:
        imlec.close()
        baglanti.close()


def toplu_fiyat_verilerini_aktar():
    """Tum menkul kiymetlerin fiyat verilerini aktarir."""

    menkul_kiymetler = menkul_kiymetleri_getir()
    tarih_araliklari = (
        aylik_tarih_araliklarini_olustur()
    )

    sembol_idleri = {
        sembol: menkul_kiymet_id
        for menkul_kiymet_id, sembol
        in menkul_kiymetler
    }

    gruplar = gruplara_ayir(
        menkul_kiymetler
    )

    toplam_grup = (
        len(gruplar)
        * len(tarih_araliklari)
    )

    sira = 0

    for baslangic, bitis in tarih_araliklari:
        for grup in gruplar:
            sira += 1

            semboller = [
                sembol
                for _, sembol in grup
            ]

            print(
                f"[{sira}/{toplam_grup}] "
                f"{baslangic.date()} - "
                f"{bitis.date()} | "
                f"{len(semboller)} sembol"
            )

            veri = fiyat_verisi_indir(
                semboller=semboller,
                baslangic=baslangic,
                bitis=bitis,
                zaman_araligi_dakika=(
                    ZAMAN_ARALIGI_DAKIKA
                )
            )

            kayitlar = fiyat_verilerini_hazirla(
                veri,
                sembol_idleri
            )

            fiyat_verilerini_kaydet(
                kayitlar
            )

    print("Fiyat verisi aktarimi tamamlandi.")


if __name__ == "__main__":
    toplu_fiyat_verilerini_aktar()