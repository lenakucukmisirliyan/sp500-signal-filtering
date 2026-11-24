-- Projenin nihai veritabanı bütünlük kontrolleri.
-- Kontrol sonucundaki hatalı değerlerin tamamı 0 olmalıdır.


-- 1. Temel kayıt sayıları

SELECT
    (
        SELECT COUNT(*)
        FROM islem_sinyalleri
        WHERE doldurulmus_veri_var_mi = FALSE
    ) AS guvenilir_sinyal,

    (
        SELECT COUNT(*)
        FROM ensemble_kararlari
    ) AS ensemble_sinyali,

    (
        SELECT COUNT(*)
        FROM model_sinyal_kararlari
    ) AS model_karari,

    (
        SELECT COUNT(*)
        FROM gecmis_sinyal_incelemesi
    ) AS gecmis_inceleme_kaydi;


-- 2. Her sinyal için altı model kararı bulunmalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS alti_modeli_olmayan_sinyal
FROM (
    SELECT
        sinyal_id,
        COUNT(*) AS model_sayisi

    FROM model_sinyal_kararlari

    GROUP BY sinyal_id

    HAVING COUNT(*) <> 6
) hatali_sinyaller;


-- 3. Aynı sinyal ve model için tekrar eden karar olmamalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS tekrarli_model_karari
FROM (
    SELECT
        sinyal_id,
        model_kodu,
        COUNT(*) AS tekrar_sayisi

    FROM model_sinyal_kararlari

    GROUP BY
        sinyal_id,
        model_kodu

    HAVING COUNT(*) > 1
) tekrarlar;


-- 4. Her sinyal için yalnızca bir ensemble kararı olmalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS tekrarli_ensemble_karari
FROM (
    SELECT
        sinyal_id,
        COUNT(*) AS tekrar_sayisi

    FROM ensemble_kararlari

    GROUP BY sinyal_id

    HAVING COUNT(*) > 1
) tekrarlar;


-- 5. Ensemble oy ağırlıkları toplamı 1 olmalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS hatali_oy_toplami
FROM ensemble_kararlari
WHERE ABS(
    al_oy_agirligi
    + notr_oy_agirligi
    + alma_oy_agirligi
    - 1
) > 0.0001;


-- 6. Her dönemde model ağırlıkları toplamı 1 olmalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS hatali_model_agirligi
FROM (
    SELECT
        uygulama_donemi,
        SUM(model_agirligi) AS toplam_agirlik

    FROM model_agirliklari

    GROUP BY uygulama_donemi

    HAVING ABS(
        SUM(model_agirligi) - 1
    ) > 0.0001
) hatali_donemler;


-- 7. Geçersiz model kararları bulunmamalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS gecersiz_model_karari
FROM model_sinyal_kararlari
WHERE model_karari NOT IN (
    'AL',
    'NOTR',
    'ALMA'
)
OR model_karari IS NULL;


-- 8. Geçersiz ensemble kararları bulunmamalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS gecersiz_ensemble_karari
FROM ensemble_kararlari
WHERE ensemble_karari NOT IN (
    'AL',
    'NOTR',
    'ALMA'
)
OR ensemble_karari IS NULL;


-- 9. Model olasılıkları 0 ile 1 arasında olmalıdır.
-- Sonucun 0 olması beklenir.

SELECT COUNT(*) AS gecersiz_model_olasiligi
FROM model_sinyal_kararlari
WHERE basari_olasiligi < 0
   OR basari_olasiligi > 1
   OR basari_olasiligi IS NULL;


-- 10. Ensemble kayıtları ile geçmiş inceleme görünümü
-- aynı sayıda sinyal içermelidir.
-- Farkın 0 olması beklenir.

SELECT
    (
        SELECT COUNT(*)
        FROM ensemble_kararlari
    )
    -
    (
        SELECT COUNT(*)
        FROM gecmis_sinyal_incelemesi
    ) AS kayit_sayisi_farki;