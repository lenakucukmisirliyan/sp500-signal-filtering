import numpy as np
from psycopg2.extras import execute_values

from src.makine_ogrenmesi_modeli import (
    HEDEF_ENGELLEME_ORANI,
    OZELLIKLER,
    deney_donemlerini_olustur,
    model_olustur,
    veriyi_getir,
)
from src.veritabani import (
    veritabani_baglantisi_olustur
)


KURAL_ESIGI = -0.001


def donem_verisini_al(
    veri,
    donemler
):
    """Istenen deney donemlerinin satirlarini getirir."""

    return veri[
        veri["deney_donemi"].isin(
            donemler
        )
    ].copy()


def bir_donemin_sonuclarini_hazirla(
    veri,
    egitim_donemleri,
    degerlendirme_donemi
):
    """Bir walk-forward adiminin filtre kararlarini hazirlar."""

    egitim_verisi = donem_verisini_al(
        veri,
        egitim_donemleri
    )

    degerlendirme_verisi = (
        donem_verisini_al(
            veri,
            [degerlendirme_donemi]
        )
    )

    egitim_ozellikleri = (
        egitim_verisi[OZELLIKLER]
        .astype(float)
    )

    egitim_hedefi = (
        egitim_verisi["basarili_mi"]
        .astype(int)
    )

    degerlendirme_ozellikleri = (
        degerlendirme_verisi[
            OZELLIKLER
        ]
        .astype(float)
    )

    model = model_olustur()

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi
    )

    # Esik yalnizca gecmis egitim verisinden belirlenir.
    egitim_olasiliklari = (
        model.predict_proba(
            egitim_ozellikleri
        )[:, 1]
    )

    ml_esigi = np.quantile(
        egitim_olasiliklari,
        HEDEF_ENGELLEME_ORANI
    )

    ml_olasiliklari = (
        model.predict_proba(
            degerlendirme_ozellikleri
        )[:, 1]
    )

    ml_izin_verilenler = (
        ml_olasiliklari
        >= ml_esigi
    )

    spy_getirisi = (
        degerlendirme_verisi[
            "spy_60dk_getiri"
        ]
        .astype(float)
    )

    kural_izin_verilenler = (
        spy_getirisi.isna()
        | (
            spy_getirisi
            >= KURAL_ESIGI
        )
    ).to_numpy()

    kayitlar = []

    sinyal_idleri = (
        degerlendirme_verisi[
            "sinyal_id"
        ]
        .astype(int)
        .to_numpy()
    )

    for sira in range(
        len(degerlendirme_verisi)
    ):
        kayitlar.append(
            (
                int(sinyal_idleri[sira]),
                degerlendirme_donemi,
                bool(
                    kural_izin_verilenler[
                        sira
                    ]
                ),
                float(
                    ml_olasiliklari[
                        sira
                    ]
                ),
                float(ml_esigi),
                bool(
                    ml_izin_verilenler[
                        sira
                    ]
                ),
            )
        )

    print(
        f"{degerlendirme_donemi}: "
        f"{len(kayitlar):,} sonuc hazirlandi | "
        f"ML esigi: {ml_esigi:.4f}"
    )

    return kayitlar


def sonuclari_kaydet():
    """Uc walk-forward doneminin filtre kararlarini kaydeder."""

    veri = veriyi_getir()

    veri = deney_donemlerini_olustur(
        veri
    )

    tum_kayitlar = []

    tum_kayitlar.extend(
        bir_donemin_sonuclarini_hazirla(
            veri=veri,
            egitim_donemleri=[
                "EGITIM",
            ],
            degerlendirme_donemi=(
                "DOGRULAMA"
            )
        )
    )

    tum_kayitlar.extend(
        bir_donemin_sonuclarini_hazirla(
            veri=veri,
            egitim_donemleri=[
                "EGITIM",
                "DOGRULAMA",
            ],
            degerlendirme_donemi=(
                "IKINCIL_DOGRULAMA"
            )
        )
    )

    tum_kayitlar.extend(
        bir_donemin_sonuclarini_hazirla(
            veri=veri,
            egitim_donemleri=[
                "EGITIM",
                "DOGRULAMA",
                "IKINCIL_DOGRULAMA",
            ],
            degerlendirme_donemi=(
                "NIHAI_TEST"
            )
        )
    )

    baglanti = None
    imlec = None

    try:
        baglanti = (
            veritabani_baglantisi_olustur()
        )

        imlec = baglanti.cursor()

        imlec.execute(
            """
            TRUNCATE TABLE filtre_sonuclari;
            """
        )

        execute_values(
            imlec,
            """
            INSERT INTO filtre_sonuclari (
                sinyal_id,
                deney_donemi,
                kural_izin_verdi_mi,
                ml_basari_olasiligi,
                ml_esigi,
                ml_izin_verdi_mi
            )
            VALUES %s;
            """,
            tum_kayitlar,
            page_size=5000
        )

        baglanti.commit()

        print()
        print(
            f"Toplam kaydedilen sonuc: "
            f"{len(tum_kayitlar):,}"
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
    sonuclari_kaydet()