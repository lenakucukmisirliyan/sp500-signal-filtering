-- Filtresiz, kural tabanlı, Random Forest ve ağırlıklı
-- ensemble sonuçlarını aynı performans ölçüleriyle karşılaştırır.
--
-- Ensemble yönteminde ALMA kararı verilen sinyaller engellenir.
-- AL ve NOTR kararları verilen sinyaller kullanılmaya devam eder.

CREATE OR REPLACE VIEW genisletilmis_performans_sonuclari AS

WITH ensemble_verileri AS (
    SELECT
        ek.deney_donemi,
        ek.ensemble_karari,
        iss.basarili_mi,
        iss.net_getiri

    FROM ensemble_kararlari ek

    INNER JOIN islem_sinyalleri iss
        ON iss.sinyal_id = ek.sinyal_id
),

ensemble_temel_sonuclar AS (
    SELECT
        deney_donemi,

        COUNT(*) AS toplam_sinyal_sayisi,

        COUNT(*) FILTER (
            WHERE ensemble_karari <> 'ALMA'
        ) AS kullanilan_sinyal_sayisi,

        COUNT(*) FILTER (
            WHERE ensemble_karari = 'ALMA'
        ) AS engellenen_sinyal_sayisi,

        (
            COUNT(*) FILTER (
                WHERE ensemble_karari = 'ALMA'
            )::NUMERIC
            / COUNT(*)
            * 100
        ) AS engelleme_orani_yuzde,

        (
            AVG(
                basarili_mi::INTEGER
            ) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
            * 100
        ) AS basari_orani_yuzde,

        (
            AVG(net_getiri) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
            * 100
        ) AS ortalama_net_getiri_yuzde,

        (
            PERCENTILE_CONT(0.50)
            WITHIN GROUP (
                ORDER BY net_getiri
            ) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
            * 100
        ) AS medyan_net_getiri_yuzde,

        (
            STDDEV_SAMP(net_getiri) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
            * 100
        ) AS getiri_standart_sapmasi_yuzde,

        (
            MIN(net_getiri) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
            * 100
        ) AS en_kotu_getiri_yuzde,

        (
            MAX(net_getiri) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
            * 100
        ) AS en_iyi_getiri_yuzde,

        (
            PERCENTILE_CONT(0.05)
            WITHIN GROUP (
                ORDER BY net_getiri
            ) FILTER (
                WHERE ensemble_karari <> 'ALMA'
            )
        ) AS alt_yuzde_5_esigi

    FROM ensemble_verileri

    GROUP BY deney_donemi
),

ensemble_alt_yuzde_5 AS (
    SELECT
        ets.deney_donemi,

        (
            AVG(ev.net_getiri)
            * 100
        ) AS en_kotu_yuzde_5_ortalama_getiri

    FROM ensemble_temel_sonuclar ets

    INNER JOIN ensemble_verileri ev
        ON ev.deney_donemi =
           ets.deney_donemi

    WHERE ev.ensemble_karari <> 'ALMA'
      AND ev.net_getiri <=
          ets.alt_yuzde_5_esigi

    GROUP BY ets.deney_donemi
),

ensemble_sonuclari AS (
    SELECT
        ets.deney_donemi,

        'AGIRLIKLI_ENSEMBLE'::VARCHAR
            AS yontem,

        ets.toplam_sinyal_sayisi,
        ets.kullanilan_sinyal_sayisi,
        ets.engellenen_sinyal_sayisi,

        ROUND(
            ets.engelleme_orani_yuzde,
            2
        ) AS engelleme_orani_yuzde,

        ROUND(
            ets.basari_orani_yuzde,
            2
        ) AS basari_orani_yuzde,

        ROUND(
            ets.ortalama_net_getiri_yuzde,
            4
        ) AS ortalama_net_getiri_yuzde,

        ROUND(
            ets.medyan_net_getiri_yuzde::NUMERIC,
            4
        ) AS medyan_net_getiri_yuzde,

        ROUND(
            ets.getiri_standart_sapmasi_yuzde,
            4
        ) AS getiri_standart_sapmasi_yuzde,

        ROUND(
            ets.en_kotu_getiri_yuzde,
            4
        ) AS en_kotu_getiri_yuzde,

        ROUND(
            ets.en_iyi_getiri_yuzde,
            4
        ) AS en_iyi_getiri_yuzde,

        ROUND(
            (
                ets.alt_yuzde_5_esigi
                * 100
            )::NUMERIC,
            4
        ) AS alt_yuzde_5_getiri_esigi,

        ROUND(
            eay.en_kotu_yuzde_5_ortalama_getiri,
            4
        ) AS en_kotu_yuzde_5_ortalama_getiri

    FROM ensemble_temel_sonuclar ets

    INNER JOIN ensemble_alt_yuzde_5 eay
        ON eay.deney_donemi =
           ets.deney_donemi
)

SELECT
    deney_donemi,
    yontem,
    toplam_sinyal_sayisi,
    kullanilan_sinyal_sayisi,
    engellenen_sinyal_sayisi,
    engelleme_orani_yuzde,
    basari_orani_yuzde,
    ortalama_net_getiri_yuzde,
    medyan_net_getiri_yuzde,
    getiri_standart_sapmasi_yuzde,
    en_kotu_getiri_yuzde,
    en_iyi_getiri_yuzde,
    alt_yuzde_5_getiri_esigi,
    en_kotu_yuzde_5_ortalama_getiri

FROM performans_sonuclari

UNION ALL

SELECT
    deney_donemi,
    yontem,
    toplam_sinyal_sayisi,
    kullanilan_sinyal_sayisi,
    engellenen_sinyal_sayisi,
    engelleme_orani_yuzde,
    basari_orani_yuzde,
    ortalama_net_getiri_yuzde,
    medyan_net_getiri_yuzde,
    getiri_standart_sapmasi_yuzde,
    en_kotu_getiri_yuzde,
    en_iyi_getiri_yuzde,
    alt_yuzde_5_getiri_esigi,
    en_kotu_yuzde_5_ortalama_getiri

FROM ensemble_sonuclari;