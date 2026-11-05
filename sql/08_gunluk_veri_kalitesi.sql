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

-- 1. S&P 500 uyelerinin beklenen islem gunlerini ekler.

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
    eu.menkul_kiymet_id,
    pt.islem_tarihi,
    pt.beklenen_bar_sayisi,
    0,
    pt.beklenen_bar_sayisi,
    0,
    'ELENDI'
FROM
    endeks_uyelikleri eu,
    piyasa_takvimi pt
WHERE pt.islem_tarihi >= eu.baslangic_tarihi
  AND pt.islem_tarihi < eu.bitis_tarihi
  AND eu.endeks_kodu = 'SP500';


-- 2. SPY icin butun islem gunlerini ekler.

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
    mk.menkul_kiymet_id,
    pt.islem_tarihi,
    pt.beklenen_bar_sayisi,
    0,
    pt.beklenen_bar_sayisi,
    0,
    'ELENDI'
FROM
    menkul_kiymetler mk,
    piyasa_takvimi pt
WHERE mk.sembol = 'SPY';


-- 3. Her menkul kiymet ve gun icin bulunan barlari sayar.

UPDATE gunluk_veri_kalitesi gvk
SET bulunan_bar_sayisi = sayim.bulunan_bar_sayisi
FROM (
    SELECT
        hfv.menkul_kiymet_id,
        pt.islem_tarihi,
        COUNT(*)::SMALLINT AS bulunan_bar_sayisi
    FROM
        ham_fiyat_verileri hfv,
        piyasa_takvimi pt
    WHERE hfv.bar_zamani >= pt.piyasa_acilis_zamani
      AND hfv.bar_zamani < pt.piyasa_kapanis_zamani
      AND hfv.zaman_araligi_dakika = 5
    GROUP BY
        hfv.menkul_kiymet_id,
        pt.islem_tarihi
) sayim
WHERE gvk.menkul_kiymet_id = sayim.menkul_kiymet_id
  AND gvk.islem_tarihi = sayim.islem_tarihi;


-- 4. Eksik bar sayisini ve kapsama oranini hesaplar.

UPDATE gunluk_veri_kalitesi
SET
    eksik_bar_sayisi =
        beklenen_bar_sayisi - bulunan_bar_sayisi,

    kapsama_orani =
        bulunan_bar_sayisi::NUMERIC
        / beklenen_bar_sayisi;


-- 5. Gunluk kalite durumunu belirler.

UPDATE gunluk_veri_kalitesi
SET kalite_durumu =
    CASE
        WHEN bulunan_bar_sayisi = beklenen_bar_sayisi
            THEN 'TAM'

        WHEN kapsama_orani >= 0.80
            THEN 'DOLDURULABILIR'

        ELSE 'ELENDI'
    END;