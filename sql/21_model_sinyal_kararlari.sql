-- Her makine ogrenmesi modelinin
-- her sinyal icin verdigi karari tutar.

CREATE TABLE IF NOT EXISTS model_sinyal_kararlari (
    model_karar_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    sinyal_id BIGINT NOT NULL,

    deney_donemi VARCHAR(30) NOT NULL,

    model_kodu VARCHAR(30) NOT NULL,

    basari_olasiligi NUMERIC(12, 10) NOT NULL,

    alma_esigi NUMERIC(12, 10) NOT NULL,

    al_esigi NUMERIC(12, 10) NOT NULL,

    model_karari VARCHAR(10) NOT NULL,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_model_karari_sinyal
        FOREIGN KEY (sinyal_id)
        REFERENCES islem_sinyalleri (sinyal_id)
        ON DELETE CASCADE,

    CONSTRAINT gecerli_model_karari
        CHECK (
            model_karari IN (
                'AL',
                'NOTR',
                'ALMA'
            )
        ),

    CONSTRAINT gecerli_olasilik
        CHECK (
            basari_olasiligi >= 0
            AND basari_olasiligi <= 1
        ),

    CONSTRAINT gecerli_esikler
        CHECK (
            alma_esigi >= 0
            AND al_esigi <= 1
            AND alma_esigi <= al_esigi
        ),

    CONSTRAINT benzersiz_model_karari
        UNIQUE (
            sinyal_id,
            model_kodu
        )
);


CREATE INDEX IF NOT EXISTS
    idx_model_kararlari_donem
ON model_sinyal_kararlari (
    deney_donemi
);


CREATE INDEX IF NOT EXISTS
    idx_model_kararlari_model
ON model_sinyal_kararlari (
    model_kodu
);


CREATE INDEX IF NOT EXISTS
    idx_model_kararlari_karar
ON model_sinyal_kararlari (
    model_karari
);