import pandas as pd

from psycopg2.extras import execute_values
from sklearn.metrics import roc_auc_score

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


def model_kararlarini_getir():
    """Model kararlarini ve gercek sonuclari veritabanindan getirir."""

    baglanti = (
        veritabani_baglantisi_olustur()
    )

    imlec = baglanti.cursor()

    try:
        imlec.execute(
            """
            SELECT
                msk.sinyal_id,
                msk.deney_donemi,
                msk.model_kodu,
                msk.basari_olasiligi,
                msk.model_karari,
                ins.basarili_mi

            FROM
                model_sinyal_kararlari msk,
                islem_sinyalleri ins

            WHERE msk.sinyal_id =
                  ins.sinyal_id

            ORDER BY
                msk.deney_donemi,
                msk.sinyal_id,
                msk.model_kodu;
            """
        )

        sutunlar = [
            "sinyal_id",
            "deney_donemi",
            "model_kodu",
            "basari_olasiligi",
            "model_karari",
            "basarili_mi",
        ]

        veri = pd.DataFrame(
            imlec.fetchall(),
            columns=sutunlar,
        )

    finally:
        imlec.close()
        baglanti.close()

    veri["basari_olasiligi"] = (
        pd.to_numeric(
            veri["basari_olasiligi"],
            errors="coerce",
        )
    )

    veri["basarili_mi"] = (
        veri["basarili_mi"]
        .astype(int)
    )

    return veri


def model_auc_ortalamasini_hesapla(
    veri,
    model_kodu,
    kaynak_donemler,
):
    """Modelin gecmis dogrulama ROC-AUC ortalamasini hesaplar."""

    auc_degerleri = []

    for donem in kaynak_donemler:
        model_verisi = veri[
            (veri["model_kodu"] == model_kodu)
            & (veri["deney_donemi"] == donem)
        ]

        auc = roc_auc_score(
            model_verisi["basarili_mi"],
            model_verisi[
                "basari_olasiligi"
            ],
        )

        auc_degerleri.append(
            auc
        )

    return sum(auc_degerleri) / len(
        auc_degerleri
    )


def esit_agirliklari_hazirla():
    """Gecmis dogrulama sonucu yoksa modellere esit agirlik verir."""

    model_sayisi = len(
        MODEL_KODLARI
    )

    esit_agirlik = (
        1 / model_sayisi
    )

    agirliklar = {
        model_kodu: esit_agirlik
        for model_kodu in MODEL_KODLARI
    }

    auc_degerleri = {
        model_kodu: 0.50
        for model_kodu in MODEL_KODLARI
    }

    puanlar = {
        model_kodu: 0.0
        for model_kodu in MODEL_KODLARI
    }

    return (
        agirliklar,
        auc_degerleri,
        puanlar,
    )


def performans_agirliklarini_hazirla(
    veri,
    kaynak_donemler,
):
    """Gecmis ROC-AUC degerlerinden model agirliklarini hesaplar."""

    auc_degerleri = {}

    for model_kodu in MODEL_KODLARI:
        auc_degerleri[model_kodu] = (
            model_auc_ortalamasini_hesapla(
                veri=veri,
                model_kodu=model_kodu,
                kaynak_donemler=(
                    kaynak_donemler
                ),
            )
        )

    # ROC-AUC 0.50 rastgele tahmin duzeyidir.
    # Yalnizca rastgele duzeyin uzerindeki kisim
    # modelin agirlik puani olarak kullanilir.
    puanlar = {
        model_kodu: max(
            auc - 0.50,
            0.0,
        )
        for model_kodu, auc
        in auc_degerleri.items()
    }

    toplam_puan = sum(
        puanlar.values()
    )

    if toplam_puan == 0:
        return esit_agirliklari_hazirla()

    agirliklar = {
        model_kodu: puan / toplam_puan
        for model_kodu, puan
        in puanlar.items()
    }

    return (
        agirliklar,
        auc_degerleri,
        puanlar,
    )


def donem_agirliklarini_hazirla(
    veri,
):
    """Her uygulama donemi icin yalnizca gecmis veriden agirlik hesaplar."""

    donem_ayarlari = [
        {
            "uygulama_donemi":
                "DOGRULAMA",

            "kaynak_donemler":
                None,

            "agirlik_kaynagi":
                "ESIT_AGIRLIK",
        },

        {
            "uygulama_donemi":
                "IKINCIL_DOGRULAMA",

            "kaynak_donemler": [
                "DOGRULAMA",
            ],

            "agirlik_kaynagi":
                "BIRINCI_DOGRULAMA",
        },

        {
            "uygulama_donemi":
                "NIHAI_TEST",

            "kaynak_donemler": [
                "DOGRULAMA",
                "IKINCIL_DOGRULAMA",
            ],

            "agirlik_kaynagi":
                "IKI_DOGRULAMA_ORTALAMASI",
        },
    ]

    donem_agirliklari = {}
    agirlik_kayitlari = []

    for ayar in donem_ayarlari:
        uygulama_donemi = ayar[
            "uygulama_donemi"
        ]

        kaynak_donemler = ayar[
            "kaynak_donemler"
        ]

        if kaynak_donemler is None:
            (
                agirliklar,
                auc_degerleri,
                puanlar,
            ) = esit_agirliklari_hazirla()

        else:
            (
                agirliklar,
                auc_degerleri,
                puanlar,
            ) = (
                performans_agirliklarini_hazirla(
                    veri=veri,
                    kaynak_donemler=(
                        kaynak_donemler
                    ),
                )
            )

        donem_agirliklari[
            uygulama_donemi
        ] = agirliklar

        for model_kodu in MODEL_KODLARI:
            agirlik_kayitlari.append(
                (
                    uygulama_donemi,
                    model_kodu,
                    float(
                        auc_degerleri[
                            model_kodu
                        ]
                    ),
                    float(
                        puanlar[
                            model_kodu
                        ]
                    ),
                    float(
                        agirliklar[
                            model_kodu
                        ]
                    ),
                    ayar[
                        "agirlik_kaynagi"
                    ],
                )
            )

    return (
        donem_agirliklari,
        agirlik_kayitlari,
    )


