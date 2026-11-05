-- SPY verisinden hesaplanan piyasa kosullarini tutar.

CREATE TABLE IF NOT EXISTS piyasa_kosullari (
    bar_zamani TIMESTAMPTZ PRIMARY KEY,

    spy_kapanis NUMERIC(18, 6) NOT NULL,

    spy_kisa_ortalama NUMERIC(18, 6),

    spy_uzun_ortalama NUMERIC(18, 6),

    spy_er12 NUMERIC(10, 6),

    olumlu_piyasa_mi BOOLEAN,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP
);