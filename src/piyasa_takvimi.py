from datetime import date

import pandas as pd
import pandas_market_calendars as mcal

from psycopg2.extras import execute_values
from src.veritabani import veritabani_baglantisi_olustur


ANALIZ_BASLANGIC_TARIHI = date(2023, 1, 3)
ANALIZ_BITIS_TARIHI = date(2024, 3, 28)
BAR_SURESI_DAKIKA = 5


def nyse_takvimini_olustur(
    baslangic_tarihi=ANALIZ_BASLANGIC_TARIHI,
    bitis_tarihi=ANALIZ_BITIS_TARIHI,
):

    nyse = mcal.get_calendar("NYSE")

    takvim = nyse.schedule(
        start_date=baslangic_tarihi,
        end_date=bitis_tarihi,
    ).copy()

    takvim.index.name = "islem_tarihi"
    takvim = takvim.reset_index()

    takvim["islem_tarihi"] = (
        pd.to_datetime(takvim["islem_tarihi"]).dt.date
    )

    seans_suresi = (
        takvim["market_close"]
        - takvim["market_open"]
    )

    takvim["beklenen_bar_sayisi"] = (
        seans_suresi
        / pd.Timedelta(minutes=BAR_SURESI_DAKIKA)
    ).astype(int)

    return takvim

def piyasa_takvimini_aktar():
    """NYSE takvimini PostgreSQL'e aktarir."""

    takvim = nyse_takvimini_olustur()

    kayitlar = []

    for satir in takvim.itertuples(index=False):
        kayitlar.append(
            (
                satir.islem_tarihi,
                satir.market_open.to_pydatetime(),
                satir.market_close.to_pydatetime(),
                int(satir.beklenen_bar_sayisi),
                bool(satir.beklenen_bar_sayisi < 78),
            )
        )

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        execute_values(
            imlec,
            """
            INSERT INTO piyasa_takvimi (
                islem_tarihi,
                piyasa_acilis_zamani,
                piyasa_kapanis_zamani,
                beklenen_bar_sayisi,
                erken_kapanis_mi
            )
            VALUES %s
            ON CONFLICT (islem_tarihi)
            DO UPDATE SET
                piyasa_acilis_zamani =
                    EXCLUDED.piyasa_acilis_zamani,

                piyasa_kapanis_zamani =
                    EXCLUDED.piyasa_kapanis_zamani,

                beklenen_bar_sayisi =
                    EXCLUDED.beklenen_bar_sayisi,

                erken_kapanis_mi =
                    EXCLUDED.erken_kapanis_mi;
            """,
            kayitlar
        )

        baglanti.commit()

        print("Piyasa takvimi aktarildi.")

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
    piyasa_takvimini_aktar()