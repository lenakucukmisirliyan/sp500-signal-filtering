import pandas as pd
from psycopg2.extras import execute_values

from src.veritabani import veritabani_baglantisi_olustur


SEMBOL_SINIRI = None


def sembolleri_getir(imlec):
    """Sinyal bulunan sembolleri getirir."""

    imlec.execute(
        """
        SELECT DISTINCT
            mk.sembol

        FROM
            islem_sinyalleri s,
            menkul_kiymetler mk

        WHERE s.menkul_kiymet_id =
              mk.menkul_kiymet_id

        ORDER BY mk.sembol;
        """
    )

    return [
        satir[0]
        for satir in imlec.fetchall()
    ]


def fiyat_verisini_getir(imlec, sembol):
    """Bir sembolun analiz fiyatlarini getirir."""

    imlec.execute(
        """
        SELECT
            afv.bar_zamani,
            afv.kapanis,
            afv.hacim

        FROM
            analiz_fiyat_verileri afv,
            menkul_kiymetler mk

        WHERE afv.menkul_kiymet_id =
              mk.menkul_kiymet_id
          AND mk.sembol = %s

        ORDER BY afv.bar_zamani;
        """,
        (sembol,)
    )

    veri = pd.DataFrame(
        imlec.fetchall(),
        columns=[
            "bar_zamani",
            "kapanis",
            "hacim",
        ]
    )

    veri["kapanis"] = (
        veri["kapanis"].astype(float)
    )

    veri["hacim"] = (
        veri["hacim"].astype(float)
    )

    veri["bar_zamani"] = pd.to_datetime(
        veri["bar_zamani"],
        utc=True
    )

    return veri


def sinyalleri_getir(imlec, sembol):
    """Bir sembol icin uretilen sinyalleri getirir."""

    imlec.execute(
        """
        SELECT
            s.sinyal_id,
            s.sinyal_zamani

        FROM
            islem_sinyalleri s,
            menkul_kiymetler mk

        WHERE s.menkul_kiymet_id =
              mk.menkul_kiymet_id
          AND mk.sembol = %s

        ORDER BY s.sinyal_zamani;
        """,
        (sembol,)
    )

    veri = pd.DataFrame(
        imlec.fetchall(),
        columns=[
            "sinyal_id",
            "sinyal_zamani",
        ]
    )

    veri["sinyal_zamani"] = pd.to_datetime(
        veri["sinyal_zamani"],
        utc=True
    )

    return veri


def ozellikleri_hesapla(fiyat_verisi):
    """Gecmis fiyat ve hacimden hisse ozelliklerini hesaplar."""

    veri = fiyat_verisi.copy()

    # Hesaplamalar her islem gununde yeniden baslar.
    veri["islem_tarihi"] = (
        veri["bar_zamani"]
        .dt.tz_convert("America/New_York")
        .dt.date
    )

    gruplar = veri.groupby(
        "islem_tarihi"
    )

    veri["hisse_15dk_getiri"] = (
        veri["kapanis"]
        / gruplar["kapanis"].shift(3)
        - 1
    )

    veri["hisse_60dk_getiri"] = (
        veri["kapanis"]
        / gruplar["kapanis"].shift(12)
        - 1
    )

    veri["bir_barlik_getiri"] = (
        gruplar["kapanis"]
        .pct_change(fill_method=None)
    )

    veri["hisse_60dk_volatilite"] = (
        veri.groupby("islem_tarihi")[
            "bir_barlik_getiri"
        ]
        .transform(
            lambda seri: seri.rolling(12).std()
        )
    )

    veri["ortalama_hacim_20"] = (
        veri.groupby("islem_tarihi")[
            "hacim"
        ]
        .transform(
            lambda seri: seri.rolling(20).mean()
        )
    )

    veri["hacim_orani_20"] = (
        veri["hacim"]
        / veri["ortalama_hacim_20"].where(
            veri["ortalama_hacim_20"] != 0
        )
    )

    return veri[
        [
            "bar_zamani",
            "hisse_15dk_getiri",
            "hisse_60dk_getiri",
            "hisse_60dk_volatilite",
            "hacim_orani_20",
        ]
    ]


def kayit_degerini_hazirla(deger):
    """Bos Pandas degerlerini PostgreSQL icin None yapar."""

    if pd.isna(deger):
        return None

    return float(deger)


def ozellikleri_kaydet(imlec, sinyal_ozellikleri):
    """Hesaplanan sinyal ozelliklerini PostgreSQL'e kaydeder."""

    kayitlar = []

    for satir in sinyal_ozellikleri.itertuples(
        index=False
    ):
        kayitlar.append(
            (
                int(satir.sinyal_id),

                kayit_degerini_hazirla(
                    satir.hisse_15dk_getiri
                ),

                kayit_degerini_hazirla(
                    satir.hisse_60dk_getiri
                ),

                kayit_degerini_hazirla(
                    satir.hisse_60dk_volatilite
                ),

                kayit_degerini_hazirla(
                    satir.hacim_orani_20
                ),
            )
        )

    execute_values(
        imlec,
        """
        INSERT INTO sinyal_ozellikleri (
            sinyal_id,
            hisse_15dk_getiri,
            hisse_60dk_getiri,
            hisse_60dk_volatilite,
            hacim_orani_20
        )
        VALUES %s

        ON CONFLICT (sinyal_id)
        DO UPDATE SET
            hisse_15dk_getiri =
                EXCLUDED.hisse_15dk_getiri,

            hisse_60dk_getiri =
                EXCLUDED.hisse_60dk_getiri,

            hisse_60dk_volatilite =
                EXCLUDED.hisse_60dk_volatilite,

            hacim_orani_20 =
                EXCLUDED.hacim_orani_20;
        """,
        kayitlar,
        page_size=1000
    )


def bir_sembolu_hazirla(imlec, sembol):
    """Bir sembolun sinyal ozelliklerini hesaplar."""

    fiyat_verisi = fiyat_verisini_getir(
        imlec,
        sembol
    )

    sinyaller = sinyalleri_getir(
        imlec,
        sembol
    )

    hesaplanan_ozellikler = (
        ozellikleri_hesapla(
            fiyat_verisi
        )
    )

    sinyal_ozellikleri = sinyaller.merge(
        hesaplanan_ozellikler,
        left_on="sinyal_zamani",
        right_on="bar_zamani",
        how="left"
    )

    sinyal_ozellikleri = (
        sinyal_ozellikleri.drop(
            columns=["bar_zamani"]
        )
    )

    ozellikleri_kaydet(
        imlec,
        sinyal_ozellikleri
    )

    return len(sinyal_ozellikleri)


def tum_ozellikleri_hazirla():
    """Tum sembollerin sinyal ozelliklerini hazirlar."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        semboller = sembolleri_getir(
            imlec
        )

        if SEMBOL_SINIRI is not None:
            semboller = semboller[
                :SEMBOL_SINIRI
            ]

        print(
            f"Hazirlanacak sembol sayisi: "
            f"{len(semboller)}"
        )

        for sira, sembol in enumerate(
            semboller,
            start=1
        ):
            satir_sayisi = (
                bir_sembolu_hazirla(
                    imlec,
                    sembol
                )
            )

            baglanti.commit()

            print(
                f"[{sira}/{len(semboller)}] "
                f"{sembol}: "
                f"{satir_sayisi:,} sinyal"
            )

        print(
            "Sinyal ozellikleri hazirlandi."
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
    tum_ozellikleri_hazirla()