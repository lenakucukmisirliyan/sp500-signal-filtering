import argparse
import time
from datetime import datetime, timezone

from psycopg2.extras import execute_values

from src.alpaca_verisi import fiyat_verisi_indir
from src.fiyat_verisi_aktarimi import fiyat_verilerini_hazirla
from src.veritabani import veritabani_baglantisi_olustur


VARSAYILAN_BASLANGIC = datetime(
    2023,
    1,
    3,
    tzinfo=timezone.utc,
)

VARSAYILAN_BITIS = datetime(
    2024,
    4,
    1,
    tzinfo=timezone.utc,
)

GRUP_BUYUKLUGU = 20
ZAMAN_ARALIGI_DAKIKA = 5
VERI_KAYNAGI = "ALPACA_SIP"
AZAMI_DENEME = 3


def tarih_metnini_cevir(tarih_metni):
    """YYYY-AA-GG bicimindeki tarihi UTC zamanina cevirir."""

    return datetime.strptime(
        tarih_metni,
        "%Y-%m-%d",
    ).replace(tzinfo=timezone.utc)


def sonraki_ayin_ilk_gunu(tarih):
    """Verilen tarihten sonraki ayin ilk gununu hesaplar."""

    if tarih.month == 12:
        return datetime(
            tarih.year + 1,
            1,
            1,
            tzinfo=timezone.utc,
        )

    return datetime(
        tarih.year,
        tarih.month + 1,
        1,
        tzinfo=timezone.utc,
    )


def aylik_tarih_araliklarini_olustur(baslangic, bitis):
    """Verilen tarih araligini aylik parcalara ayirir."""

    tarih_araliklari = []
    parca_baslangici = baslangic

    while parca_baslangici < bitis:
        parca_bitisi = min(
            sonraki_ayin_ilk_gunu(parca_baslangici),
            bitis,
        )

        tarih_araliklari.append(
            (
                parca_baslangici,
                parca_bitisi,
            )
        )

        parca_baslangici = parca_bitisi

    return tarih_araliklari


