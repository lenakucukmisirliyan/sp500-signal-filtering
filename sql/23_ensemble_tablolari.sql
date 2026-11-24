-- Modellerin her uygulama donemindeki
-- performansa dayali agirliklarini tutar.

CREATE TABLE IF NOT EXISTS model_agirliklari (
    model_agirlik_id INTEGER
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    uygulama_donemi VARCHAR(30) NOT NULL,

    model_kodu VARCHAR(30) NOT NULL,

    roc_auc NUMERIC(8, 6) NOT NULL,

    rastgele_ustu_puan NUMERIC(8, 6)
        NOT NULL,

    model_agirligi NUMERIC(8, 6)
        NOT NULL,

    agirlik_kaynagi VARCHAR(50) NOT NULL,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT gecerli_roc_auc
        CHECK (
            roc_auc >= 0
            AND roc_auc <= 1
        ),

    CONSTRAINT gecerli_model_agirligi
        CHECK (
            model_agirligi >= 0
            AND model_agirligi <= 1
        ),

    CONSTRAINT benzersiz_model_agirligi
        UNIQUE (
            uygulama_donemi,
            model_kodu
        )
);


-- Modellerin agirlikli oylarindan olusan
-- nihai ensemble kararlarini tutar.

CREATE TABLE IF NOT EXISTS ensemble_kararlari (
    ensemble_karar_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    sinyal_id BIGINT NOT NULL,

    deney_donemi VARCHAR(30) NOT NULL,

    al_oy_agirligi NUMERIC(8, 6)
        NOT NULL,

    notr_oy_agirligi NUMERIC(8, 6)
        NOT NULL,

    alma_oy_agirligi NUMERIC(8, 6)
        NOT NULL,

    ensemble_karari VARCHAR(10) NOT NULL,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_ensemble_sinyal
        FOREIGN KEY (sinyal_id)
        REFERENCES islem_sinyalleri (sinyal_id)
        ON DELETE CASCADE,

    CONSTRAINT gecerli_al_oyu
        CHECK (
            al_oy_agirligi >= 0
            AND al_oy_agirligi <= 1
        ),

    CONSTRAINT gecerli_notr_oyu
        CHECK (
            notr_oy_agirligi >= 0
            AND notr_oy_agirligi <= 1
        ),

    CONSTRAINT gecerli_alma_oyu
        CHECK (
            alma_oy_agirligi >= 0
            AND alma_oy_agirligi <= 1
        ),

    CONSTRAINT gecerli_ensemble_karari
        CHECK (
            ensemble_karari IN (
                'AL',
                'NOTR',
                'ALMA'
            )
        ),

    CONSTRAINT benzersiz_ensemble_karari
        UNIQUE (
            sinyal_id
        )
);


CREATE INDEX IF NOT EXISTS
    idx_ensemble_donem
ON ensemble_kararlari (
    deney_donemi
);


CREATE INDEX IF NOT EXISTS
    idx_ensemble_karar
ON ensemble_kararlari (
    ensemble_karari
);