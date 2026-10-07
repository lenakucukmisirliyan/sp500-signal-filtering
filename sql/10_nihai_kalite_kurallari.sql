-- Gunluk verilerin nihai kalite kararlarini saklamak icin
-- gunluk_veri_kalitesi tablosuna yeni sutunlar ekler.

ALTER TABLE gunluk_veri_kalitesi
ADD COLUMN IF NOT EXISTS acilis_bari_var_mi BOOLEAN;

ALTER TABLE gunluk_veri_kalitesi
ADD COLUMN IF NOT EXISTS en_uzun_eksik_seri SMALLINT;

ALTER TABLE gunluk_veri_kalitesi
ADD COLUMN IF NOT EXISTS nihai_kalite_durumu VARCHAR(20);

ALTER TABLE gunluk_veri_kalitesi
ADD COLUMN IF NOT EXISTS eleme_nedeni VARCHAR(100);


-- Dosya yeniden calistirilirsa once onceki sonuclari temizler.

UPDATE gunluk_veri_kalitesi
SET
    acilis_bari_var_mi = NULL,
    en_uzun_eksik_seri = NULL,
    nihai_kalite_durumu = NULL,
    eleme_nedeni = NULL;


-- Her sembol-gunun acilis barinin bulunup bulunmadigini kontrol eder.

UPDATE gunluk_veri_kalitesi gvk
SET acilis_bari_var_mi = EXISTS (
    SELECT 1

    FROM piyasa_takvimi pt

    INNER JOIN ham_fiyat_verileri hfv
        ON hfv.menkul_kiymet_id =
            gvk.menkul_kiymet_id
        AND hfv.bar_zamani =
            pt.piyasa_acilis_zamani
        AND hfv.zaman_araligi_dakika = 5

    WHERE pt.islem_tarihi =
        gvk.islem_tarihi
);


-- Doldurulabilir gunlerdeki beklenen 5 dakikalik barlari olusturur.

WITH beklenen_barlar AS (
    SELECT
        gvk.menkul_kiymet_id,
        gvk.islem_tarihi,

        generate_series(
            pt.piyasa_acilis_zamani,
            pt.piyasa_kapanis_zamani
                - INTERVAL '5 minutes',
            INTERVAL '5 minutes'
        ) AS beklenen_bar_zamani

    FROM gunluk_veri_kalitesi gvk

    INNER JOIN piyasa_takvimi pt
        ON pt.islem_tarihi =
            gvk.islem_tarihi

    WHERE gvk.kalite_durumu =
        'DOLDURULABILIR'
),

eksik_barlar AS (
    SELECT
        bb.menkul_kiymet_id,
        bb.islem_tarihi,
        bb.beklenen_bar_zamani

    FROM beklenen_barlar bb

    LEFT JOIN ham_fiyat_verileri hfv
        ON hfv.menkul_kiymet_id =
            bb.menkul_kiymet_id
        AND hfv.bar_zamani =
            bb.beklenen_bar_zamani
        AND hfv.zaman_araligi_dakika = 5

    WHERE hfv.bar_zamani IS NULL
),

sirali_eksikler AS (
    SELECT
        menkul_kiymet_id,
        islem_tarihi,
        beklenen_bar_zamani,

        beklenen_bar_zamani
        - (
            ROW_NUMBER() OVER (
                PARTITION BY
                    menkul_kiymet_id,
                    islem_tarihi
                ORDER BY
                    beklenen_bar_zamani
            )
            * INTERVAL '5 minutes'
        ) AS seri_grubu

    FROM eksik_barlar
),

eksik_seriler AS (
    SELECT
        menkul_kiymet_id,
        islem_tarihi,
        seri_grubu,
        COUNT(*) AS seri_uzunlugu

    FROM sirali_eksikler

    GROUP BY
        menkul_kiymet_id,
        islem_tarihi,
        seri_grubu
),

gunluk_en_uzun_seri AS (
    SELECT
        menkul_kiymet_id,
        islem_tarihi,
        MAX(seri_uzunlugu) AS en_uzun_eksik_seri

    FROM eksik_seriler

    GROUP BY
        menkul_kiymet_id,
        islem_tarihi
)

UPDATE gunluk_veri_kalitesi gvk
SET en_uzun_eksik_seri =
    geus.en_uzun_eksik_seri

FROM gunluk_en_uzun_seri geus

WHERE gvk.menkul_kiymet_id =
        geus.menkul_kiymet_id
  AND gvk.islem_tarihi =
        geus.islem_tarihi;


-- Nihai kalite kararini verir.

UPDATE gunluk_veri_kalitesi
SET
    nihai_kalite_durumu =
        CASE
            WHEN kalite_durumu = 'TAM'
                THEN 'TUTULDU'

            WHEN kalite_durumu = 'DOLDURULABILIR'
                 AND acilis_bari_var_mi = TRUE
                 AND en_uzun_eksik_seri <= 3
                THEN 'DOLDURULACAK'

            ELSE 'ELENDI'
        END,

    eleme_nedeni =
        CASE
            WHEN kalite_durumu = 'ELENDI'
                THEN 'KAPSAMA_YUZDE_80_ALTINDA'

            WHEN kalite_durumu = 'DOLDURULABILIR'
                 AND acilis_bari_var_mi = FALSE
                THEN 'ACILIS_BARI_EKSIK'

            WHEN kalite_durumu = 'DOLDURULABILIR'
                 AND en_uzun_eksik_seri >= 4
                THEN 'UZUN_EKSIK_BAR_SERISI'

            ELSE NULL
        END;


-- Nihai sonuclari kontrol eder.

SELECT
    nihai_kalite_durumu,
    COUNT(*) AS sembol_gun_sayisi

FROM gunluk_veri_kalitesi

GROUP BY nihai_kalite_durumu

ORDER BY nihai_kalite_durumu;


-- Elenme nedenlerini kontrol eder.

SELECT
    eleme_nedeni,
    COUNT(*) AS sembol_gun_sayisi

FROM gunluk_veri_kalitesi

WHERE nihai_kalite_durumu = 'ELENDI'

GROUP BY eleme_nedeni

ORDER BY sembol_gun_sayisi DESC;

COMMIT;