def ensemble_karari_ver(
    al_oyu,
    alma_oyu,
):
    """Agirlikli cogunluga gore ensemble kararini verir."""

    if al_oyu > 0.50:
        return "AL"

    if alma_oyu > 0.50:
        return "ALMA"

    return "NOTR"


def ensemble_kayitlarini_hazirla(
    veri,
    donem_agirliklari,
):
    """Her sinyal icin agirlikli model oylarini birlestirir."""

    ensemble_kayitlari = []

    gruplar = veri.groupby(
        [
            "deney_donemi",
            "sinyal_id",
        ]
    )

    for (
        deney_donemi,
        sinyal_id,
    ), sinyal_grubu in gruplar:

        agirliklar = donem_agirliklari[
            deney_donemi
        ]

        al_oyu = 0.0
        notr_oyu = 0.0
        alma_oyu = 0.0

        for satir in (
            sinyal_grubu.itertuples(
                index=False
            )
        ):
            model_agirligi = agirliklar[
                satir.model_kodu
            ]

            if satir.model_karari == "AL":
                al_oyu += model_agirligi

            elif satir.model_karari == "ALMA":
                alma_oyu += model_agirligi

            else:
                notr_oyu += model_agirligi

        ensemble_karari = (
            ensemble_karari_ver(
                al_oyu=al_oyu,
                alma_oyu=alma_oyu,
            )
        )

        ensemble_kayitlari.append(
            (
                int(sinyal_id),
                deney_donemi,
                float(al_oyu),
                float(notr_oyu),
                float(alma_oyu),
                ensemble_karari,
            )
        )

    return ensemble_kayitlari


def sonuclari_kaydet(
    agirlik_kayitlari,
    ensemble_kayitlari,
):
    """Agirliklari ve ensemble kararlarini PostgreSQL'e kaydeder."""

    baglanti = None
    imlec = None

    try:
        baglanti = (
            veritabani_baglantisi_olustur()
        )

        imlec = baglanti.cursor()

        imlec.execute(
            """
            TRUNCATE TABLE
                model_agirliklari,
                ensemble_kararlari
            RESTART IDENTITY;
            """
        )

        execute_values(
            imlec,
            """
            INSERT INTO model_agirliklari (
                uygulama_donemi,
                model_kodu,
                roc_auc,
                rastgele_ustu_puan,
                model_agirligi,
                agirlik_kaynagi
            )
            VALUES %s;
            """,
            agirlik_kayitlari,
            page_size=100,
        )

        execute_values(
            imlec,
            """
            INSERT INTO ensemble_kararlari (
                sinyal_id,
                deney_donemi,
                al_oy_agirligi,
                notr_oy_agirligi,
                alma_oy_agirligi,
                ensemble_karari
            )
            VALUES %s;
            """,
            ensemble_kayitlari,
            page_size=5000,
        )

        baglanti.commit()

    except Exception:
        if baglanti is not None:
            baglanti.rollback()

        raise

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def sonuclari_yazdir(
    agirlik_kayitlari,
    ensemble_kayitlari,
):
    """Hesaplanan agirliklari ve karar dagilimini gosterir."""

    agirlik_sutunlari = [
        "donem",
        "model",
        "roc_auc",
        "puan",
        "agirlik",
        "kaynak",
    ]

    agirlik_tablosu = pd.DataFrame(
        agirlik_kayitlari,
        columns=agirlik_sutunlari,
    )

    karar_sutunlari = [
        "sinyal_id",
        "donem",
        "al_oyu",
        "notr_oyu",
        "alma_oyu",
        "karar",
    ]

    karar_tablosu = pd.DataFrame(
        ensemble_kayitlari,
        columns=karar_sutunlari,
    )

    print(
        "\nMODEL AGIRLIKLARI"
    )

    print(
        agirlik_tablosu.to_string(
            index=False,
            float_format=lambda deger: (
                f"{deger:.4f}"
            ),
        )
    )

    print(
        "\nENSEMBLE KARAR DAGILIMI"
    )

    karar_dagilimi = (
        karar_tablosu.groupby(
            [
                "donem",
                "karar",
            ]
        )
        .size()
        .reset_index(
            name="sinyal_sayisi"
        )
    )

    print(
        karar_dagilimi.to_string(
            index=False
        )
    )


def ensemble_kararlarini_hazirla():
    """Model agirliklarini ve ensemble kararlarini olusturur."""

    veri = model_kararlarini_getir()

    (
        donem_agirliklari,
        agirlik_kayitlari,
    ) = donem_agirliklarini_hazirla(
        veri
    )

    ensemble_kayitlari = (
        ensemble_kayitlarini_hazirla(
            veri=veri,
            donem_agirliklari=(
                donem_agirliklari
            ),
        )
    )

    sonuclari_kaydet(
        agirlik_kayitlari=(
            agirlik_kayitlari
        ),
        ensemble_kayitlari=(
            ensemble_kayitlari
        ),
    )

    sonuclari_yazdir(
        agirlik_kayitlari=(
            agirlik_kayitlari
        ),
        ensemble_kayitlari=(
            ensemble_kayitlari
        ),
    )

    print(
        f"\nToplam ensemble karari: "
        f"{len(ensemble_kayitlari):,}"
    )


if __name__ == "__main__":
    ensemble_kararlarini_hazirla()