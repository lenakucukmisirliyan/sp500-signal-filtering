-- Model karar kayitlarinin genel kontrolu.

SELECT
    COUNT(*) AS toplam_kayit,
    COUNT(DISTINCT sinyal_id)
        AS benzersiz_sinyal,
    COUNT(DISTINCT model_kodu)
        AS model_sayisi
FROM model_sinyal_kararlari;


-- Her sinyal icin alti model karari bulunmalidir.
-- Sonucun bos olmasi beklenir.

SELECT
    sinyal_id,
    COUNT(*) AS karar_sayisi
FROM model_sinyal_kararlari
GROUP BY sinyal_id
HAVING COUNT(*) <> 6;


-- Her model kararinin gercek performansi.

SELECT
    msk.deney_donemi,
    msk.model_kodu,
    msk.model_karari,

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
    model_sinyal_kararlari msk,
    islem_sinyalleri ins

WHERE msk.sinyal_id =
      ins.sinyal_id

GROUP BY
    msk.deney_donemi,
    msk.model_kodu,
    msk.model_karari

ORDER BY
    msk.deney_donemi,
    msk.model_kodu,

    CASE msk.model_karari
        WHEN 'AL' THEN 1
        WHEN 'NOTR' THEN 2
        WHEN 'ALMA' THEN 3
    END;