-- Analiz tablosundaki sembol bazli satir sayilarini kontrol eder.

SELECT
    mk.sembol,
    COUNT(*) AS toplam_satir,
    COUNT(*) FILTER (
        WHERE afv.dolduruldu_mu = TRUE
    ) AS doldurulan_satir,
    COUNT(*) FILTER (
        WHERE afv.dolduruldu_mu = FALSE
    ) AS gercek_satir

FROM analiz_fiyat_verileri afv

INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
        afv.menkul_kiymet_id

WHERE mk.sembol IN (
    'AAPL',
    'SPY',
    'SNA'
)

GROUP BY mk.sembol

ORDER BY mk.sembol;


-- Doldurulan barlarin fiyat ve hacim kurallarini kontrol eder.
-- Sonucun 0 olmasi gerekir.

SELECT
    COUNT(*) AS hatali_doldurulan_bar

FROM analiz_fiyat_verileri

WHERE dolduruldu_mu = TRUE
  AND (
      acilis <> kapanis
      OR en_yuksek <> kapanis
      OR en_dusuk <> kapanis
      OR hacim_agirlikli_ortalama_fiyat
            <> kapanis
      OR hacim <> 0
      OR islem_sayisi <> 0
  );


-- Ayni sembol ve zamanda tekrar eden kayitlari kontrol eder.
-- Sonucun bos olmasi gerekir.

SELECT
    menkul_kiymet_id,
    bar_zamani,
    zaman_araligi_dakika,
    COUNT(*) AS tekrar_sayisi

FROM analiz_fiyat_verileri

GROUP BY
    menkul_kiymet_id,
    bar_zamani,
    zaman_araligi_dakika

HAVING COUNT(*) > 1;


-- SNA icin doldurulan ilk 10 bari gosterir.

SELECT
    mk.sembol,
    afv.bar_zamani,
    afv.acilis,
    afv.en_yuksek,
    afv.en_dusuk,
    afv.kapanis,
    afv.hacim,
    afv.islem_sayisi,
    afv.dolduruldu_mu

FROM analiz_fiyat_verileri afv

INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
        afv.menkul_kiymet_id

WHERE mk.sembol = 'SNA'
  AND afv.dolduruldu_mu = TRUE

ORDER BY afv.bar_zamani

LIMIT 10;


-- Beklenen ve gercek analiz tablosu buyuklugunu karsilastirir.

WITH beklenen AS (
    SELECT
        COUNT(
            DISTINCT gvk.menkul_kiymet_id
        ) AS beklenen_sembol,

        SUM(
            pt.beklenen_bar_sayisi
        ) AS beklenen_satir

    FROM gunluk_veri_kalitesi gvk

    INNER JOIN piyasa_takvimi pt
        ON pt.islem_tarihi =
            gvk.islem_tarihi

    WHERE gvk.nihai_kalite_durumu IN (
        'TUTULDU',
        'DOLDURULACAK'
    )
),

gercek AS (
    SELECT
        COUNT(
            DISTINCT menkul_kiymet_id
        ) AS gercek_sembol,

        COUNT(*) AS gercek_satir,

        COUNT(*) FILTER (
            WHERE dolduruldu_mu = TRUE
        ) AS doldurulan_satir

    FROM analiz_fiyat_verileri
)

SELECT
    beklenen_sembol,
    gercek_sembol,
    beklenen_satir,
    gercek_satir,
    doldurulan_satir

FROM beklenen
CROSS JOIN gercek;


-- Tekrar eden barlari kontrol eder.
-- Sonuc bos olmali.

SELECT
    menkul_kiymet_id,
    bar_zamani,
    zaman_araligi_dakika,
    COUNT(*) AS tekrar_sayisi

FROM analiz_fiyat_verileri

GROUP BY
    menkul_kiymet_id,
    bar_zamani,
    zaman_araligi_dakika

HAVING COUNT(*) > 1;


-- Doldurulan barlarin kurallara uygunlugunu kontrol eder.
-- Sonuc 0 olmali.

SELECT
    COUNT(*) AS hatali_doldurulan_bar

FROM analiz_fiyat_verileri

WHERE dolduruldu_mu = TRUE
  AND (
      acilis <> kapanis
      OR en_yuksek <> kapanis
      OR en_dusuk <> kapanis
      OR hacim_agirlikli_ortalama_fiyat
            <> kapanis
      OR hacim <> 0
      OR islem_sayisi <> 0
  );


-- Elenen gunlerden analiz tablosuna satir sizmis mi kontrol eder.
-- Sonuc 0 olmali.

SELECT
    COUNT(*) AS elenen_gunlerden_gelen_satir

FROM analiz_fiyat_verileri afv

INNER JOIN gunluk_veri_kalitesi gvk
    ON gvk.menkul_kiymet_id =
        afv.menkul_kiymet_id
    AND gvk.islem_tarihi =
        (
            afv.bar_zamani
            AT TIME ZONE 'America/New_York'
        )::DATE

WHERE gvk.nihai_kalite_durumu =
    'ELENDI';


-- PARA yanlislikla analiz tablosuna alinmis mi kontrol eder.
-- Sonuc 0 olmali.

SELECT
    COUNT(*) AS para_satiri

FROM analiz_fiyat_verileri afv

INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
        afv.menkul_kiymet_id

WHERE mk.sembol = 'PARA';