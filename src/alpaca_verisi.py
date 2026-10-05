import os
from datetime import datetime, timezone
from pathlib import Path

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from dotenv import load_dotenv


# Projenin ana klasörünü bulur.
PROJE_KLASORU = Path(__file__).resolve().parent.parent

# Ana klasördeki .env dosyasını okur.
load_dotenv(PROJE_KLASORU / ".env")


def alpaca_baglantisi_olustur():
    api_anahtari = os.getenv("ALPACA_API_KEY")
    gizli_anahtar = os.getenv("ALPACA_SECRET_KEY")

    if not api_anahtari or not gizli_anahtar:
        raise ValueError(
            "ALPACA_API_KEY veya ALPACA_SECRET_KEY .env dosyasında bulunamadı."
        )

    return StockHistoricalDataClient(
        api_key=api_anahtari,
        secret_key=gizli_anahtar
    )


def ornek_veri_indir():
    istemci = alpaca_baglantisi_olustur()

    istek = StockBarsRequest(
        symbol_or_symbols=["AAPL"],
        timeframe=TimeFrame(5, TimeFrameUnit.Minute),
        start=datetime(2023, 1, 3, tzinfo=timezone.utc),
        end=datetime(2023, 1, 6, tzinfo=timezone.utc),
        feed=DataFeed.SIP,
        adjustment=Adjustment.ALL
    )

    sonuc = istemci.get_stock_bars(istek)

    veri = sonuc.df.reset_index()

    print("İndirilen ilk 10 satır:")
    print(veri.head(10))

    print(f"\nToplam satır sayısı: {len(veri)}")

    if not veri.empty:
        print(f"İlk bar zamanı: {veri['timestamp'].min()}")
        print(f"Son bar zamanı: {veri['timestamp'].max()}")

    return veri


if __name__ == "__main__":
    ornek_veri_indir()