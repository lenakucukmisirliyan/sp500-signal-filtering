-- Sinyal ve makine ogrenmesi analizlerinde kullanilacak
-- temizlenmis 5 dakikalik fiyat verilerini saklar.
--
-- Ham fiyat verileri degistirilmez.
-- Eksik barlar doldurulursa dolduruldu_mu alani TRUE olur.

CREATE TABLE IF NOT EXISTS analiz_fiyat_verileri (
    analiz_fiyat_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    menkul_kiymet_id INTEGER NOT NULL,

    bar_zamani TIMESTAMPTZ NOT NULL,

    zaman_araligi_dakika SMALLINT
        NOT NULL
        DEFAULT 5,

    acilis NUMERIC(18, 6) NOT NULL,

    en_yuksek NUMERIC(18, 6) NOT NULL,

    en_dusuk NUMERIC(18, 6) NOT NULL,

    kapanis NUMERIC(18, 6) NOT NULL,

    hacim BIGINT NOT NULL,

    islem_sayisi INTEGER,

    hacim_agirlikli_ortalama_fiyat
        NUMERIC(18, 6),

    dolduruldu_mu BOOLEAN
        NOT NULL
        DEFAULT FALSE,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_analiz_fiyat_menkul_kiymet
        FOREIGN KEY (menkul_kiymet_id)
        REFERENCES menkul_kiymetler (menkul_kiymet_id)
        ON DELETE RESTRICT,

    CONSTRAINT benzersiz_analiz_fiyat_bari
        UNIQUE (
            menkul_kiymet_id,
            bar_zamani,
            zaman_araligi_dakika
        ),

    CONSTRAINT gecerli_analiz_fiyatlari
        CHECK (
            acilis > 0
            AND en_yuksek > 0
            AND en_dusuk > 0
            AND kapanis > 0
            AND hacim >= 0
            AND (
                islem_sayisi IS NULL
                OR islem_sayisi >= 0
            )
        ),

    CONSTRAINT tutarli_analiz_fiyatlari
        CHECK (
            en_yuksek >= acilis
            AND en_yuksek >= kapanis
            AND en_yuksek >= en_dusuk
            AND en_dusuk <= acilis
            AND en_dusuk <= kapanis
        )
);


-- Sembol ve zaman uzerinden yapilacak sorgulari hizlandirir.

CREATE INDEX IF NOT EXISTS
    idx_analiz_fiyat_sembol_zaman

ON analiz_fiyat_verileri (
    menkul_kiymet_id,
    bar_zamani
);