-- Her donemde model agirliklarinin
-- toplaminin 1 olmasi beklenir.

SELECT
    uygulama_donemi,
    COUNT(*) AS model_sayisi,
    ROUND(
        SUM(model_agirligi),
        6
    ) AS toplam_agirlik

FROM model_agirliklari

GROUP BY uygulama_donemi

ORDER BY uygulama_donemi;


-- Her ensemble kararindaki oy agirliklarinin
-- toplaminin 1 olmasi beklenir.
-- Sonucun bos olmasi gerekir.

SELECT
    sinyal_id,
    (
        al_oy_agirligi
        + notr_oy_agirligi
        + alma_oy_agirligi
    ) AS toplam_oy

FROM ensemble_kararlari

WHERE ABS(
    (
        al_oy_agirligi
        + notr_oy_agirligi
        + alma_oy_agirligi
    ) - 1
) > 0.000010;


-- Ensemble kararlarinin gercek performansi.

SELECT
    ek.deney_donemi,
    ek.ensemble_karari,

    COUNT(*) AS sinyal_sayisi,

    ROUND(
        AVG(
            CASE
                WHEN ins.basarili_mi = TRUE
                    THEN 1.0
                ELSE 0.0
            END
        ) * 100,
        2
    ) AS basari_orani,

    ROUND(
        AVG(ins.net_getiri) * 100,
        4
    ) AS ortalama_net_getiri_yuzde

FROM
    ensemble_kararlari ek,
    islem_sinyalleri ins

WHERE ek.sinyal_id =
      ins.sinyal_id

GROUP BY
    ek.deney_donemi,
    ek.ensemble_karari

ORDER BY
    ek.deney_donemi,

    CASE ek.ensemble_karari
        WHEN 'AL' THEN 1
        WHEN 'NOTR' THEN 2
        WHEN 'ALMA' THEN 3
    END;