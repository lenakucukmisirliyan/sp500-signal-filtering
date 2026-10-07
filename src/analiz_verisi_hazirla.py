import argparse

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from src.veritabani import veritabani_baglantisi_olustur


def sembol_id_bul(imlec, sembol):
    """Sembolun veritabanindaki kimlik numarasini bulur."""

    imlec.execute(
        """
        SELECT menkul_kiymet_id
        FROM menkul_kiymetler
        WHERE sembol = %s;
        """,
        (sembol,)
    )

    sonuc = imlec.fetchone()

    if sonuc is None:
        raise ValueError(
            f"{sembol} menkul_kiymetler tablosunda bulunamadi."
        )

    return sonuc[0]


def kullanilacak_gunleri_getir(
    imlec,
    menkul_kiymet_id
):
    """Analizde tutulacak gunleri ve piyasa saatlerini getirir."""

    imlec.execute(
        """
        SELECT
            gvk.islem_tarihi,
            pt.piyasa_acilis_zamani,
            pt.piyasa_kapanis_zamani,
            gvk.nihai_kalite_durumu

        FROM gunluk_veri_kalitesi gvk

        INNER JOIN piyasa_takvimi pt
            ON pt.islem_tarihi =
                gvk.islem_tarihi

        WHERE gvk.menkul_kiymet_id = %s
          AND gvk.nihai_kalite_durumu IN (
              'TUTULDU',
              'DOLDURULACAK'
          )

        ORDER BY gvk.islem_tarihi;
        """,
        (menkul_kiymet_id,)
    )

    sutunlar = [
        "islem_tarihi",
        "piyasa_acilis_zamani",
        "piyasa_kapanis_zamani",
        "nihai_kalite_durumu",
    ]

    return pd.DataFrame(
        imlec.fetchall(),
        columns=sutunlar
    )


def ham_fiyatlari_getir(
    imlec,
    menkul_kiymet_id
):
    """Bir menkul kiymetin ham 5 dakikalik fiyatlarini getirir."""

    imlec.execute(
        """
        SELECT
            bar_zamani,
            acilis,
            en_yuksek,
            en_dusuk,
            kapanis,
            hacim,
            islem_sayisi,
            hacim_agirlikli_ortalama_fiyat

        FROM ham_fiyat_verileri

        WHERE menkul_kiymet_id = %s
          AND zaman_araligi_dakika = 5

        ORDER BY bar_zamani;
        """,
        (menkul_kiymet_id,)
    )

    sutunlar = [
        "bar_zamani",
        "acilis",
        "en_yuksek",
        "en_dusuk",
        "kapanis",
        "hacim",
        "islem_sayisi",
        "hacim_agirlikli_ortalama_fiyat",
    ]

    veri = pd.DataFrame(
        imlec.fetchall(),
        columns=sutunlar
    )

    if not veri.empty:
        veri["bar_zamani"] = pd.to_datetime(
            veri["bar_zamani"],
            utc=True
        )

    return veri


def bir_gunu_hazirla(
    gun_bilgisi,
    ham_fiyatlar,
    menkul_kiymet_id
):
    """Bir sembol-gunu duzenli 5 dakikalik zaman cizelgesine getirir."""

    piyasa_acilisi = pd.Timestamp(
        gun_bilgisi.piyasa_acilis_zamani
    )

    piyasa_kapanisi = pd.Timestamp(
        gun_bilgisi.piyasa_kapanis_zamani
    )

    beklenen_zamanlar = pd.date_range(
        start=piyasa_acilisi,
        end=piyasa_kapanisi
            - pd.Timedelta(minutes=5),
        freq="5min"
    )

    gun_verisi = ham_fiyatlar[
        (ham_fiyatlar["bar_zamani"] >= piyasa_acilisi)
        & (
            ham_fiyatlar["bar_zamani"]
            < piyasa_kapanisi
        )
    ].copy()

    gun_verisi = gun_verisi.set_index(
        "bar_zamani"
    )

    gun_verisi = gun_verisi.reindex(
        beklenen_zamanlar
    )

    # Kapanis fiyati bos olan satirlar eksik barlardir.
    eksik_bar_mi = gun_verisi["kapanis"].isna()

    # Eksik barlarda bir onceki gercek veya doldurulmus
    # kapanis fiyatini kullanir.
    onceki_kapanis = (
        gun_verisi["kapanis"]
        .ffill()
    )

    fiyat_sutunlari = [
        "acilis",
        "en_yuksek",
        "en_dusuk",
        "kapanis",
        "hacim_agirlikli_ortalama_fiyat",
    ]

    for sutun in fiyat_sutunlari:
        gun_verisi.loc[
            eksik_bar_mi,
            sutun
        ] = onceki_kapanis[eksik_bar_mi]

    gun_verisi.loc[
        eksik_bar_mi,
        "hacim"
    ] = 0

    gun_verisi.loc[
        eksik_bar_mi,
        "islem_sayisi"
    ] = 0

    gun_verisi["dolduruldu_mu"] = (
        eksik_bar_mi
    )

    gun_verisi["menkul_kiymet_id"] = (
        menkul_kiymet_id
    )

    gun_verisi["zaman_araligi_dakika"] = 5

    gun_verisi = gun_verisi.reset_index(
        names="bar_zamani"
    )

    return gun_verisi


