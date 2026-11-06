-- Filtresiz, kural tabanli ve Random Forest
-- sonuclarini performans ve risk acisindan karsilastirir.


DROP VIEW IF EXISTS performans_sonuclari;


CREATE VIEW performans_sonuclari AS

WITH tum_yontemler AS (

    -- 1. FILTRESIZ YONTEM
    -- Butun sinyaller kullanilir.
    SELECT
        fs.deney_donemi,
        'FILTRESIZ'::VARCHAR(30) AS yontem,
        TRUE AS izin_verildi_mi,
        s.basarili_mi,
        s.net_getiri

    FROM
        filtre_sonuclari fs,
        islem_sinyalleri s

    WHERE fs.sinyal_id = s.sinyal_id


    UNION ALL


    -- 2. KURAL TABANLI FILTRE
    SELECT
        fs.deney_donemi,
        'KURAL_TABANLI'::VARCHAR(30) AS yontem,
        fs.kural_izin_verdi_mi AS izin_verildi_mi,
        s.basarili_mi,
        s.net_getiri

    FROM
        filtre_sonuclari fs,
        islem_sinyalleri s

    WHERE fs.sinyal_id = s.sinyal_id


    UNION ALL


    -- 3. RANDOM FOREST FILTRESI
    SELECT
        fs.deney_donemi,
        'RANDOM_FOREST'::VARCHAR(30) AS yontem,
        fs.ml_izin_verdi_mi AS izin_verildi_mi,
        s.basarili_mi,
        s.net_getiri

    FROM
        filtre_sonuclari fs,
        islem_sinyalleri s

    WHERE fs.sinyal_id = s.sinyal_id
),

yontem_ozetleri AS (

    SELECT
        deney_donemi,
        yontem,

        COUNT(*) AS toplam_sinyal_sayisi,

        COUNT(*) FILTER (
            WHERE izin_verildi_mi = TRUE
        ) AS kullanilan_sinyal_sayisi,

        COUNT(*) FILTER (
            WHERE izin_verildi_mi = FALSE
        ) AS engellenen_sinyal_sayisi,

        ROUND(
            100.0
            * COUNT(*) FILTER (
                WHERE izin_verildi_mi = FALSE
            )
            / COUNT(*),
            2
        ) AS engelleme_orani_yuzde,

        ROUND(
            100.0
            * AVG(
                basarili_mi::INTEGER
            ) FILTER (
                WHERE izin_verildi_mi = TRUE
            ),
            2
        ) AS basari_orani_yuzde,

        ROUND(
            100.0
            * AVG(net_getiri) FILTER (
                WHERE izin_verildi_mi = TRUE
            ),
            4
        ) AS ortalama_net_getiri_yuzde,

        ROUND(
            100.0
            * PERCENTILE_CONT(0.50)
                WITHIN GROUP (
                    ORDER BY net_getiri
                ) FILTER (
                    WHERE izin_verildi_mi = TRUE
                )::NUMERIC,
            4
        ) AS medyan_net_getiri_yuzde,

        ROUND(
            100.0
            * STDDEV_SAMP(net_getiri) FILTER (
                WHERE izin_verildi_mi = TRUE
            ),
            4
        ) AS getiri_standart_sapmasi_yuzde,

        ROUND(
            100.0
            * MIN(net_getiri) FILTER (
                WHERE izin_verildi_mi = TRUE
            ),
            4
        ) AS en_kotu_getiri_yuzde,

        ROUND(
            100.0
            * MAX(net_getiri) FILTER (
                WHERE izin_verildi_mi = TRUE
            ),
            4
        ) AS en_iyi_getiri_yuzde,

        PERCENTILE_CONT(0.05)
            WITHIN GROUP (
                ORDER BY net_getiri
            ) FILTER (
                WHERE izin_verildi_mi = TRUE
            ) AS alt_yuzde_5_esigi

    FROM tum_yontemler

    GROUP BY
        deney_donemi,
        yontem
)

SELECT
    yo.deney_donemi,
    yo.yontem,
    yo.toplam_sinyal_sayisi,
    yo.kullanilan_sinyal_sayisi,
    yo.engellenen_sinyal_sayisi,
    yo.engelleme_orani_yuzde,
    yo.basari_orani_yuzde,
    yo.ortalama_net_getiri_yuzde,
    yo.medyan_net_getiri_yuzde,
    yo.getiri_standart_sapmasi_yuzde,
    yo.en_kotu_getiri_yuzde,
    yo.en_iyi_getiri_yuzde,

    ROUND(
        100.0
        * yo.alt_yuzde_5_esigi::NUMERIC,
        4
    ) AS alt_yuzde_5_getiri_esigi,

    ROUND(
        100.0
        * AVG(ty.net_getiri) FILTER (
            WHERE ty.izin_verildi_mi = TRUE
              AND ty.net_getiri
                  <= yo.alt_yuzde_5_esigi
        ),
        4
    ) AS en_kotu_yuzde_5_ortalama_getiri

FROM yontem_ozetleri yo

INNER JOIN tum_yontemler ty
    ON ty.deney_donemi = yo.deney_donemi
    AND ty.yontem = yo.yontem

GROUP BY
    yo.deney_donemi,
    yo.yontem,
    yo.toplam_sinyal_sayisi,
    yo.kullanilan_sinyal_sayisi,
    yo.engellenen_sinyal_sayisi,
    yo.engelleme_orani_yuzde,
    yo.basari_orani_yuzde,
    yo.ortalama_net_getiri_yuzde,
    yo.medyan_net_getiri_yuzde,
    yo.getiri_standart_sapmasi_yuzde,
    yo.en_kotu_getiri_yuzde,
    yo.en_iyi_getiri_yuzde,
    yo.alt_yuzde_5_esigi;