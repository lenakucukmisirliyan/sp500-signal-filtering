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
            "spy_kapanis",
        ]
    )

    veri["spy_kapanis"] = (
        veri["spy_kapanis"].astype(float)
    )

    return veri


def piyasa_kosullarini_hesapla(veri):
    """SPY piyasa gostergelerini hesaplar."""

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

    # Son 12 bardaki ara hareketlerin toplami.
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

    # Bar zamanini New York islem tarihine cevirir.
    veri["islem_tarihi"] = (
        pd.to_datetime(
            veri["bar_zamani"],
            utc=True
        )
        .dt.tz_convert("America/New_York")
        .dt.date
    )

    # Ayni islem gunundeki 12 bar onceki kapanisi bulur.
    onceki_kapanis = (
        veri.groupby("islem_tarihi")[
            "spy_kapanis"
        ]
        .shift(12)
    )

    # Son 12 bar, yaklasik 60 dakikalik getiri.
    veri["spy_60dk_getiri"] = (
        veri["spy_kapanis"]
        / onceki_kapanis
        - 1
    )

    # SMA50 ve ER12 hesaplanamayan ilk satirlar kullanilmaz.
    veri = veri.dropna(
        subset=[
            "spy_kisa_ortalama",
            "spy_uzun_ortalama",
            "spy_er12",
        ]
    ).copy()

    # SPY'nin SMA20'ye oransal uzakligi.
    veri["spy_sma20_farki_orani"] = (
        (
            veri["spy_kapanis"]
            - veri["spy_kisa_ortalama"]
        )
        / veri["spy_kisa_ortalama"]
    )

    veri["sma20_ustu_mu"] = (
        veri["spy_sma20_farki_orani"] >= 0
    )

    # Yalnizca hesaplama sirasinda kullanilan sutunlar.
    veri = veri.drop(
        columns=[
            "bir_barlik_hareket",
            "islem_tarihi",
        ]
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
                float(satir.spy_sma20_farki_orani),
                (
                    float(satir.spy_60dk_getiri)
                    if not pd.isna(
                        satir.spy_60dk_getiri
                    )
                    else None
                ),
                bool(satir.sma20_ustu_mu),
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
            spy_sma20_farki_orani,
            spy_60dk_getiri,
            sma20_ustu_mu
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

        sma20_ustu_bar_sayisi = int(
            piyasa_kosullari[
                "sma20_ustu_mu"
            ].sum()
        )

        getiri_hesaplanan_bar = int(
            piyasa_kosullari[
                "spy_60dk_getiri"
            ].notna()
            .sum()
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
            f"SMA20 ustundeki bar: "
            f"{sma20_ustu_bar_sayisi:,}"
        )

        print(
            f"60 dakikalik getiri hesaplanan bar: "
            f"{getiri_hesaplanan_bar:,}"
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