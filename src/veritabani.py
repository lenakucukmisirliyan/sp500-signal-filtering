import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


# Projenin ana klasorunu bulur.
PROJE_KLASORU = Path(__file__).resolve().parent.parent

# Ana klasordeki .env dosyasini okur.
load_dotenv(PROJE_KLASORU / ".env")


def veritabani_baglantisi_olustur():
    """PostgreSQL veritabanina baglanti olusturur."""

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    veritabani = os.getenv("POSTGRES_DB")
    kullanici = os.getenv("POSTGRES_USER")
    parola = os.getenv("POSTGRES_PASSWORD")

    ayarlar = {
        "POSTGRES_HOST": host,
        "POSTGRES_PORT": port,
        "POSTGRES_DB": veritabani,
        "POSTGRES_USER": kullanici,
        "POSTGRES_PASSWORD": parola,
    }

    eksik_ayarlar = [
        ayar_adi
        for ayar_adi, ayar_degeri in ayarlar.items()
        if not ayar_degeri
    ]

    if eksik_ayarlar:
        raise ValueError(
            "Eksik veritabani ayarlari: "
            + ", ".join(eksik_ayarlar)
        )

    return psycopg2.connect(
        host=host,
        port=int(port),
        dbname=veritabani,
        user=kullanici,
        password=parola,
        connect_timeout=10,
    )


def baglantiyi_test_et():
    """Baglantiyi test eder ve temel sunucu bilgilerini gosterir."""

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        imlec.execute(
            """
            SELECT
                current_database(),
                current_user,
                CURRENT_TIMESTAMP;
            """
        )

        veritabani, kullanici, sunucu_zamani = imlec.fetchone()

        print("PostgreSQL baglantisi basarili.")
        print(f"Veritabani: {veritabani}")
        print(f"Kullanici: {kullanici}")
        print(f"Sunucu zamani: {sunucu_zamani}")

    except (psycopg2.Error, ValueError) as hata:
        print(f"Baglanti hatasi: {hata}")

    finally:
        if imlec is not None:
            imlec.close()

        if baglanti is not None:
            baglanti.close()


if __name__ == "__main__":
    baglantiyi_test_et()