import pandas as pd
from psycopg2.extras import execute_values

from src.veritabani import veritabani_baglantisi_olustur


KISA_ORTALAMA = 20
UZUN_ORTALAMA = 50


def spy_verisini_getir(imlec):
    """SPY fiyatlarini analiz tablosundan getirir."""

    imlec.execute(
        """
        SELECT
            afv.bar_zamani,
            afv.kapanis

        FROM
            analiz_fiyat_verileri afv,
            menkul_kiymetler mk

        WHERE afv.menkul_kiymet_id =
              mk.menkul_kiymet_id
          AND mk.sembol = 'SPY'

        ORDER BY afv.bar_zamani;
        """
    )

    veri = pd.DataFrame(
        imlec.fetchall(),
        columns=[
            "bar_zamani",
            "spy_kapanis"
        ]
    )

    veri["spy_kapanis"] = (
        veri["spy_kapanis"].astype(float)
    )

    return veri


def piyasa_kosullarini_hesapla(veri):
    """SPY ortalamalarini ve trend gucunu hesaplar."""

    veri["spy_kisa_ortalama"] = (
        veri["spy_kapanis"]
        .rolling(KISA_ORTALAMA)
        .mean()
    )

    veri["spy_uzun_ortalama"] = (
        veri["spy_kapanis"]
        .rolling(UZUN_ORTALAMA)
        .mean()
    )

    # Her bardaki fiyat hareketinin buyuklugu.
    veri["bir_barlik_hareket"] = (
        veri["spy_kapanis"]
        .diff()
        .abs()
    )

    # Son 12 bardaki baslangic-bitis farki.
    net_hareket = (
        veri["spy_kapanis"]
        .diff(12)
        .abs()
    )

    # Son 12 bardaki butun ara hareketlerin toplami.
    toplam_hareket = (
        veri["bir_barlik_hareket"]
        .rolling(12)
        .sum()
    )

    veri["spy_er12"] = (
        net_hareket
        / toplam_hareket.where(
            toplam_hareket != 0
        )
    )

    # SMA50 hesaplanamayan ilk satirlar kullanilmaz.
    veri = veri.dropna().copy()

    veri["olumlu_piyasa_mi"] = (
        veri["spy_kisa_ortalama"]
        > veri["spy_uzun_ortalama"]
    )

    # Yalnizca hesaplama sirasinda kullanilan sutunu siler.
    veri = veri.drop(
        columns=["bir_barlik_hareket"]
    )

    return veri


def piyasa_kosullarini_kaydet(imlec, veri):
    """Hesaplanan piyasa kosullarini PostgreSQL'e kaydeder."""

    imlec.execute(
        """
        TRUNCATE TABLE piyasa_kosullari;
        """
    )

    kayitlar = []

    for satir in veri.itertuples(index=False):
        kayitlar.append(
            (
                satir.bar_zamani,
                float(satir.spy_kapanis),
                float(satir.spy_kisa_ortalama),
                float(satir.spy_uzun_ortalama),
                float(satir.spy_er12),
                bool(satir.olumlu_piyasa_mi),
            )
        )

    execute_values(
        imlec,
        """
        INSERT INTO piyasa_kosullari (
            bar_zamani,
            spy_kapanis,
            spy_kisa_ortalama,
            spy_uzun_ortalama,
            spy_er12,
            olumlu_piyasa_mi
        )
        VALUES %s;
        """,
        kayitlar,
        page_size=5000
    )


def piyasa_kosullarini_hazirla():
    """SPY verisinden piyasa kosullarini hazirlar."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        spy_verisi = spy_verisini_getir(imlec)

        piyasa_kosullari = (
            piyasa_kosullarini_hesapla(
                spy_verisi
            )
        )

        piyasa_kosullarini_kaydet(
            imlec,
            piyasa_kosullari
        )

        baglanti.commit()

        olumlu_bar_sayisi = int(
            piyasa_kosullari[
                "olumlu_piyasa_mi"
            ].sum()
        )

        print(
            f"SPY fiyat satiri: "
            f"{len(spy_verisi):,}"
        )

        print(
            f"Piyasa kosulu satiri: "
            f"{len(piyasa_kosullari):,}"
        )

        print(
            f"Olumlu piyasa bari: "
            f"{olumlu_bar_sayisi:,}"
        )

    except Exception:
        if baglanti is not None:
            baglanti.rollback()

        raise

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


if __name__ == "__main__":
    piyasa_kosullarini_hazirla()