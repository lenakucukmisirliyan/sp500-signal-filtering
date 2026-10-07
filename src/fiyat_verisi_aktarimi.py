import argparse
from datetime import datetime, timezone

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src.alpaca_verisi import fiyat_verisi_indir
from src.veritabani import veritabani_baglantisi_olustur


def tarih_metnini_cevir(tarih_metni):
    """YYYY-AA-GG bicimindeki tarihi UTC datetime degerine cevirir."""

    return datetime.strptime(
        tarih_metni,
        "%Y-%m-%d"
    ).replace(tzinfo=timezone.utc)


def menkul_kiymet_id_bul(imlec, sembol):
    """Sembolun menkul_kiymet_id degerini veritabanindan bulur."""

    imlec.execute(
        """
        SELECT menkul_kiymet_id
        FROM menkul_kiymetler
        WHERE sembol = %s;
        """,
        (sembol,)
    )

    sonuc = imlec.fetchone()

    if sonuc is None:
        raise ValueError(
            f"{sembol} menkul_kiymetler tablosunda bulunamadi."
        )

    return sonuc[0]


def fiyat_verilerini_hazirla(veri, menkul_kiymet_id):
    """Alpaca verilerini PostgreSQL'e uygun kayitlara donusturur."""

    kayitlar = []

    for satir in veri.itertuples(index=False):
        kayit = (
            menkul_kiymet_id,
            satir.timestamp.to_pydatetime(),
            5,
            float(satir.open),
            float(satir.high),
            float(satir.low),
            float(satir.close),
            int(satir.volume),
            (
                int(satir.trade_count)
                if not pd.isna(satir.trade_count)
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

        kayitlar.append(kayit)

    return kayitlar


def fiyat_verilerini_aktar(sembol, baslangic, bitis):
    """Belirtilen sembol ve tarih araligini PostgreSQL'e aktarir."""

    baglanti = None
    imlec = None

    try:
        sembol = sembol.upper()

        print(
            f"Veri indiriliyor: {sembol} | "
            f"{baslangic.date()} - {bitis.date()}"
        )

        veri = fiyat_verisi_indir(
            semboller=[sembol],
            baslangic=baslangic,
            bitis=bitis,
            zaman_araligi_dakika=5
        )

        if veri.empty:
            print("Aktarilacak veri bulunamadi.")
            return

        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        menkul_kiymet_id = menkul_kiymet_id_bul(
            imlec,
            sembol
        )

        kayitlar = fiyat_verilerini_hazirla(
            veri,
            menkul_kiymet_id
        )

        ekleme_sorgusu = """
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
            DO NOTHING
            RETURNING 1;
        """

        eklenen_kayitlar = execute_values(
            imlec,
            ekleme_sorgusu,
            kayitlar,
            page_size=1000,
            fetch=True
        )

        eklenen_satir_sayisi = len(eklenen_kayitlar)

        baglanti.commit()

        print("Veri aktarimi basarili.")
        print(f"Hazirlanan satir: {len(kayitlar)}")
        print(f"Yeni eklenen satir: {eklenen_satir_sayisi}")

    except (psycopg2.Error, ValueError) as hata:
        if baglanti is not None:
            baglanti.rollback()

        print(f"Veri aktarim hatasi: {hata}")

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def komut_satiri_argumanlarini_al():
    """Terminalden sembol ve tarih bilgilerini alir."""

    parser = argparse.ArgumentParser(
        description="Alpaca fiyat verilerini PostgreSQL'e aktarir."
    )

    parser.add_argument(
        "--sembol",
        required=True,
        help="Hisse sembolu. Ornek: AAPL"
    )

    parser.add_argument(
        "--baslangic",
        required=True,
        help="Baslangic tarihi. Bicim: YYYY-AA-GG"
    )

    parser.add_argument(
        "--bitis",
        required=True,
        help="Bitis tarihi. Bicim: YYYY-AA-GG"
    )

    return parser.parse_args()


if __name__ == "__main__":
    argumanlar = komut_satiri_argumanlarini_al()

    fiyat_verilerini_aktar(
        sembol=argumanlar.sembol,
        baslangic=tarih_metnini_cevir(
            argumanlar.baslangic
        ),
        bitis=tarih_metnini_cevir(
            argumanlar.bitis
        )
    )