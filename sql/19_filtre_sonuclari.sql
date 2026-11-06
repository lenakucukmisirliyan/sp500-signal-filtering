-- Kural tabanli ve makine ogrenmesi filtrelerinin
-- her sinyal icin verdigi kararlari tutar.

CREATE TABLE IF NOT EXISTS filtre_sonuclari (
    sinyal_id BIGINT PRIMARY KEY,

    deney_donemi VARCHAR(30) NOT NULL,

    kural_izin_verdi_mi BOOLEAN NOT NULL,

    ml_basari_olasiligi NUMERIC(12, 10) NOT NULL,

    ml_esigi NUMERIC(12, 10) NOT NULL,

    ml_izin_verdi_mi BOOLEAN NOT NULL,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_filtre_sonuclari_sinyal
        FOREIGN KEY (sinyal_id)
        REFERENCES islem_sinyalleri (sinyal_id)
        ON DELETE CASCADE,

    CONSTRAINT gecerli_deney_donemi
        CHECK (
            deney_donemi IN (
                'DOGRULAMA',
                'IKINCIL_DOGRULAMA',
                'NIHAI_TEST'
            )
        ),

    CONSTRAINT gecerli_ml_olasiligi
        CHECK (
            ml_basari_olasiligi >= 0
            AND ml_basari_olasiligi <= 1
        ),

    CONSTRAINT gecerli_ml_esigi
        CHECK (
            ml_esigi >= 0
            AND ml_esigi <= 1
        )
);