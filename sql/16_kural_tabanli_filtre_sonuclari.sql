SELECT
    s.veri_donemi,

    COUNT(*) AS filtresiz_sinyal,

    COUNT(*) FILTER (
        WHERE pk.spy_er12 >= 0.20
    ) AS filtreli_sinyal,

    ROUND(
        100.0 * (
            COUNT(*)
            - COUNT(*) FILTER (
                WHERE pk.spy_er12 >= 0.20
            )
        ) / COUNT(*),
        2
    ) AS engelleme_orani,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE s.basarili_mi = TRUE
        ) / COUNT(*),
        2
    ) AS filtresiz_basari,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE s.basarili_mi = TRUE
              AND pk.spy_er12 >= 0.20
        )
        / COUNT(*) FILTER (
            WHERE pk.spy_er12 >= 0.20
        ),
        2
    ) AS filtreli_basari,

    ROUND(
        100.0 * AVG(s.net_getiri),
        4
    ) AS filtresiz_ortalama_getiri,

    ROUND(
        100.0 * AVG(s.net_getiri) FILTER (
            WHERE pk.spy_er12 >= 0.20
        ),
        4
    ) AS filtreli_ortalama_getiri

FROM
    islem_sinyalleri s,
    piyasa_kosullari pk

WHERE s.sinyal_zamani = pk.bar_zamani
  AND s.doldurulmus_veri_var_mi = FALSE

GROUP BY s.veri_donemi

ORDER BY
    CASE s.veri_donemi
        WHEN 'EGITIM' THEN 1
        WHEN 'DOGRULAMA' THEN 2
        WHEN 'TEST' THEN 3
    END;