import os
from datetime import datetime, timezone
from pathlib import Path

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from dotenv import load_dotenv


# Projenin ana klasorunu bulur.
PROJE_KLASORU = Path(__file__).resolve().parent.parent

# Ana klasordeki .env dosyasini okur.
load_dotenv(PROJE_KLASORU / ".env")


def alpaca_baglantisi_olustur():
    """Alpaca Market Data istemcisini olusturur."""

    api_anahtari = os.getenv("ALPACA_API_KEY")
    gizli_anahtar = os.getenv("ALPACA_SECRET_KEY")

    if not api_anahtari or not gizli_anahtar:
        raise ValueError(
            "ALPACA_API_KEY veya ALPACA_SECRET_KEY "
            ".env dosyasinda bulunamadi."
        )

    return StockHistoricalDataClient(
        api_key=api_anahtari,
        secret_key=gizli_anahtar
    )


def fiyat_verisi_indir(
    semboller,
    baslangic,
    bitis,
    zaman_araligi_dakika=5
):
    """Belirtilen sembol ve tarihler icin fiyat verisi indirir."""

    istemci = alpaca_baglantisi_olustur()

    veri_kaynagi = os.getenv(
        "ALPACA_FEED",
        "sip"
    ).lower()

    fiyat_duzeltmesi = os.getenv(
        "ALPACA_ADJUSTMENT",
        "all"
    ).lower()

    istek = StockBarsRequest(
        symbol_or_symbols=semboller,
        timeframe=TimeFrame(
            zaman_araligi_dakika,
            TimeFrameUnit.Minute
        ),
        start=baslangic,
        end=bitis,
        feed=DataFeed(veri_kaynagi),
        adjustment=Adjustment(fiyat_duzeltmesi)
    )

    sonuc = istemci.get_stock_bars(istek)

    return sonuc.df.reset_index()


def ornek_veri_indir():
    """AAPL icin kucuk bir ornek veri indirir."""

    veri = fiyat_verisi_indir(
        semboller=["AAPL"],
        baslangic=datetime(
            2023, 1, 3,
            tzinfo=timezone.utc
        ),
        bitis=datetime(
            2023, 1, 6,
            tzinfo=timezone.utc
        ),
        zaman_araligi_dakika=5
    )

    print("Indirilen ilk 10 satir:")
    print(veri.head(10))

    print(f"\nToplam satir sayisi: {len(veri)}")

    if not veri.empty:
        print(
            f"Ilk bar zamani: "
            f"{veri['timestamp'].min()}"
        )
        print(
            f"Son bar zamani: "
            f"{veri['timestamp'].max()}"
        )

    return veri


if __name__ == "__main__":
    ornek_veri_indir()