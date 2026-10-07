from psycopg2.extras import execute_values

from src.piyasa_takvimi import nyse_takvimini_olustur
from src.veritabani import veritabani_baglantisi_olustur


def piyasa_takvimini_aktar():
    """NYSE takvimini PostgreSQL'e aktarir."""

    takvim = nyse_takvimini_olustur()

    kayitlar = []

    for satir in takvim.itertuples(index=False):
        kayitlar.append(
            (
                satir.islem_tarihi,
                satir.market_open.to_pydatetime(),
                satir.market_close.to_pydatetime(),
                int(satir.beklenen_bar_sayisi),
                bool(satir.beklenen_bar_sayisi < 78),
            )
        )

    baglanti = None
    imlec = None

    try:
        baglanti = veritabani_baglantisi_olustur()
        imlec = baglanti.cursor()

        execute_values(
            imlec,
            """
            INSERT INTO piyasa_takvimi (
                islem_tarihi,
                piyasa_acilis_zamani,
                piyasa_kapanis_zamani,
                beklenen_bar_sayisi,
                erken_kapanis_mi
            )
            VALUES %s
            ON CONFLICT (islem_tarihi)
            DO UPDATE SET
                piyasa_acilis_zamani =
                    EXCLUDED.piyasa_acilis_zamani,

                piyasa_kapanis_zamani =
                    EXCLUDED.piyasa_kapanis_zamani,

                beklenen_bar_sayisi =
                    EXCLUDED.beklenen_bar_sayisi,

                erken_kapanis_mi =
                    EXCLUDED.erken_kapanis_mi;
            """,
            kayitlar,
            page_size=500,
        )

        baglanti.commit()

        print("Piyasa takvimi aktarildi.")
        print(f"Islem gunu sayisi: {len(kayitlar)}")

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
    piyasa_takvimini_aktar()