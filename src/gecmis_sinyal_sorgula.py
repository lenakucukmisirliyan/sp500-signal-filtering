import argparse
from datetime import datetime

from src.veritabani import veritabani_baglantisi_olustur


MODEL_SUTUNLARI = [
    (
        "Logistic Regression",
        "logistic_regression_karari",
        "logistic_regression_olasiligi",
    ),
    (
        "Decision Tree",
        "decision_tree_karari",
        "decision_tree_olasiligi",
    ),
    (
        "Random Forest",
        "random_forest_karari",
        "random_forest_olasiligi",
    ),
    (
        "K-Nearest Neighbors",
        "knn_karari",
        "knn_olasiligi",
    ),
    (
        "Gaussian Naive Bayes",
        "naive_bayes_karari",
        "naive_bayes_olasiligi",
    ),
    (
        "Yapay Sinir Agi",
        "yapay_sinir_agi_karari",
        "yapay_sinir_agi_olasiligi",
    ),
]


def sinyalleri_getir(sembol, tarih):
    """Seçilen sembol ve tarihteki sinyalleri getirir."""

    baglanti = veritabani_baglantisi_olustur()
    imlec = baglanti.cursor()

    try:
        imlec.execute(
            """
            SELECT
                *
            FROM gecmis_sinyal_incelemesi
            WHERE sembol = %s
              AND sinyal_zamani_new_york::DATE = %s
            ORDER BY sinyal_zamani_new_york;
            """,
            (
                sembol.upper(),
                tarih,
            ),
        )

        sutunlar = [
            aciklama[0]
            for aciklama in imlec.description
        ]

        return [
            dict(zip(sutunlar, satir))
            for satir in imlec.fetchall()
        ]

    finally:
        imlec.close()
        baglanti.close()


def yuzde_yaz(deger, basamak=2):
    """Ondalık değeri yüzde biçiminde yazar."""

    if deger is None:
        return "-"

    return f"%{float(deger) * 100:.{basamak}f}"


def sinyali_goster(sinyal):
    """Bir sinyalin model ve gerçekleşen sonuçlarını gösterir."""

    print()
    print("=" * 60)
    print(f"Sembol: {sinyal['sembol']}")
    print(
        "Sinyal zamani (New York): "
        f"{sinyal['sinyal_zamani_new_york']}"
    )
    print(f"Veri donemi: {sinyal['veri_donemi']}")

    print()
    print("SINYAL ANINDAKI MODEL KARARLARI")

    for (
        model_adi,
        karar_sutunu,
        olasilik_sutunu,
    ) in MODEL_SUTUNLARI:
        karar = sinyal[karar_sutunu]
        olasilik = yuzde_yaz(
            sinyal[olasilik_sutunu]
        )

        print(
            f"{model_adi}: "
            f"{karar} | "
            f"Basari olasiligi: {olasilik}"
        )

    print()
    print("ENSEMBLE KARARI")
    print(
        f"Nihai karar: "
        f"{sinyal['ensemble_karari']}"
    )
    print(
        f"AL oy agirligi: "
        f"{yuzde_yaz(sinyal['al_oy_agirligi'])}"
    )
    print(
        f"NOTR oy agirligi: "
        f"{yuzde_yaz(sinyal['notr_oy_agirligi'])}"
    )
    print(
        f"ALMA oy agirligi: "
        f"{yuzde_yaz(sinyal['alma_oy_agirligi'])}"
    )

    print()
    print("SONRADAN GERCEKLESEN SONUC")
    print(f"Giris zamani: {sinyal['giris_zamani']}")
    print(f"Cikis zamani: {sinyal['cikis_zamani']}")
    print(
        f"Giris fiyati: "
        f"{float(sinyal['giris_fiyati']):.4f}"
    )
    print(
        f"Cikis fiyati: "
        f"{float(sinyal['cikis_fiyati']):.4f}"
    )
    print(
        f"Net getiri: "
        f"{yuzde_yaz(sinyal['net_getiri'], 4)}"
    )

    sonuc = (
        "BASARILI"
        if sinyal["basarili_mi"]
        else "BASARISIZ"
    )

    print(f"Gerceklesen sonuc: {sonuc}")


def argumanlari_al():
    """Komut satırı argümanlarını alır."""

    parser = argparse.ArgumentParser(
        description=(
            "Bir sembolün geçmiş sinyal kararlarını gösterir."
        )
    )

    parser.add_argument(
        "--sembol",
        required=True,
        help="Örnek: AAPL",
    )

    parser.add_argument(
        "--tarih",
        required=True,
        help="New York tarihine göre YYYY-AA-GG",
    )

    return parser.parse_args()


def main():
    """Seçilen sembol ve tarihteki sinyalleri gösterir."""

    argumanlar = argumanlari_al()

    try:
        tarih = datetime.strptime(
            argumanlar.tarih,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        raise ValueError(
            "Tarih YYYY-AA-GG biçiminde olmalıdır."
        )

    sinyaller = sinyalleri_getir(
        sembol=argumanlar.sembol,
        tarih=tarih,
    )

    if not sinyaller:
        print(
            f"{argumanlar.sembol.upper()} için "
            f"{tarih} tarihinde sinyal bulunamadı."
        )
        return

    print(
        f"Bulunan sinyal sayisi: "
        f"{len(sinyaller)}"
    )

    for sinyal in sinyaller:
        sinyali_goster(sinyal)


if __name__ == "__main__":
    main()