import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src.alpaca_verisi import ornek_veri_indir
from src.veritabani import veritabani_baglantisi_olustur


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


def bos_degeri_duzelt(deger):
    """Pandas bos degerlerini PostgreSQL icin None degerine cevirir."""

    if pd.isna(deger):
        return None

    return deger


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


def fiyat_verilerini_aktar():
    """AAPL verilerini indirir ve PostgreSQL'e aktarir."""

    baglanti = None
    imlec = None

    try:
        veri = ornek_veri_indir()

        if veri.empty:
            print("Aktarilacak veri bulunamadi.")
            return

        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        menkul_kiymet_id = menkul_kiymet_id_bul(
            imlec,
            "AAPL"
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
            DO NOTHING;
        """

        execute_values(
            imlec,
            ekleme_sorgusu,
            kayitlar,
            page_size=1000
        )

        eklenen_satir_sayisi = imlec.rowcount

        baglanti.commit()

        print("\nVeri aktarimi basarili.")
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


if __name__ == "__main__":
    fiyat_verilerini_aktar()