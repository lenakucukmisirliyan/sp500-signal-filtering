import os
from pathlib import Path

import pandas as pd
import psycopg2
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from src.veritabani import veritabani_baglantisi_olustur


PROJE_KLASORU = Path(__file__).resolve().parent.parent

SEMBOL_DOSYASI = (
    PROJE_KLASORU
    / "veriler"
    / "sp500_analiz_sembolleri.csv"
)

load_dotenv(PROJE_KLASORU / ".env")


def alpaca_varliklarini_al():
    """Alpaca'da bulunan tum varlik tanimlarini getirir."""

    api_anahtari = os.getenv("ALPACA_API_KEY")
    gizli_anahtar = os.getenv("ALPACA_SECRET_KEY")

    if not api_anahtari or not gizli_anahtar:
        raise ValueError(
            "Alpaca API anahtarlari .env dosyasinda bulunamadi."
        )

    istemci = TradingClient(
        api_key=api_anahtari,
        secret_key=gizli_anahtar,
        paper=True
    )

    varliklar = istemci.get_all_assets()

    return {
        varlik.symbol: varlik
        for varlik in varliklar
    }


def sembol_listesini_oku():
    """Analiz sembollerini CSV dosyasindan okur."""

    veri = pd.read_csv(SEMBOL_DOSYASI)

    semboller = (
        veri["sembol"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )

    # SPY bir sirket degil, piyasa rejimini temsil eden ETF'dir.
    if "SPY" not in semboller:
        semboller.append("SPY")

    return sorted(set(semboller))


def kayitlari_hazirla(semboller, alpaca_varliklari):
    """Veritabani kayitlarini ve bulunamayan sembolleri hazirlar."""

    kayitlar = []
    bulunamayan_semboller = []

    for sembol in semboller:
        varlik = alpaca_varliklari.get(sembol)

        if varlik is None:
            bulunamayan_semboller.append(sembol)

            kayitlar.append(
                (
                    sembol,
                    None,
                    "ETF" if sembol == "SPY" else "HISSE",
                    None,
                    None,
                    None,
                    "USD",
                    False
                )
            )

            continue

        kayitlar.append(
            (
                sembol,
                varlik.name,
                "ETF" if sembol == "SPY" else "HISSE",
                varlik.exchange.value,
                None,
                None,
                "USD",
                varlik.status.value == "active"
            )
        )

    return kayitlar, bulunamayan_semboller


def menkul_kiymetleri_aktar():
    """S&P 500 sembollerini PostgreSQL'e aktarir."""

    baglanti = None
    imlec = None

    try:
        semboller = sembol_listesini_oku()
        alpaca_varliklari = alpaca_varliklarini_al()

        kayitlar, bulunamayan_semboller = kayitlari_hazirla(
            semboller,
            alpaca_varliklari
        )

        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        sorgu = """
            INSERT INTO menkul_kiymetler (
                sembol,
                menkul_kiymet_adi,
                varlik_turu,
                borsa,
                sektor,
                alt_sektor,
                para_birimi,
                aktif_mi
            )
            VALUES %s
            ON CONFLICT (sembol)
            DO UPDATE SET
                menkul_kiymet_adi =
                    EXCLUDED.menkul_kiymet_adi,
                varlik_turu =
                    EXCLUDED.varlik_turu,
                borsa =
                    EXCLUDED.borsa,
                para_birimi =
                    EXCLUDED.para_birimi,
                aktif_mi =
                    EXCLUDED.aktif_mi;
        """

        execute_values(
            imlec,
            sorgu,
            kayitlar,
            page_size=1000
        )

        baglanti.commit()

        print("Menkul kiymet aktarimi tamamlandi.")
        print(f"Toplam sembol: {len(semboller)}")
        print(
            f"Alpaca'da bulunan: "
            f"{len(semboller) - len(bulunamayan_semboller)}"
        )
        print(
            f"Alpaca'da bulunamayan: "
            f"{len(bulunamayan_semboller)}"
        )

        if bulunamayan_semboller:
            print(
                "Bulunamayan semboller: "
                + ", ".join(bulunamayan_semboller)
            )

    except (psycopg2.Error, ValueError) as hata:
        if baglanti is not None:
            baglanti.rollback()

        print(f"Aktarim hatasi: {hata}")

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


if __name__ == "__main__":
    menkul_kiymetleri_aktar()