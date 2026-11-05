SELECT
    COUNT(*) AS toplam_satir,
    COUNT(DISTINCT menkul_kiymet_id) AS menkul_kiymet_sayisi,
    MIN(bar_zamani) AS ilk_bar,
    MAX(bar_zamani) AS son_bar
FROM ham_fiyat_verileri;


-- Bos veya gecersiz degerleri kontrol eder.
SELECT
    COUNT(*) FILTER (
        WHERE acilis IS NULL
           OR en_yuksek IS NULL
           OR en_dusuk IS NULL
           OR kapanis IS NULL
           OR hacim IS NULL
    ) AS bos_deger_sayisi,

    COUNT(*) FILTER (
        WHERE acilis <= 0
           OR en_yuksek <= 0
           OR en_dusuk <= 0
           OR kapanis <= 0
           OR hacim < 0
    ) AS gecersiz_deger_sayisi,

    COUNT(*) FILTER (
        WHERE en_yuksek < en_dusuk
           OR en_yuksek < acilis
           OR en_yuksek < kapanis
           OR en_dusuk > acilis
           OR en_dusuk > kapanis
    ) AS tutarsiz_fiyat_sayisi
FROM ham_fiyat_verileri;


-- 3. Bar zamanlarinin bes dakikaya uygunlugunu kontrol eder.
SELECT
    COUNT(*) AS hatali_zaman_hizasi
FROM ham_fiyat_verileri
WHERE EXTRACT(MINUTE FROM bar_zamani)::INTEGER % 5 <> 0
   OR EXTRACT(SECOND FROM bar_zamani) <> 0;


-- 4. Analiz tarih araligi disindaki verileri kontrol eder.
SELECT
    COUNT(*) AS tarih_araligi_disindaki_satir
FROM ham_fiyat_verileri
WHERE bar_zamani < TIMESTAMPTZ '2023-01-03 00:00:00+00'
   OR bar_zamani >= TIMESTAMPTZ '2024-04-01 00:00:00+00';


-- 5. Tekrarli barlari kontrol eder.
SELECT
    COUNT(*) AS tekrar_grubu
FROM (
    SELECT
        menkul_kiymet_id,
        bar_zamani,
        zaman_araligi_dakika
    FROM ham_fiyat_verileri
    GROUP BY
        menkul_kiymet_id,
        bar_zamani,
        zaman_araligi_dakika
    HAVING COUNT(*) > 1
) tekrarlar;


-- 6. Resmi piyasa saatleri disindaki satirlari kontrol eder.
SELECT
    COUNT(*) AS seans_disi_satir
FROM ham_fiyat_verileri hfv
WHERE NOT EXISTS (
    SELECT 1
    FROM piyasa_takvimi pt
    WHERE hfv.bar_zamani >= pt.piyasa_acilis_zamani
      AND hfv.bar_zamani < pt.piyasa_kapanis_zamani
);


-- 7. Piyasa takviminin genel bilgilerini kontrol eder.
SELECT
    COUNT(*) AS islem_gunu,
    COUNT(*) FILTER (
        WHERE erken_kapanis_mi = TRUE
    ) AS erken_kapanis_gunu,
    MIN(islem_tarihi) AS ilk_islem_gunu,
    MAX(islem_tarihi) AS son_islem_gunu
FROM piyasa_takvimi;