def menkul_kiymetleri_getir():
    """Veritabanindaki menkul kiymet kimliklerini getirir."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        imlec.execute(
            """
            SELECT
                menkul_kiymet_id,
                sembol
            FROM menkul_kiymetler
            ORDER BY sembol;
            """
        )

        return imlec.fetchall()

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def secili_menkul_kiymetleri_bul(
    menkul_kiymetler,
    secili_semboller,
):
    """Komut satirinda sembol verildiyse listeyi filtreler."""

    if not secili_semboller:
        return menkul_kiymetler

    secili_semboller = {
        sembol.upper()
        for sembol in secili_semboller
    }

    bulunan_semboller = {
        sembol
        for _, sembol in menkul_kiymetler
        if sembol in secili_semboller
    }

    bulunamayan_semboller = (
        secili_semboller - bulunan_semboller
    )

    if bulunamayan_semboller:
        raise ValueError(
            "Menkul kiymetler tablosunda bulunamayan semboller: "
            + ", ".join(sorted(bulunamayan_semboller))
        )

    return [
        kayit
        for kayit in menkul_kiymetler
        if kayit[1] in secili_semboller
    ]


def gruplara_ayir(liste, grup_buyuklugu):
    """Listeyi belirtilen buyuklukte gruplara ayirir."""

    for baslangic in range(
        0,
        len(liste),
        grup_buyuklugu,
    ):
        yield liste[
            baslangic:baslangic + grup_buyuklugu
        ]


def tamamlanan_menkul_kiymetleri_getir(
    parca_baslangici,
    parca_bitisi,
):
    """Daha once tamamlanan aktarimlari getirir."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        imlec.execute(
            """
            SELECT DISTINCT menkul_kiymet_id
            FROM veri_aktarimlari
            WHERE veri_baslangic_zamani = %s
              AND veri_bitis_zamani = %s
              AND zaman_araligi_dakika = %s
              AND veri_kaynagi = %s
              AND aktarim_durumu = 'TAMAMLANDI';
            """,
            (
                parca_baslangici,
                parca_bitisi,
                ZAMAN_ARALIGI_DAKIKA,
                VERI_KAYNAGI,
            ),
        )

        return {
            satir[0]
            for satir in imlec.fetchall()
        }

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def aktarim_kayitlarini_baslat(
    menkul_kiymetler,
    parca_baslangici,
    parca_bitisi,
):
    """Aktarimlar icin BASLADI durum kayitlarini olusturur."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        aktarim_idleri = {}

        for menkul_kiymet_id, sembol in menkul_kiymetler:
            # Onceki calisma tamamlanmadan kesildiyse kapatilir.
            imlec.execute(
                """
                UPDATE veri_aktarimlari
                SET
                    aktarim_durumu = 'BASARISIZ',
                    hata_mesaji = %s,
                    aktarim_tamamlanma_zamani =
                        CURRENT_TIMESTAMP
                WHERE menkul_kiymet_id = %s
                  AND veri_baslangic_zamani = %s
                  AND veri_bitis_zamani = %s
                  AND zaman_araligi_dakika = %s
                  AND veri_kaynagi = %s
                  AND aktarim_durumu = 'BASLADI';
                """,
                (
                    "Onceki calisma tamamlanmadan kesildi.",
                    menkul_kiymet_id,
                    parca_baslangici,
                    parca_bitisi,
                    ZAMAN_ARALIGI_DAKIKA,
                    VERI_KAYNAGI,
                ),
            )

            imlec.execute(
                """
                INSERT INTO veri_aktarimlari (
                    menkul_kiymet_id,
                    veri_baslangic_zamani,
                    veri_bitis_zamani,
                    zaman_araligi_dakika,
                    veri_kaynagi,
                    aktarim_durumu
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'BASLADI'
                )
                RETURNING aktarim_id;
                """,
                (
                    menkul_kiymet_id,
                    parca_baslangici,
                    parca_bitisi,
                    ZAMAN_ARALIGI_DAKIKA,
                    VERI_KAYNAGI,
                ),
            )

            aktarim_idleri[sembol] = imlec.fetchone()[0]

        baglanti.commit()

        return aktarim_idleri

    except Exception:
        if baglanti is not None:
            baglanti.rollback()

        raise

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def veriyi_tekrar_deneyerek_indir(
    semboller,
    parca_baslangici,
    parca_bitisi,
):
    """Alpaca indirmesini gecici hatalarda yeniden dener."""

    son_hata = None

    for deneme in range(1, AZAMI_DENEME + 1):
        try:
            return fiyat_verisi_indir(
                semboller=semboller,
                baslangic=parca_baslangici,
                bitis=parca_bitisi,
                zaman_araligi_dakika=(
                    ZAMAN_ARALIGI_DAKIKA
                ),
            )

        except Exception as hata:
            son_hata = hata

            print(
                "Indirme denemesi basarisiz: "
                f"{deneme}/{AZAMI_DENEME} | {hata}"
            )

            if deneme < AZAMI_DENEME:
                bekleme_suresi = deneme * 5

                print(
                    f"{bekleme_suresi} saniye sonra "
                    "yeniden denenecek."
                )

                time.sleep(bekleme_suresi)

    raise son_hata


def fiyatlari_kaydet_ve_aktarimlari_tamamla(
    veri,
    menkul_kiymetler,
    aktarim_idleri,
    parca_baslangici,
    parca_bitisi,
):
    """Fiyatlari kaydeder ve aktarimlari tamamlar."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        sembol_idleri = {
            sembol: menkul_kiymet_id
            for menkul_kiymet_id, sembol
            in menkul_kiymetler
        }

        tum_kayitlar = []

        if not veri.empty:
            for sembol, menkul_kiymet_id in (
                sembol_idleri.items()
            ):
                sembol_verisi = veri[
                    veri["symbol"] == sembol
                ]

                if sembol_verisi.empty:
                    continue

                kayitlar = fiyat_verilerini_hazirla(
                    sembol_verisi,
                    menkul_kiymet_id,
                )

                tum_kayitlar.extend(kayitlar)

        if tum_kayitlar:
            execute_values(
                imlec,
                """
                INSERT INTO ham_fiyat_verileri (
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
                    veri_kaynagi,
                    fiyat_duzeltmesi
                )
                VALUES %s
                ON CONFLICT (
                    menkul_kiymet_id,
                    bar_zamani,
                    zaman_araligi_dakika
                )
                DO NOTHING;
                """,
                tum_kayitlar,
                page_size=5000,
            )

        menkul_kiymet_idleri = list(
            sembol_idleri.values()
        )

        imlec.execute(
            """
            SELECT
                menkul_kiymet_id,
                COUNT(*)
            FROM ham_fiyat_verileri
            WHERE menkul_kiymet_id = ANY(%s)
              AND bar_zamani >= %s
              AND bar_zamani < %s
              AND zaman_araligi_dakika = %s
            GROUP BY menkul_kiymet_id;
            """,
            (
                menkul_kiymet_idleri,
                parca_baslangici,
                parca_bitisi,
                ZAMAN_ARALIGI_DAKIKA,
            ),
        )

        saklanan_satir_sayilari = {
            menkul_kiymet_id: satir_sayisi
            for menkul_kiymet_id, satir_sayisi
            in imlec.fetchall()
        }

        sonuc = {}

        for sembol, aktarim_id in aktarim_idleri.items():
            menkul_kiymet_id = sembol_idleri[sembol]

            satir_sayisi = saklanan_satir_sayilari.get(
                menkul_kiymet_id,
                0,
            )

            imlec.execute(
                """
                UPDATE veri_aktarimlari
                SET
                    aktarim_durumu = 'TAMAMLANDI',
                    aktarilan_satir_sayisi = %s,
                    hata_mesaji = NULL,
                    aktarim_tamamlanma_zamani =
                        CURRENT_TIMESTAMP
                WHERE aktarim_id = %s;
                """,
                (
                    satir_sayisi,
                    aktarim_id,
                ),
            )

            sonuc[sembol] = satir_sayisi

        baglanti.commit()

        return sonuc

    except Exception:
        if baglanti is not None:
            baglanti.rollback()

        raise

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def aktarimlari_basarisiz_yap(
    aktarim_idleri,
    hata,
):
    """Hata alan aktarimlari BASARISIZ olarak isaretler."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        for aktarim_id in aktarim_idleri.values():
            imlec.execute(
                """
                UPDATE veri_aktarimlari
                SET
                    aktarim_durumu = 'BASARISIZ',
                    hata_mesaji = %s,
                    aktarim_tamamlanma_zamani =
                        CURRENT_TIMESTAMP
                WHERE aktarim_id = %s;
                """,
                (
                    str(hata)[:2000],
                    aktarim_id,
                ),
            )

        baglanti.commit()

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def toplu_aktarimi_baslat(
    baslangic,
    bitis,
    secili_semboller=None,
):
    """Secilen menkul kiymetlerin verilerini aktarir."""

    if bitis <= baslangic:
        raise ValueError(
            "Bitis tarihi baslangic tarihinden "
            "sonra olmalidir."
        )

    menkul_kiymetler = menkul_kiymetleri_getir()

    menkul_kiymetler = secili_menkul_kiymetleri_bul(
        menkul_kiymetler,
        secili_semboller,
    )

    tarih_araliklari = (
        aylik_tarih_araliklarini_olustur(
            baslangic,
            bitis,
        )
    )

    aylik_grup_sayisi = (
        len(menkul_kiymetler)
        + GRUP_BUYUKLUGU
        - 1
    ) // GRUP_BUYUKLUGU

    azami_grup_sayisi = (
        aylik_grup_sayisi
        * len(tarih_araliklari)
    )

    islenen_grup_sayisi = 0
    toplam_saklanan_satir = 0

    print(
        f"Toplam menkul kiymet: "
        f"{len(menkul_kiymetler)}"
    )
    print(
        f"Aylik donem sayisi: "
        f"{len(tarih_araliklari)}"
    )
    print(
        f"Azami grup sayisi: "
        f"{azami_grup_sayisi}"
    )
    print(
        f"Genel donem: {baslangic.date()} - "
        f"{bitis.date()} (bitis haric)"
    )

    for parca_baslangici, parca_bitisi in (
        tarih_araliklari
    ):
        tamamlanan_idler = (
            tamamlanan_menkul_kiymetleri_getir(
                parca_baslangici,
                parca_bitisi,
            )
        )

        bekleyen_menkul_kiymetler = [
            kayit
            for kayit in menkul_kiymetler
            if kayit[0] not in tamamlanan_idler
        ]

        atlanan_sayi = (
            len(menkul_kiymetler)
            - len(bekleyen_menkul_kiymetler)
        )

        print(
            "\nDonem: "
            f"{parca_baslangici.date()} - "
            f"{parca_bitisi.date()} | "
            f"Tamamlanmis sembol: {atlanan_sayi} | "
            "Bekleyen sembol: "
            f"{len(bekleyen_menkul_kiymetler)}"
        )

        for grup in gruplara_ayir(
            bekleyen_menkul_kiymetler,
            GRUP_BUYUKLUGU,
        ):
            islenen_grup_sayisi += 1

            semboller = [
                sembol
                for _, sembol in grup
            ]

            print(
                f"\n[{islenen_grup_sayisi}/"
                f"{azami_grup_sayisi}] "
                f"{parca_baslangici.date()} - "
                f"{parca_bitisi.date()} | "
                f"{len(semboller)} sembol"
            )

            print(", ".join(semboller))

            aktarim_idleri = {}

            try:
                aktarim_idleri = (
                    aktarim_kayitlarini_baslat(
                        grup,
                        parca_baslangici,
                        parca_bitisi,
                    )
                )

                veri = veriyi_tekrar_deneyerek_indir(
                    semboller,
                    parca_baslangici,
                    parca_bitisi,
                )

                satir_sayilari = (
                    fiyatlari_kaydet_ve_aktarimlari_tamamla(
                        veri,
                        grup,
                        aktarim_idleri,
                        parca_baslangici,
                        parca_bitisi,
                    )
                )

                grup_satir_sayisi = sum(
                    satir_sayilari.values()
                )

                toplam_saklanan_satir += (
                    grup_satir_sayisi
                )

                print(
                    "Grup tamamlandi. "
                    "Saklanan satir: "
                    f"{grup_satir_sayisi:,}"
                )

            except Exception as hata:
                print(
                    f"Grup aktarim hatasi: {hata}"
                )

                if aktarim_idleri:
                    aktarimlari_basarisiz_yap(
                        aktarim_idleri,
                        hata,
                    )

            time.sleep(0.25)

    print("\nToplu aktarim calismasi tamamlandi.")
    print(
        "Bu calistirmada kontrol edilen toplam satir: "
        f"{toplam_saklanan_satir:,}"
    )


def komut_satiri_argumanlarini_al():
    """Terminalden aktarim ayarlarini alir."""

    parser = argparse.ArgumentParser(
        description=(
            "Alpaca fiyat verilerini aylik parcalar "
            "halinde PostgreSQL'e aktarir."
        )
    )

    parser.add_argument(
        "--baslangic",
        default=VARSAYILAN_BASLANGIC.strftime(
            "%Y-%m-%d"
        ),
        help="Baslangic tarihi. Bicim: YYYY-AA-GG",
    )

    parser.add_argument(
        "--bitis",
        default=VARSAYILAN_BITIS.strftime(
            "%Y-%m-%d"
        ),
        help=(
            "Haric tutulan bitis tarihi. "
            "Bicim: YYYY-AA-GG"
        ),
    )

    parser.add_argument(
        "--semboller",
        nargs="+",
        help=(
            "Yalnizca aktarilacak semboller. "
            "Ornek: --semboller AAPL SPY"
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    argumanlar = komut_satiri_argumanlarini_al()

    toplu_aktarimi_baslat(
        baslangic=tarih_metnini_cevir(
            argumanlar.baslangic
        ),
        bitis=tarih_metnini_cevir(
            argumanlar.bitis
        ),
        secili_semboller=argumanlar.semboller,
    )