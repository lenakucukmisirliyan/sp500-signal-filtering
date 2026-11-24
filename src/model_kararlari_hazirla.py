import numpy as np
from psycopg2.extras import execute_values

from src.makine_ogrenmesi_modeli import (
    HEDEF_ENGELLEME_ORANI,
    OZELLIKLER,
    deney_donemlerini_olustur,
    donem_verisini_getir,
    model_olustur,
    veriyi_getir,
)
from src.veritabani import (
    veritabani_baglantisi_olustur,
)


MODEL_KODLARI = [
    "LOGISTIC_REGRESSION",
    "DECISION_TREE",
    "RANDOM_FOREST",
    "KNN",
    "NAIVE_BAYES",
    "YAPAY_SINIR_AGI",
]


def deneyleri_hazirla(
    veri,
):
    """Zaman sirali egitim ve degerlendirme donemlerini hazirlar."""

    return [
        {
            "donem": "DOGRULAMA",

            "egitim": donem_verisini_getir(
                veri,
                ["EGITIM"],
            ),

            "degerlendirme": donem_verisini_getir(
                veri,
                ["DOGRULAMA"],
            ),
        },

        {
            "donem": "IKINCIL_DOGRULAMA",

            "egitim": donem_verisini_getir(
                veri,
                [
                    "EGITIM",
                    "DOGRULAMA",
                ],
            ),

            "degerlendirme": donem_verisini_getir(
                veri,
                ["IKINCIL_DOGRULAMA"],
            ),
        },

        {
            "donem": "NIHAI_TEST",

            "egitim": donem_verisini_getir(
                veri,
                [
                    "EGITIM",
                    "DOGRULAMA",
                    "IKINCIL_DOGRULAMA",
                ],
            ),

            "degerlendirme": donem_verisini_getir(
                veri,
                ["NIHAI_TEST"],
            ),
        },
    ]


def esikleri_hesapla(
    egitim_olasiliklari,
):
    """ALMA ve AL esiklerini yalnizca egitim verisinden bulur."""

    alma_esigi = np.quantile(
        egitim_olasiliklari,
        HEDEF_ENGELLEME_ORANI,
    )

    al_esigi = np.quantile(
        egitim_olasiliklari,
        1 - HEDEF_ENGELLEME_ORANI,
    )

    return alma_esigi, al_esigi


def karar_ver(
    basari_olasiligi,
    alma_esigi,
    al_esigi,
):
    """Basari olasiligini AL, NOTR veya ALMA kararina cevirir."""

    if basari_olasiligi < alma_esigi:
        return "ALMA"

    if basari_olasiligi >= al_esigi:
        return "AL"

    return "NOTR"


def bir_modelin_kararlarini_hazirla(
    model_kodu,
    deney_donemi,
    egitim_verisi,
    degerlendirme_verisi,
):
    """Bir modeli egitir ve bir donem icin kararlarini hazirlar."""

    model = model_olustur(
        model_kodu
    )

    egitim_ozellikleri = egitim_verisi[
        OZELLIKLER
    ]

    egitim_hedefi = (
        egitim_verisi["basarili_mi"]
        .astype(int)
    )

    degerlendirme_ozellikleri = (
        degerlendirme_verisi[
            OZELLIKLER
        ]
    )

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi,
    )

    # Karar esikleri degerlendirme verisinden degil,
    # yalnizca gecmis egitim verisinden hesaplanir.
    egitim_olasiliklari = (
        model.predict_proba(
            egitim_ozellikleri
        )[:, 1]
    )

    (
        alma_esigi,
        al_esigi,
    ) = esikleri_hesapla(
        egitim_olasiliklari
    )

    degerlendirme_olasiliklari = (
        model.predict_proba(
            degerlendirme_ozellikleri
        )[:, 1]
    )

    kayitlar = []

    karar_sayilari = {
        "AL": 0,
        "NOTR": 0,
        "ALMA": 0,
    }

    sinyal_idleri = (
        degerlendirme_verisi[
            "sinyal_id"
        ].astype(int)
    )

    for (
        sinyal_id,
        basari_olasiligi,
    ) in zip(
        sinyal_idleri,
        degerlendirme_olasiliklari,
    ):
        model_karari = karar_ver(
            basari_olasiligi=(
                basari_olasiligi
            ),
            alma_esigi=alma_esigi,
            al_esigi=al_esigi,
        )

        karar_sayilari[
            model_karari
        ] += 1

        kayitlar.append(
            (
                int(sinyal_id),
                deney_donemi,
                model_kodu,
                float(basari_olasiligi),
                float(alma_esigi),
                float(al_esigi),
                model_karari,
            )
        )

    return (
        kayitlar,
        karar_sayilari,
        alma_esigi,
        al_esigi,
    )


def kararlari_kaydet(
    imlec,
    kayitlar,
):
    """Model kararlarini PostgreSQL'e kaydeder."""

    execute_values(
        imlec,
        """
        INSERT INTO model_sinyal_kararlari (
            sinyal_id,
            deney_donemi,
            model_kodu,
            basari_olasiligi,
            alma_esigi,
            al_esigi,
            model_karari
        )
        VALUES %s;
        """,
        kayitlar,
        page_size=5000,
    )


def model_kararlarini_hazirla():
    """Butun modellerin zaman sirali kararlarini hazirlar."""

    veri = veriyi_getir()

    veri = deney_donemlerini_olustur(
        veri
    )

    deneyler = deneyleri_hazirla(
        veri
    )

    baglanti = None
    imlec = None
    toplam_kayit = 0

    try:
        baglanti = (
            veritabani_baglantisi_olustur()
        )

        imlec = baglanti.cursor()

        # Dosya yeniden calistirilirsa eski kararlar
        # silinerek sonuclar bastan olusturulur.
        imlec.execute(
            """
            TRUNCATE TABLE
                model_sinyal_kararlari
            RESTART IDENTITY;
            """
        )

        for deney in deneyler:
            deney_donemi = deney[
                "donem"
            ]

            egitim_verisi = deney[
                "egitim"
            ]

            degerlendirme_verisi = deney[
                "degerlendirme"
            ]

            print(
                "\n"
                + "=" * 60
            )

            print(
                f"Donem: {deney_donemi}"
            )

            print(
                f"Egitim sinyali: "
                f"{len(egitim_verisi):,}"
            )

            print(
                f"Degerlendirme sinyali: "
                f"{len(degerlendirme_verisi):,}"
            )

            for model_kodu in MODEL_KODLARI:
                (
                    kayitlar,
                    karar_sayilari,
                    alma_esigi,
                    al_esigi,
                ) = (
                    bir_modelin_kararlarini_hazirla(
                        model_kodu=model_kodu,
                        deney_donemi=(
                            deney_donemi
                        ),
                        egitim_verisi=(
                            egitim_verisi
                        ),
                        degerlendirme_verisi=(
                            degerlendirme_verisi
                        ),
                    )
                )

                kararlari_kaydet(
                    imlec,
                    kayitlar,
                )

                toplam_kayit += len(
                    kayitlar
                )

                print(
                    f"{model_kodu}: "
                    f"AL={karar_sayilari['AL']:,} | "
                    f"NOTR={karar_sayilari['NOTR']:,} | "
                    f"ALMA={karar_sayilari['ALMA']:,} | "
                    f"Alt esik={alma_esigi:.4f} | "
                    f"Ust esik={al_esigi:.4f}"
                )

        baglanti.commit()

        print(
            "\nModel kararlari kaydedildi."
        )

        print(
            f"Toplam kayit: "
            f"{toplam_kayit:,}"
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
    model_kararlarini_hazirla()