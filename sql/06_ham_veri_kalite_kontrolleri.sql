-- Ham fiyat verilerinin kalite kontrolleri.


-- 1. Genel veri kapsami
SELECT
    COUNT(*) AS toplam_satir,
    COUNT(DISTINCT menkul_kiymet_id)
        AS menkul_kiymet_sayisi,
    MIN(bar_zamani) AS ilk_bar,
    MAX(bar_zamani) AS son_bar
FROM ham_fiyat_verileri;


-- 2. Bos deger kontrolleri
SELECT
    COUNT(*) FILTER (
        WHERE acilis IS NULL
    ) AS bos_acilis,

    COUNT(*) FILTER (
        WHERE en_yuksek IS NULL
    ) AS bos_en_yuksek,

    COUNT(*) FILTER (
        WHERE en_dusuk IS NULL
    ) AS bos_en_dusuk,

    COUNT(*) FILTER (
        WHERE kapanis IS NULL
    ) AS bos_kapanis,

    COUNT(*) FILTER (
        WHERE hacim IS NULL
    ) AS bos_hacim,

    COUNT(*) FILTER (
        WHERE islem_sayisi IS NULL
    ) AS bos_islem_sayisi,

    COUNT(*) FILTER (
        WHERE hacim_agirlikli_ortalama_fiyat IS NULL
    ) AS bos_vwap
FROM ham_fiyat_verileri;


-- 3. Gecersiz sayisal deger kontrolleri
SELECT
    COUNT(*) FILTER (
        WHERE acilis <= 0
    ) AS gecersiz_acilis,

    COUNT(*) FILTER (
        WHERE en_yuksek <= 0
    ) AS gecersiz_en_yuksek,

    COUNT(*) FILTER (
        WHERE en_dusuk <= 0
    ) AS gecersiz_en_dusuk,

    COUNT(*) FILTER (
        WHERE kapanis <= 0
    ) AS gecersiz_kapanis,

    COUNT(*) FILTER (
        WHERE hacim < 0
    ) AS negatif_hacim,

    COUNT(*) FILTER (
        WHERE islem_sayisi < 0
    ) AS negatif_islem_sayisi,

    COUNT(*) FILTER (
        WHERE hacim_agirlikli_ortalama_fiyat <= 0
    ) AS gecersiz_vwap
FROM ham_fiyat_verileri;


-- 4. OHLC fiyat tutarliligi
SELECT
    COUNT(*) FILTER (
        WHERE en_yuksek < en_dusuk
    ) AS yuksek_dusukten_kucuk,

    COUNT(*) FILTER (
        WHERE en_yuksek < acilis
    ) AS yuksek_acilistan_kucuk,

    COUNT(*) FILTER (
        WHERE en_yuksek < kapanis
    ) AS yuksek_kapanistan_kucuk,

    COUNT(*) FILTER (
        WHERE en_dusuk > acilis
    ) AS dusuk_acilistan_buyuk,

    COUNT(*) FILTER (
        WHERE en_dusuk > kapanis
    ) AS dusuk_kapanistan_buyuk
FROM ham_fiyat_verileri;


-- 5. Bes dakikalik zaman hizasi kontrolu
SELECT
    COUNT(*) AS hatali_zaman_hizasi
FROM ham_fiyat_verileri
WHERE
    EXTRACT(MINUTE FROM bar_zamani)::INTEGER % 5 <> 0
    OR EXTRACT(SECOND FROM bar_zamani) <> 0;


-- 6. Analiz tarih araligi disindaki veriler
SELECT
    COUNT(*) AS tarih_araligi_disindaki_satir
FROM ham_fiyat_verileri
WHERE
    bar_zamani
        < TIMESTAMPTZ '2023-01-03 00:00:00+00'
    OR
    bar_zamani
        >= TIMESTAMPTZ '2024-04-01 00:00:00+00';


-- 7. Tekrarli bar kontrolu
SELECT
    COUNT(*) AS tekrar_grubu
FROM (
    SELECT
        menkul_kiymet_id,
        bar_zamani,
        zaman_araligi_dakika,
        COUNT(*)
    FROM ham_fiyat_verileri
    GROUP BY
        menkul_kiymet_id,
        bar_zamani,
        zaman_araligi_dakika
    HAVING COUNT(*) > 1
) tekrarlar;


-- 8. Resmi NYSE takvimine gore normal seans ve seans disi
-- Erken kapanis gunleri de dogru bicimde dikkate alinir.
SELECT
    COUNT(*) FILTER (
        WHERE pt.islem_tarihi IS NOT NULL
    ) AS normal_seans_satiri,

    COUNT(*) FILTER (
        WHERE pt.islem_tarihi IS NULL
    ) AS seans_disi_satir
FROM ham_fiyat_verileri hfv
LEFT JOIN piyasa_takvimi pt
    ON pt.islem_tarihi =
        (
            hfv.bar_zamani
            AT TIME ZONE 'America/New_York'
        )::DATE
    AND hfv.bar_zamani >= pt.piyasa_acilis_zamani
    AND hfv.bar_zamani < pt.piyasa_kapanis_zamani;


-- 9. Piyasa takviminin genel kontrolu
SELECT
    COUNT(*) AS islem_gunu,
    COUNT(*) FILTER (
        WHERE erken_kapanis_mi = TRUE
    ) AS erken_kapanis_gunu,
    MIN(islem_tarihi) AS ilk_islem_gunu,
    MAX(islem_tarihi) AS son_islem_gunu
FROM piyasa_takvimi;


-- 10. Erken kapanis gunleri
SELECT
    islem_tarihi,
    piyasa_acilis_zamani,
    piyasa_kapanis_zamani,
    beklenen_bar_sayisi,
    erken_kapanis_mi
FROM piyasa_takvimi
WHERE erken_kapanis_mi = TRUE
ORDER BY islem_tarihi;


-- 11. SPY verisinin resmi takvime gore gunluk kapsami
SELECT
    pt.islem_tarihi,
    pt.beklenen_bar_sayisi,
    COUNT(hfv.bar_zamani) AS bulunan_bar_sayisi
FROM piyasa_takvimi pt
INNER JOIN menkul_kiymetler mk
    ON mk.sembol = 'SPY'
LEFT JOIN ham_fiyat_verileri hfv
    ON hfv.menkul_kiymet_id = mk.menkul_kiymet_id
    AND hfv.bar_zamani >= pt.piyasa_acilis_zamani
    AND hfv.bar_zamani < pt.piyasa_kapanis_zamani
GROUP BY
    pt.islem_tarihi,
    pt.beklenen_bar_sayisi
ORDER BY pt.islem_tarihi;


-- 12. SPY gunlerinde beklenen ve bulunan bar farklari
-- Sonucun bos olmasi beklenir.
WITH spy_gunluk AS (
    SELECT
        pt.islem_tarihi,
        pt.beklenen_bar_sayisi,
        COUNT(hfv.bar_zamani) AS bulunan_bar_sayisi
    FROM piyasa_takvimi pt
    INNER JOIN menkul_kiymetler mk
        ON mk.sembol = 'SPY'
    LEFT JOIN ham_fiyat_verileri hfv
        ON hfv.menkul_kiymet_id =
            mk.menkul_kiymet_id
        AND hfv.bar_zamani >=
            pt.piyasa_acilis_zamani
        AND hfv.bar_zamani <
            pt.piyasa_kapanis_zamani
    GROUP BY
        pt.islem_tarihi,
        pt.beklenen_bar_sayisi
)
SELECT *
FROM spy_gunluk
WHERE bulunan_bar_sayisi <> beklenen_bar_sayisi
ORDER BY islem_tarihi;