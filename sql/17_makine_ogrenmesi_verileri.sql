-- Eski gorunumu kaldirir.
-- Gorunum veri saklamadigi icin tablolar silinmez.

DROP VIEW IF EXISTS makine_ogrenmesi_verileri;


-- Makine ogrenmesi icin sinyal, piyasa ve hisse
-- ozelliklerini tek bir gorunumde bir araya getirir.

CREATE VIEW makine_ogrenmesi_verileri AS

SELECT
    s.sinyal_id,

    s.menkul_kiymet_id,

    mk.sembol,

    s.sinyal_zamani,

    s.veri_donemi,

    -- Piyasa ozellikleri
    pk.spy_sma20_farki_orani,

    pk.spy_60dk_getiri,

    pk.spy_60dk_volatilite,

    pk.spy_er12,

    (
        pk.spy_kisa_ortalama
        - pk.spy_uzun_ortalama
    ) / pk.spy_uzun_ortalama
        AS spy_ortalama_farki_orani,

    -- Hisse ozellikleri
    so.hisse_15dk_getiri,

    so.hisse_60dk_getiri,

    so.hisse_60dk_volatilite,

    so.hacim_orani_20,

    (
        s.kisa_ortalama
        - s.uzun_ortalama
    ) / s.uzun_ortalama
        AS hisse_ortalama_farki_orani,

    -- Hissenin SPY'ye gore son 60 dakikalik
    -- goreceli hareketini gosterir.
    (
        so.hisse_60dk_getiri
        - pk.spy_60dk_getiri
    ) AS goreceli_60dk_getiri,

    -- Sinyalin New York saatine gore
    -- gun icindeki dakikasi
    (
        EXTRACT(
            HOUR FROM
            s.sinyal_zamani
            AT TIME ZONE 'America/New_York'
        ) * 60

        + EXTRACT(
            MINUTE FROM
            s.sinyal_zamani
            AT TIME ZONE 'America/New_York'
        )
    ) AS gunun_dakikasi,

    -- Modelin tahmin etmeye calisacagi hedef
    s.basarili_mi,

    -- Model girdisi olarak kullanilmayacak,
    -- performans degerlendirmesinde kullanilacak
    s.brut_getiri,

    s.net_getiri

FROM
    islem_sinyalleri s,
    piyasa_kosullari pk,
    menkul_kiymetler mk,
    sinyal_ozellikleri so

WHERE s.sinyal_zamani = pk.bar_zamani
  AND s.menkul_kiymet_id = mk.menkul_kiymet_id
  AND s.sinyal_id = so.sinyal_id
  AND s.doldurulmus_veri_var_mi = FALSE;