def verileri_kaydet(
    imlec,
    menkul_kiymet_id,
    analiz_verisi
):
    """Hazirlanan analiz verilerini PostgreSQL'e kaydeder."""

    # Ayni sembol daha once hazirlandiysa eski analiz
    # satirlarini silerek temiz bir aktarim yapar.
    imlec.execute(
        """
        DELETE FROM analiz_fiyat_verileri
        WHERE menkul_kiymet_id = %s;
        """,
        (menkul_kiymet_id,)
    )

    kayitlar = []

    for satir in analiz_verisi.itertuples(
        index=False
    ):
        kayitlar.append(
            (
                int(satir.menkul_kiymet_id),
                satir.bar_zamani.to_pydatetime(),
                int(satir.zaman_araligi_dakika),
                float(satir.acilis),
                float(satir.en_yuksek),
                float(satir.en_dusuk),
                float(satir.kapanis),
                int(satir.hacim),
                int(satir.islem_sayisi),
                float(
                    satir.hacim_agirlikli_ortalama_fiyat
                ),
                bool(satir.dolduruldu_mu),
            )
        )

    ekleme_sorgusu = """
        INSERT INTO analiz_fiyat_verileri (
            menkul_kiymet_id,
            bar_zamani,
            zaman_araligi_dakika,
            acilis,
            en_yuksek,
            en_dusuk,
            kapanis,
            hacim,
            islem_sayisi,
            hacim_agirlikli_ortalama_fiyat,
            dolduruldu_mu
        )
        VALUES %s;
    """

    execute_values(
        imlec,
        ekleme_sorgusu,
        kayitlar,
        page_size=5000
    )


def bir_sembolu_hazirla(sembol):
    """Bir sembolun analiz verisini bastan sona hazirlar."""

    baglanti = None
    imlec = None

    try:
        sembol = sembol.upper()

        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        menkul_kiymet_id = sembol_id_bul(
            imlec,
            sembol
        )

        kullanilacak_gunler = (
            kullanilacak_gunleri_getir(
                imlec,
                menkul_kiymet_id
            )
        )

        ham_fiyatlar = ham_fiyatlari_getir(
            imlec,
            menkul_kiymet_id
        )

        if kullanilacak_gunler.empty:
            print(
                f"{sembol}: Kullanilacak gun bulunamadi."
            )
            return

        hazirlanan_gunler = []

        for gun_bilgisi in (
            kullanilacak_gunler.itertuples(
                index=False
            )
        ):
            gun_verisi = bir_gunu_hazirla(
                gun_bilgisi,
                ham_fiyatlar,
                menkul_kiymet_id
            )

            hazirlanan_gunler.append(
                gun_verisi
            )

        analiz_verisi = pd.concat(
            hazirlanan_gunler,
            ignore_index=True
        )

        verileri_kaydet(
            imlec,
            menkul_kiymet_id,
            analiz_verisi
        )

        baglanti.commit()

        doldurulan_bar_sayisi = int(
            analiz_verisi[
                "dolduruldu_mu"
            ].sum()
        )

        print(
            f"{sembol}: "
            f"{len(analiz_verisi):,} satir kaydedildi."
        )

        print(
            f"{sembol}: "
            f"{doldurulan_bar_sayisi:,} "
            f"eksik bar dolduruldu."
        )

    except (
        psycopg2.Error,
        ValueError,
        TypeError
    ) as hata:
        if baglanti is not None:
            baglanti.rollback()

        print(f"{sembol}: Hata: {hata}")

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def komut_satiri_argumanlarini_al():
    """Terminalden hazirlanacak sembolleri alir."""

    parser = argparse.ArgumentParser(
        description=(
            "Temiz analiz fiyat verilerini hazirlar."
        )
    )

    parser.add_argument(
        "--semboller",
        nargs="+",
        required=True,
        help="Ornek: AAPL SPY"
    )

    return parser.parse_args()


if __name__ == "__main__":
    argumanlar = (
        komut_satiri_argumanlarini_al()
    )

    for sembol in argumanlar.semboller:
        bir_sembolu_hazirla(sembol)