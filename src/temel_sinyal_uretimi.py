from datetime import date

import pandas as pd
from psycopg2.extras import execute_values

from src.veritabani import veritabani_baglantisi_olustur


KISA_PERIYOT = 20
UZUN_PERIYOT = 50
BEKLETME_BAR_SAYISI = 12
ISLEM_MALIYETI_ORANI = 0.001


def fiyat_verilerini_getir(imlec, sembol):
    """Bir sembolun temizlenmis fiyat verilerini getirir."""

    imlec.execute(
        """
        SELECT
            afv.menkul_kiymet_id,
            afv.bar_zamani,
            afv.acilis,
            afv.kapanis,
            afv.dolduruldu_mu
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

    sutunlar = [
        "menkul_kiymet_id",
        "bar_zamani",
        "acilis",
        "kapanis",
        "dolduruldu_mu",
    ]

    veri = pd.DataFrame(
        imlec.fetchall(),
        columns=sutunlar
    )

    if veri.empty:
        return veri

    veri["bar_zamani"] = pd.to_datetime(
        veri["bar_zamani"],
        utc=True
    )

    veri["acilis"] = veri["acilis"].astype(float)
    veri["kapanis"] = veri["kapanis"].astype(float)

    # Islem tarihini New York saatine gore belirler.
    veri["islem_tarihi"] = (
        veri["bar_zamani"]
        .dt.tz_convert("America/New_York")
        .dt.date
    )

    return veri


def veri_donemini_belirle(sinyal_tarihi):
    """Sinyalin egitim, dogrulama veya test donemini belirler."""

    if sinyal_tarihi <= date(2023, 8, 31):
        return "EGITIM"

    if sinyal_tarihi <= date(2023, 12, 31):
        return "DOGRULAMA"

    return "TEST"


def sinyalleri_hesapla(veri):
    """SMA20 ve SMA50 kesisiminden alim sinyalleri uretir."""

    veri["kisa_ortalama"] = (
        veri["kapanis"]
        .rolling(KISA_PERIYOT)
        .mean()
    )

    veri["uzun_ortalama"] = (
        veri["kapanis"]
        .rolling(UZUN_PERIYOT)
        .mean()
    )

    # Kisa ortalama uzun ortalamayi asagi yönden
    # yukari gectiginde alim sinyali olusur.
    veri["alim_sinyali"] = (
        (
            veri["kisa_ortalama"]
            > veri["uzun_ortalama"]
        )
        & (
            veri["kisa_ortalama"].shift(1)
            <= veri["uzun_ortalama"].shift(1)
        )
    )

    sinyaller = []
    son_cikis_sirasi = -1

    sinyal_siralari = veri.index[
        veri["alim_sinyali"]
    ].tolist()

    for sinyal_sirasi in sinyal_siralari:
        giris_sirasi = sinyal_sirasi + 1
        cikis_sirasi = (
            sinyal_sirasi
            + BEKLETME_BAR_SAYISI
        )

        # Veri setinin sonunda giris veya cikis yoksa kullanilmaz.
        if cikis_sirasi >= len(veri):
            continue

        # Onceki islem devam ederken yeni islem acilmaz.
        if giris_sirasi <= son_cikis_sirasi:
            continue

        sinyal_satiri = veri.iloc[sinyal_sirasi]
        giris_satiri = veri.iloc[giris_sirasi]
        cikis_satiri = veri.iloc[cikis_sirasi]

        # Giris ve cikis ayni islem gununde olmalidir.
        if (
            giris_satiri["islem_tarihi"]
            != cikis_satiri["islem_tarihi"]
        ):
            continue

        giris_fiyati = giris_satiri["acilis"]
        cikis_fiyati = cikis_satiri["kapanis"]

        brut_getiri = (
            cikis_fiyati / giris_fiyati
        ) - 1

        net_getiri = (
            brut_getiri
            - ISLEM_MALIYETI_ORANI
        )

        # Gosterge penceresinde veya islem araliginda
        # doldurulmus bar bulunup bulunmadigini kontrol eder.
        pencere_baslangici = max(
            0,
            sinyal_sirasi - UZUN_PERIYOT + 1
        )

        doldurulmus_veri_var_mi = bool(
            veri.iloc[
                pencere_baslangici:
                cikis_sirasi + 1
            ]["dolduruldu_mu"].any()
        )

        sinyaller.append(
            (
                int(sinyal_satiri["menkul_kiymet_id"]),
                sinyal_satiri["bar_zamani"].to_pydatetime(),
                giris_satiri["bar_zamani"].to_pydatetime(),
                cikis_satiri["bar_zamani"].to_pydatetime(),
                float(giris_fiyati),
                float(cikis_fiyati),
                float(sinyal_satiri["kisa_ortalama"]),
                float(sinyal_satiri["uzun_ortalama"]),
                float(brut_getiri),
                ISLEM_MALIYETI_ORANI,
                float(net_getiri),
                bool(net_getiri > 0),
                veri_donemini_belirle(
                    sinyal_satiri["islem_tarihi"]
                ),
                doldurulmus_veri_var_mi,
            )
        )

        son_cikis_sirasi = cikis_sirasi

    return sinyaller


def sinyalleri_kaydet(imlec, sembol, sinyaller):
    """Eski sinyalleri siler ve yeni sinyalleri kaydeder."""

    imlec.execute(
        """
        DELETE FROM islem_sinyalleri
        WHERE menkul_kiymet_id = (
            SELECT menkul_kiymet_id
            FROM menkul_kiymetler
            WHERE sembol = %s
        );
        """,
        (sembol,)
    )

    if not sinyaller:
        return

    execute_values(
        imlec,
        """
        INSERT INTO islem_sinyalleri (
            menkul_kiymet_id,
            sinyal_zamani,
            giris_zamani,
            cikis_zamani,
            giris_fiyati,
            cikis_fiyati,
            kisa_ortalama,
            uzun_ortalama,
            brut_getiri,
            islem_maliyeti_orani,
            net_getiri,
            basarili_mi,
            veri_donemi,
            doldurulmus_veri_var_mi
        )
        VALUES %s;
        """,
        sinyaller,
        page_size=1000
    )


def bir_sembol_icin_sinyal_uret(sembol):
    """Bir sembol icin sinyalleri hesaplar ve kaydeder."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        veri = fiyat_verilerini_getir(
            imlec,
            sembol
        )

        if veri.empty:
            print(f"{sembol}: Fiyat verisi bulunamadi.")
            return

        sinyaller = sinyalleri_hesapla(veri)

        sinyalleri_kaydet(
            imlec,
            sembol,
            sinyaller
        )

        baglanti.commit()

        basarili_sinyal_sayisi = sum(
            sinyal[11]
            for sinyal in sinyaller
        )

        if sinyaller:
            basari_orani = (
                basarili_sinyal_sayisi
                / len(sinyaller)
                * 100
            )
        else:
            basari_orani = 0

        print(f"Sembol: {sembol}")
        print(f"Fiyat satiri: {len(veri):,}")
        print(f"Uretilen sinyal: {len(sinyaller):,}")
        print(
            f"Basarili sinyal: "
            f"{basarili_sinyal_sayisi:,}"
        )
        print(
            f"Basari orani: "
            f"%{basari_orani:.2f}"
        )

    except Exception as hata:
        if baglanti is not None:
            baglanti.rollback()

        print(f"{sembol}: Hata: {hata}")

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


if __name__ == "__main__":
    bir_sembol_icin_sinyal_uret("AAPL")