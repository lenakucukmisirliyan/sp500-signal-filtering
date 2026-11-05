CREATE TABLE IF NOT EXISTS menkul_kiymetler (
    menkul_kiymet_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sembol VARCHAR(15) NOT NULL UNIQUE,
    menkul_kiymet_adi VARCHAR(200),
    varlik_turu VARCHAR(20) NOT NULL,
    borsa VARCHAR(20),
    sektor VARCHAR(100),
    alt_sektor VARCHAR(150),
    para_birimi CHAR(3) NOT NULL DEFAULT 'USD',
    aktif_mi BOOLEAN NOT NULL DEFAULT TRUE,
    olusturulma_zamani TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT gecerli_varlik_turu
        CHECK (varlik_turu IN ('HISSE', 'ETF'))
);


CREATE TABLE IF NOT EXISTS endeks_uyelikleri (
    endeks_uyelik_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    menkul_kiymet_id INTEGER NOT NULL,
    endeks_kodu VARCHAR(20) NOT NULL DEFAULT 'SP500',
    baslangic_tarihi DATE NOT NULL,
    bitis_tarihi DATE,
    olusturulma_zamani TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_endeks_uyelikleri_menkul_kiymet
        FOREIGN KEY (menkul_kiymet_id)
        REFERENCES menkul_kiymetler (menkul_kiymet_id)
        ON DELETE RESTRICT,

    CONSTRAINT gecerli_uyelik_tarihleri
        CHECK (
            bitis_tarihi IS NULL
            OR bitis_tarihi > baslangic_tarihi
        ),

    CONSTRAINT benzersiz_endeks_uyeligi
        UNIQUE (menkul_kiymet_id, endeks_kodu, baslangic_tarihi)
);


CREATE TABLE IF NOT EXISTS ham_fiyat_verileri (
    menkul_kiymet_id INTEGER NOT NULL,
    bar_zamani TIMESTAMPTZ NOT NULL,
    zaman_araligi_dakika SMALLINT NOT NULL DEFAULT 5,

    acilis NUMERIC(18, 6) NOT NULL,
    en_yuksek NUMERIC(18, 6) NOT NULL,
    en_dusuk NUMERIC(18, 6) NOT NULL,
    kapanis NUMERIC(18, 6) NOT NULL,

    hacim BIGINT NOT NULL,
    islem_sayisi INTEGER,
    hacim_agirlikli_ortalama_fiyat NUMERIC(18, 6),

    veri_kaynagi VARCHAR(30) NOT NULL DEFAULT 'ALPACA_SIP',
    fiyat_duzeltmesi VARCHAR(20) NOT NULL DEFAULT 'ALL',
    aktarim_zamani TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_ham_fiyat_verileri
        PRIMARY KEY (
            menkul_kiymet_id,
            bar_zamani,
            zaman_araligi_dakika
        ),

    CONSTRAINT fk_ham_fiyat_menkul_kiymet
        FOREIGN KEY (menkul_kiymet_id)
        REFERENCES menkul_kiymetler (menkul_kiymet_id)
        ON DELETE RESTRICT,

    CONSTRAINT gecerli_zaman_araligi
        CHECK (zaman_araligi_dakika > 0),

    CONSTRAINT gecerli_fiyat_degerleri
        CHECK (
            acilis > 0
            AND en_yuksek > 0
            AND en_dusuk > 0
            AND kapanis > 0
            AND en_yuksek >= GREATEST(acilis, kapanis, en_dusuk)
            AND en_dusuk <= LEAST(acilis, kapanis, en_yuksek)
        ),

    CONSTRAINT gecerli_hacim
        CHECK (hacim >= 0),

    CONSTRAINT gecerli_islem_sayisi
        CHECK (islem_sayisi IS NULL OR islem_sayisi >= 0)
);