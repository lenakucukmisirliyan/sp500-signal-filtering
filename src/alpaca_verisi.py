import os
from pathlib import Path

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from dotenv import load_dotenv


PROJE_KLASORU = Path(__file__).resolve().parent.parent

load_dotenv(PROJE_KLASORU / ".env")


def alpaca_baglantisi_olustur():

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
