-- Her sinyal aninda, yalnizca gecmis fiyat ve hacim
-- verilerinden hesaplanan hisse ozelliklerini tutar.

CREATE TABLE IF NOT EXISTS sinyal_ozellikleri (
    sinyal_id BIGINT PRIMARY KEY,

    hisse_15dk_getiri NUMERIC(12, 8),

    hisse_60dk_getiri NUMERIC(12, 8),

    hisse_60dk_volatilite NUMERIC(12, 8),

    hacim_orani_20 NUMERIC(12, 8),

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sinyal_ozellikleri_sinyal
        FOREIGN KEY (sinyal_id)
        REFERENCES islem_sinyalleri (sinyal_id)
        ON DELETE CASCADE,

    CONSTRAINT gecerli_hisse_volatilitesi
        CHECK (
            hisse_60dk_volatilite IS NULL
            OR hisse_60dk_volatilite >= 0
        ),

    CONSTRAINT gecerli_hacim_orani
        CHECK (
            hacim_orani_20 IS NULL
            OR hacim_orani_20 >= 0
        )
);