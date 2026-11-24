-- Geçmişte oluşmuş bir sinyal için bütün model kararlarını,
-- ensemble kararını ve sonradan gerçekleşen sonucu tek satırda gösterir.

CREATE OR REPLACE VIEW gecmis_sinyal_incelemesi AS

SELECT
    iss.sinyal_id,
    mk.sembol,
    iss.veri_donemi,

    iss.sinyal_zamani,

    (
        iss.sinyal_zamani
        AT TIME ZONE 'America/New_York'
    ) AS sinyal_zamani_new_york,

    iss.giris_zamani,
    iss.cikis_zamani,
    iss.giris_fiyati,
    iss.cikis_fiyati,
    iss.kisa_ortalama,
    iss.uzun_ortalama,
    iss.brut_getiri,
    iss.islem_maliyeti_orani,
    iss.net_getiri,
    iss.basarili_mi,

    -- Logistic Regression
    MAX(
        CASE
            WHEN msk.model_kodu = 'LOGISTIC_REGRESSION'
            THEN msk.basari_olasiligi
        END
    ) AS logistic_regression_olasiligi,

    MAX(
        CASE
            WHEN msk.model_kodu = 'LOGISTIC_REGRESSION'
            THEN msk.model_karari
        END
    ) AS logistic_regression_karari,

    -- Decision Tree
    MAX(
        CASE
            WHEN msk.model_kodu = 'DECISION_TREE'
            THEN msk.basari_olasiligi
        END
    ) AS decision_tree_olasiligi,

    MAX(
        CASE
            WHEN msk.model_kodu = 'DECISION_TREE'
            THEN msk.model_karari
        END
    ) AS decision_tree_karari,

    -- Random Forest
    MAX(
        CASE
            WHEN msk.model_kodu = 'RANDOM_FOREST'
            THEN msk.basari_olasiligi
        END
    ) AS random_forest_olasiligi,

    MAX(
        CASE
            WHEN msk.model_kodu = 'RANDOM_FOREST'
            THEN msk.model_karari
        END
    ) AS random_forest_karari,

    -- K-Nearest Neighbors
    MAX(
        CASE
            WHEN msk.model_kodu = 'KNN'
            THEN msk.basari_olasiligi
        END
    ) AS knn_olasiligi,

    MAX(
        CASE
            WHEN msk.model_kodu = 'KNN'
            THEN msk.model_karari
        END
    ) AS knn_karari,

    -- Gaussian Naive Bayes
    MAX(
        CASE
            WHEN msk.model_kodu = 'NAIVE_BAYES'
            THEN msk.basari_olasiligi
        END
    ) AS naive_bayes_olasiligi,

    MAX(
        CASE
            WHEN msk.model_kodu = 'NAIVE_BAYES'
            THEN msk.model_karari
        END
    ) AS naive_bayes_karari,

    -- Yapay sinir ağı
    MAX(
        CASE
            WHEN msk.model_kodu = 'YAPAY_SINIR_AGI'
            THEN msk.basari_olasiligi
        END
    ) AS yapay_sinir_agi_olasiligi,

    MAX(
        CASE
            WHEN msk.model_kodu = 'YAPAY_SINIR_AGI'
            THEN msk.model_karari
        END
    ) AS yapay_sinir_agi_karari,

    -- Ağırlıklı ensemble sonucu
    ek.al_oy_agirligi,
    ek.notr_oy_agirligi,
    ek.alma_oy_agirligi,
    ek.ensemble_karari

FROM islem_sinyalleri iss

INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
       iss.menkul_kiymet_id

INNER JOIN ensemble_kararlari ek
    ON ek.sinyal_id = iss.sinyal_id

INNER JOIN model_sinyal_kararlari msk
    ON msk.sinyal_id = iss.sinyal_id

GROUP BY
    iss.sinyal_id,
    mk.sembol,
    iss.veri_donemi,
    iss.sinyal_zamani,
    iss.giris_zamani,
    iss.cikis_zamani,
    iss.giris_fiyati,
    iss.cikis_fiyati,
    iss.kisa_ortalama,
    iss.uzun_ortalama,
    iss.brut_getiri,
    iss.islem_maliyeti_orani,
    iss.net_getiri,
    iss.basarili_mi,
    ek.al_oy_agirligi,
    ek.notr_oy_agirligi,
    ek.alma_oy_agirligi,
    ek.ensemble_karari;