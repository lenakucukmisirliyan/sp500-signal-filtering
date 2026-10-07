-- NYSE islem gunlerini ve seans saatlerini tutar.

CREATE TABLE IF NOT EXISTS piyasa_takvimi (
    islem_tarihi DATE PRIMARY KEY,

    piyasa_acilis_zamani TIMESTAMPTZ NOT NULL,

    piyasa_kapanis_zamani TIMESTAMPTZ NOT NULL,

    beklenen_bar_sayisi SMALLINT NOT NULL,

    erken_kapanis_mi BOOLEAN NOT NULL DEFAULT FALSE,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT gecerli_piyasa_saatleri
        CHECK (
            piyasa_kapanis_zamani
            > piyasa_acilis_zamani
        ),

    CONSTRAINT gecerli_beklenen_bar_sayisi
        CHECK (
            beklenen_bar_sayisi > 0
        )
);