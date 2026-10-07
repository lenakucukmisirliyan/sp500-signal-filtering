-- Her menkul kiymetin her islem gunundeki
-- veri kapsamini ve kalite durumunu tutar.


CREATE TABLE IF NOT EXISTS gunluk_veri_kalitesi (
    gunluk_kalite_id BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    menkul_kiymet_id INTEGER NOT NULL,

    islem_tarihi DATE NOT NULL,

    beklenen_bar_sayisi SMALLINT NOT NULL,

    bulunan_bar_sayisi SMALLINT NOT NULL,

    eksik_bar_sayisi SMALLINT NOT NULL,

    kapsama_orani NUMERIC(7, 4) NOT NULL,

    kalite_durumu VARCHAR(30) NOT NULL,

    olusturulma_zamani TIMESTAMPTZ
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_gunluk_kalite_menkul_kiymet
        FOREIGN KEY (menkul_kiymet_id)
        REFERENCES menkul_kiymetler (menkul_kiymet_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_gunluk_kalite_piyasa_takvimi
        FOREIGN KEY (islem_tarihi)
        REFERENCES piyasa_takvimi (islem_tarihi)
        ON DELETE RESTRICT,

    CONSTRAINT benzersiz_gunluk_kalite
        UNIQUE (
            menkul_kiymet_id,
            islem_tarihi
        ),

    CONSTRAINT gecerli_bar_sayilari
        CHECK (
            beklenen_bar_sayisi > 0
            AND bulunan_bar_sayisi >= 0
            AND eksik_bar_sayisi >= 0
            AND bulunan_bar_sayisi
                <= beklenen_bar_sayisi
        ),

    CONSTRAINT gecerli_kapsama_orani
        CHECK (
            kapsama_orani >= 0
            AND kapsama_orani <= 1
        ),

    CONSTRAINT gecerli_kalite_durumu
        CHECK (
            kalite_durumu IN (
                'TAM',
                'DOLDURULABILIR',
                'ELENDI'
            )
        )
);


-- Dosya yeniden calistirilirsa onceki kalite
-- sonuclari silinerek yeniden hesaplanir.
TRUNCATE TABLE gunluk_veri_kalitesi
RESTART IDENTITY;


WITH beklenen_sembol_gunleri AS (
    -- Tarihsel S&P 500 uyeleri
    SELECT
        eu.menkul_kiymet_id,
        pt.islem_tarihi,
        pt.beklenen_bar_sayisi
    FROM endeks_uyelikleri eu
    INNER JOIN piyasa_takvimi pt
        ON pt.islem_tarihi >= eu.baslangic_tarihi
        AND pt.islem_tarihi < eu.bitis_tarihi
    WHERE eu.endeks_kodu = 'SP500'

    UNION ALL

    -- SPY, S&P 500 uyesi degildir.
    -- Piyasa kosullarini gostermek icin her gun eklenir.
    SELECT
        mk.menkul_kiymet_id,
        pt.islem_tarihi,
        pt.beklenen_bar_sayisi
    FROM menkul_kiymetler mk
    CROSS JOIN piyasa_takvimi pt
    WHERE mk.sembol = 'SPY'
),

bulunan_barlar AS (
    -- Yalnizca resmi NYSE seansindaki barlar sayilir.
    SELECT
        hfv.menkul_kiymet_id,
        pt.islem_tarihi,
        COUNT(*)::SMALLINT AS bulunan_bar_sayisi
    FROM ham_fiyat_verileri hfv
    INNER JOIN piyasa_takvimi pt
        ON hfv.bar_zamani
            >= pt.piyasa_acilis_zamani
        AND hfv.bar_zamani
            < pt.piyasa_kapanis_zamani
    WHERE hfv.zaman_araligi_dakika = 5
    GROUP BY
        hfv.menkul_kiymet_id,
        pt.islem_tarihi
),

kalite_hesabi AS (
    SELECT
        bsg.menkul_kiymet_id,
        bsg.islem_tarihi,
        bsg.beklenen_bar_sayisi,

        COALESCE(
            bb.bulunan_bar_sayisi,
            0
        )::SMALLINT AS bulunan_bar_sayisi,

        (
            bsg.beklenen_bar_sayisi
            - COALESCE(bb.bulunan_bar_sayisi, 0)
        )::SMALLINT AS eksik_bar_sayisi,

        (
            COALESCE(bb.bulunan_bar_sayisi, 0)::NUMERIC
            / bsg.beklenen_bar_sayisi
        )::NUMERIC(7, 4) AS kapsama_orani

    FROM beklenen_sembol_gunleri bsg

    LEFT JOIN bulunan_barlar bb
        ON bb.menkul_kiymet_id =
            bsg.menkul_kiymet_id
        AND bb.islem_tarihi =
            bsg.islem_tarihi
)

INSERT INTO gunluk_veri_kalitesi (
    menkul_kiymet_id,
    islem_tarihi,
    beklenen_bar_sayisi,
    bulunan_bar_sayisi,
    eksik_bar_sayisi,
    kapsama_orani,
    kalite_durumu
)
SELECT
    menkul_kiymet_id,
    islem_tarihi,
    beklenen_bar_sayisi,
    bulunan_bar_sayisi,
    eksik_bar_sayisi,
    kapsama_orani,

    CASE
        WHEN bulunan_bar_sayisi =
             beklenen_bar_sayisi
            THEN 'TAM'

        WHEN kapsama_orani >= 0.80
            THEN 'DOLDURULABILIR'

        ELSE 'ELENDI'
    END AS kalite_durumu

FROM kalite_hesabi;