from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from psycopg2.extras import execute_values

from src.veritabani import veritabani_baglantisi_olustur


PROJE_KLASORU = Path(__file__).resolve().parent.parent

UYELIK_DOSYASI = (
    PROJE_KLASORU
    / "veriler"
    / "sp500_tarihsel_bilesenler_2024-04-08.csv"
)

ANALIZ_BASLANGIC_TARIHI = date(2023, 1, 3)
ANALIZ_BITIS_TARIHI = date(2024, 3, 28)


def sembol_metnini_ayir(sembol_metni):
    """Virgulle ayrilmis sembol metnini kumeye donusturur."""

    if pd.isna(sembol_metni):
        return set()

    return {
        sembol.strip().upper()
        for sembol in str(sembol_metni).split(",")
        if sembol.strip()
    }


def tarihsel_listeyi_oku():
    """Tarihsel S&P 500 uyelik dosyasini okur."""

    if not UYELIK_DOSYASI.exists():
        raise FileNotFoundError(
            f"Tarihsel uyelik dosyasi bulunamadi: {UYELIK_DOSYASI}"
        )

    veri = pd.read_csv(UYELIK_DOSYASI)

    gerekli_sutunlar = {"date", "tickers"}

    eksik_sutunlar = gerekli_sutunlar - set(veri.columns)

    if eksik_sutunlar:
        raise ValueError(
            "CSV dosyasinda eksik sutunlar var: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    veri["date"] = pd.to_datetime(veri["date"]).dt.date

    veri = (
        veri.sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )

    return veri


def uyelik_araliklarini_hesapla(veri):
    """Gunluk endeks listelerinden uyelik baslangic ve bitislerini hesaplar."""

    baslangic_satirlari = veri[
        veri["date"] <= ANALIZ_BASLANGIC_TARIHI
    ]

    if baslangic_satirlari.empty:
        raise ValueError(
            "Analiz baslangic tarihinden once bir endeks listesi bulunamadi."
        )

    baslangic_satiri = baslangic_satirlari.iloc[-1]

    aktif_semboller = sembol_metnini_ayir(
        baslangic_satiri["tickers"]
    )

    uyelik_baslangiclari = {
        sembol: ANALIZ_BASLANGIC_TARIHI
        for sembol in aktif_semboller
    }

    uyelik_araliklari = []

    donem_satirlari = veri[
        (veri["date"] > ANALIZ_BASLANGIC_TARIHI)
        & (veri["date"] <= ANALIZ_BITIS_TARIHI)
    ]

    onceki_semboller = aktif_semboller

    for _, satir in donem_satirlari.iterrows():
        tarih = satir["date"]
        mevcut_semboller = sembol_metnini_ayir(satir["tickers"])

        eklenen_semboller = mevcut_semboller - onceki_semboller
        cikarilan_semboller = onceki_semboller - mevcut_semboller

        for sembol in sorted(cikarilan_semboller):
            baslangic_tarihi = uyelik_baslangiclari.pop(sembol)

            uyelik_araliklari.append(
                (
                    sembol,
                    baslangic_tarihi,
                    tarih,
                )
            )

        for sembol in sorted(eklenen_semboller):
            uyelik_baslangiclari[sembol] = tarih

        onceki_semboller = mevcut_semboller

    analiz_sonrasi_tarih = ANALIZ_BITIS_TARIHI + timedelta(days=1)

    for sembol, baslangic_tarihi in uyelik_baslangiclari.items():
        uyelik_araliklari.append(
            (
                sembol,
                baslangic_tarihi,
                analiz_sonrasi_tarih,
            )
        )

    return sorted(
        uyelik_araliklari,
        key=lambda kayit: (kayit[0], kayit[1]),
    )


def menkul_kiymet_idlerini_getir(imlec):
    """Sembol ve menkul kiymet kimliklerini veritabanindan getirir."""

    imlec.execute(
        """
        SELECT
            sembol,
            menkul_kiymet_id
        FROM menkul_kiymetler;
        """
    )

    return {
        sembol: menkul_kiymet_id
        for sembol, menkul_kiymet_id in imlec.fetchall()
    }


def endeks_uyeliklerini_aktar():
    """Hesaplanan S&P 500 uyeliklerini PostgreSQL'e aktarir."""

    veri = tarihsel_listeyi_oku()
    uyelik_araliklari = uyelik_araliklarini_hesapla(veri)

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        sembol_idleri = menkul_kiymet_idlerini_getir(imlec)

        bulunamayan_semboller = sorted(
            {
                sembol
                for sembol, _, _ in uyelik_araliklari
                if sembol not in sembol_idleri
            }
        )

        if bulunamayan_semboller:
            raise ValueError(
                "Menkul kiymetler tablosunda bulunamayan semboller: "
                + ", ".join(bulunamayan_semboller)
            )

        aktarilacak_kayitlar = [
            (
                sembol_idleri[sembol],
                "SP500",
                baslangic_tarihi,
                bitis_tarihi,
            )
            for sembol, baslangic_tarihi, bitis_tarihi
            in uyelik_araliklari
        ]

        # Dosya tekrar calistirilirsa once eski SP500 uyeliklerini temizler.
        imlec.execute(
            """
            DELETE FROM endeks_uyelikleri
            WHERE endeks_kodu = 'SP500';
            """
        )

        execute_values(
            imlec,
            """
            INSERT INTO endeks_uyelikleri (
                menkul_kiymet_id,
                endeks_kodu,
                baslangic_tarihi,
                bitis_tarihi
            )
            VALUES %s;
            """,
            aktarilacak_kayitlar,
        )

        baglanti.commit()

        benzersiz_semboller = {
            sembol
            for sembol, _, _ in uyelik_araliklari
        }

        print("Endeks uyelik aktarimi tamamlandi.")
        print(f"Benzersiz sembol: {len(benzersiz_semboller)}")
        print(f"Uyelik araligi: {len(uyelik_araliklari)}")
        print(
            "Analiz donemi: "
            f"{ANALIZ_BASLANGIC_TARIHI} - {ANALIZ_BITIS_TARIHI}"
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
    endeks_uyeliklerini_aktar()