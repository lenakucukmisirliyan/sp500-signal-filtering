WITH donem_verileri AS (
    SELECT
        s.*,

        pk.spy_60dk_getiri,

        CASE
            WHEN s.veri_donemi = 'EGITIM'
                THEN 'EGITIM'

            WHEN s.veri_donemi = 'DOGRULAMA'
                THEN 'DOGRULAMA'

            WHEN s.veri_donemi = 'TEST'
                 AND s.sinyal_zamani
                     < TIMESTAMPTZ '2024-03-01 00:00:00+00'
                THEN 'IKINCIL_DOGRULAMA'

            ELSE 'NIHAI_TEST'
        END AS deney_donemi

    FROM
        islem_sinyalleri s,
        piyasa_kosullari pk

    WHERE s.sinyal_zamani = pk.bar_zamani
      AND s.doldurulmus_veri_var_mi = FALSE
)

SELECT
    deney_donemi,

    COUNT(*) AS filtresiz_sinyal,

    COUNT(*) FILTER (
        WHERE spy_60dk_getiri IS NULL
           OR spy_60dk_getiri >= -0.001
    ) AS filtreli_sinyal,

    ROUND(
        100.0 * (
            COUNT(*)
            - COUNT(*) FILTER (
                WHERE spy_60dk_getiri IS NULL
                   OR spy_60dk_getiri >= -0.001
            )
        ) / COUNT(*),
        2
    ) AS engelleme_orani,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE basarili_mi = TRUE
        ) / COUNT(*),
        2
    ) AS filtresiz_basari,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE basarili_mi = TRUE
              AND (
                  spy_60dk_getiri IS NULL
                  OR spy_60dk_getiri >= -0.001
              )
        )
        / COUNT(*) FILTER (
            WHERE spy_60dk_getiri IS NULL
               OR spy_60dk_getiri >= -0.001
        ),
        2
    ) AS filtreli_basari,

    ROUND(
        100.0 * AVG(net_getiri),
        4
    ) AS filtresiz_ortalama_getiri,

    ROUND(
        100.0 * AVG(net_getiri) FILTER (
            WHERE spy_60dk_getiri IS NULL
               OR spy_60dk_getiri >= -0.001
        ),
        4
    ) AS filtreli_ortalama_getiri

FROM donem_verileri

GROUP BY deney_donemi

ORDER BY
    CASE deney_donemi
        WHEN 'EGITIM' THEN 1
        WHEN 'DOGRULAMA' THEN 2
        WHEN 'IKINCIL_DOGRULAMA' THEN 3
        WHEN 'NIHAI_TEST' THEN 4
    END;