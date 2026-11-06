import pandas as pd

from src.makine_ogrenmesi_modeli import (
    OZELLIKLER,
    deney_donemlerini_olustur,
    model_olustur,
    veriyi_getir,
)


def ozellik_adini_duzenle(ozellik_adi):
    """Otomatik olusturulan eksik deger adlarini anlasilir hale getirir."""

    eksik_deger_eki = "missingindicator_"

    if ozellik_adi.startswith(eksik_deger_eki):
        asil_ozellik = ozellik_adi.replace(
            eksik_deger_eki,
            "",
            1
        )

        return asil_ozellik + "_eksik_mi"

    return ozellik_adi


def ozellik_onemlerini_hesapla():
    """Nihai Random Forest modelinin ozellik onemlerini gosterir."""

    veri = veriyi_getir()
    veri = deney_donemlerini_olustur(veri)

    # Nihai testten once kullanilabilen donemler.
    egitim_donemleri = [
        "EGITIM",
        "DOGRULAMA",
        "IKINCIL_DOGRULAMA",
    ]

    egitim_verisi = veri[
        veri["deney_donemi"].isin(
            egitim_donemleri
        )
    ].copy()

    egitim_ozellikleri = egitim_verisi[
        OZELLIKLER
    ]

    egitim_hedefi = (
        egitim_verisi["basarili_mi"]
        .astype(int)
    )

    model = model_olustur()

    model.fit(
        egitim_ozellikleri,
        egitim_hedefi
    )

    # Eksik deger doldurma adimindan sonra olusan
    # gercek ozellik adlarini alir.
    eksik_deger_adimi = model.named_steps[
        "eksik_deger"
    ]

    model_ozellikleri = (
        eksik_deger_adimi
        .get_feature_names_out(OZELLIKLER)
        .tolist()
    )

    model_ozellikleri = [
        ozellik_adini_duzenle(ozellik)
        for ozellik in model_ozellikleri
    ]

    random_forest = model.named_steps[
        "model"
    ]

    onem_degerleri = (
        random_forest.feature_importances_
    )

    if len(model_ozellikleri) != len(onem_degerleri):
        raise ValueError(
            "Ozellik adlari ile onem degerlerinin "
            "sayisi birbirinden farkli."
        )

    onemler = pd.DataFrame({
        "ozellik": model_ozellikleri,
        "onem": onem_degerleri,
    })

    onemler = onemler.sort_values(
        "onem",
        ascending=False
    ).reset_index(drop=True)

    onemler["onem_yuzde"] = (
        onemler["onem"] * 100
    )

    print(
        f"Egitimde kullanilan sinyal: "
        f"{len(egitim_verisi):,}"
    )

    print(
        f"Modelin kullandigi toplam ozellik: "
        f"{len(onemler)}"
    )

    print("\nRandom Forest ozellik onemleri:\n")

    for sira, satir in onemler.iterrows():
        print(
            f"{sira + 1}. "
            f"{satir['ozellik']}: "
            f"%{satir['onem_yuzde']:.2f}"
        )

    print(
        "\nOzellik onemleri toplami: "
        f"%{onemler['onem_yuzde'].sum():.2f}"
    )


if __name__ == "__main__":
    ozellik_onemlerini_hesapla()