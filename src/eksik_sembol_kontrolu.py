from datetime import datetime, timezone

from src.alpaca_verisi import fiyat_verisi_indir
from src.veritabani import veritabani_baglantisi_olustur


def eksik_sembolleri_getir():
    """Alpaca katalog bilgisinin bulunamadigi sembolleri veritabanindan getirir."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        imlec.execute(
            """
            SELECT sembol
            FROM menkul_kiymetler
            WHERE aktif_mi = FALSE
            ORDER BY sembol;
            """
        )

        return [satir[0] for satir in imlec.fetchall()]

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


def tarihsel_veriyi_kontrol_et():
    """Eksik sembollerin 2023 yilindaki fiyat verilerini kontrol eder."""

    semboller = eksik_sembolleri_getir()

    print(f"Kontrol edilecek sembol sayisi: {len(semboller)}")
    print(", ".join(semboller))

    baslangic = datetime(2023, 1, 3, tzinfo=timezone.utc)
    bitis = datetime(2023, 1, 6, tzinfo=timezone.utc)

    veri = fiyat_verisi_indir(
        semboller=semboller,
        baslangic=baslangic,
        bitis=bitis,
        zaman_araligi_dakika=5,
    )

    if veri.empty:
        print("Hicbir sembol icin fiyat verisi bulunamadi.")
        return

    bulunan_semboller = sorted(veri["symbol"].unique().tolist())
    bulunamayan_semboller = sorted(set(semboller) - set(bulunan_semboller))

    satir_sayilari = (
        veri.groupby("symbol")
        .size()
        .sort_index()
    )

    print("\nFiyat verisi bulunan semboller:")
    for sembol, satir_sayisi in satir_sayilari.items():
        print(f"{sembol}: {satir_sayisi} satir")

    print(f"\nFiyat verisi bulunan: {len(bulunan_semboller)}")
    print(f"Fiyat verisi bulunamayan: {len(bulunamayan_semboller)}")

    if bulunamayan_semboller:
        print(
            "Fiyat verisi bulunamayan semboller: "
            + ", ".join(bulunamayan_semboller)
        )



def sembol_degisimlerini_kontrol_et():
    """Sonradan kullanilmaya baslanan sembolleri uygun tarihlerde kontrol eder."""

    kontroller = [
        {
            "sembol": "FI",
            "baslangic": datetime(2023, 6, 7, tzinfo=timezone.utc),
            "bitis": datetime(2023, 6, 10, tzinfo=timezone.utc),
        },
        {
            "sembol": "DAY",
            "baslangic": datetime(2024, 2, 1, tzinfo=timezone.utc),
            "bitis": datetime(2024, 2, 6, tzinfo=timezone.utc),
        },
    ]

    print("\nSembol degisikligi kontrolleri:")

    for kontrol in kontroller:
        sembol = kontrol["sembol"]

        veri = fiyat_verisi_indir(
            semboller=[sembol],
            baslangic=kontrol["baslangic"],
            bitis=kontrol["bitis"],
            zaman_araligi_dakika=5,
        )

        if veri.empty:
            print(f"{sembol}: Veri bulunamadi.")
        else:
            print(
                f"{sembol}: {len(veri)} satir bulundu | "
                f"Ilk bar: {veri['timestamp'].min()} | "
                f"Son bar: {veri['timestamp'].max()}"
            )


if __name__ == "__main__":
    tarihsel_veriyi_kontrol_et()
    sembol_degisimlerini_kontrol_et()