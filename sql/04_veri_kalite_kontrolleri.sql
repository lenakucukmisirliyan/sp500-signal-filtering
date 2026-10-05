SELECT
    COUNT(*) AS toplam_satir,
    COUNT(*) - COUNT(
        DISTINCT (
            menkul_kiymet_id,
            bar_zamani,
            zaman_araligi_dakika
        )
    ) AS tekrar_sayisi
FROM ham_fiyat_verileri;