import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


PROJE_KLASORU = Path(__file__).resolve().parent.parent

load_dotenv(PROJE_KLASORU / ".env")


def veritabani_baglantisi_olustur():

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