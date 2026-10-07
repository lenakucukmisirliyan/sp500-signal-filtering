from datetime import date

import pandas as pd
import pandas_market_calendars as mcal


ANALIZ_BASLANGIC_TARIHI = date(2023, 1, 3)
ANALIZ_BITIS_TARIHI = date(2024, 3, 28)
BAR_SURESI_DAKIKA = 5


def nyse_takvimini_olustur(
    baslangic_tarihi=ANALIZ_BASLANGIC_TARIHI,
    bitis_tarihi=ANALIZ_BITIS_TARIHI,
):
    """NYSE islem gunlerini ve seans saatlerini olusturur."""

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


def takvimi_goster():
    """NYSE takviminin ozetini terminalde gosterir."""

    takvim = nyse_takvimini_olustur()

    print(f"Toplam islem gunu: {len(takvim)}")

    print("\nBeklenen bar sayisi dagilimi:")

    dagilim = (
        takvim.groupby("beklenen_bar_sayisi")
        .size()
        .reset_index(name="gun_sayisi")
    )

    print(dagilim.to_string(index=False))

    erken_kapanislar = takvim[
        takvim["beklenen_bar_sayisi"] < 78
    ]

    print("\nErken kapanis gunleri:")

    if erken_kapanislar.empty:
        print("Erken kapanis gunu bulunamadi.")
    else:
        print(
            erken_kapanislar[
                [
                    "islem_tarihi",
                    "market_open",
                    "market_close",
                    "beklenen_bar_sayisi",
                ]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    takvimi_goster()