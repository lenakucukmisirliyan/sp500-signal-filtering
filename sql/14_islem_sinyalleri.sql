-- Uretilen alim sinyallerini ve islem sonuclarini tutar.

CREATE TABLE IF NOT EXISTS islem_sinyalleri (
    sinyal_id BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    menkul_kiymet_id INTEGER NOT NULL,

    sinyal_zamani TIMESTAMPTZ NOT NULL,

    giris_zamani TIMESTAMPTZ NOT NULL,

    cikis_zamani TIMESTAMPTZ NOT NULL,

    giris_fiyati NUMERIC(18, 6) NOT NULL,

    cikis_fiyati NUMERIC(18, 6) NOT NULL,

    kisa_ortalama NUMERIC(18, 6) NOT NULL,

    uzun_ortalama NUMERIC(18, 6) NOT NULL,

    brut_getiri NUMERIC(12, 8) NOT NULL,

    islem_maliyeti_orani NUMERIC(12, 8) NOT NULL,

    net_getiri NUMERIC(12, 8) NOT NULL,

    basarili_mi BOOLEAN NOT NULL,

    veri_donemi VARCHAR(20) NOT NULL,

    doldurulmus_veri_var_mi BOOLEAN
        NOT NULL DEFAULT FALSE,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sinyal_menkul_kiymet
        FOREIGN KEY (menkul_kiymet_id)
        REFERENCES menkul_kiymetler (menkul_kiymet_id)
        ON DELETE RESTRICT,

    CONSTRAINT benzersiz_sinyal
        UNIQUE (
            menkul_kiymet_id,
            sinyal_zamani
        ),

    CONSTRAINT gecerli_sinyal_fiyatlari
        CHECK (
            giris_fiyati > 0
            AND cikis_fiyati > 0
        ),

    CONSTRAINT gecerli_veri_donemi
        CHECK (
            veri_donemi IN (
                'EGITIM',
                'DOGRULAMA',
                'TEST'
            )
        )
);