-- Eksik barlarin gun icindeki dagilimini inceler.


-- 1. Eksik bar sayisi dagilimi
SELECT
    eksik_bar_sayisi,
    COUNT(*) AS sembol_gun_sayisi
FROM gunluk_veri_kalitesi
WHERE kalite_durumu = 'DOLDURULABILIR'
GROUP BY eksik_bar_sayisi
ORDER BY eksik_bar_sayisi;


-- 2. Acilis ve kapanis barlarinin eksikligi
WITH sinir_bar_kontrolu AS (
    SELECT
        gvk.menkul_kiymet_id,
        gvk.islem_tarihi,

        acilis_bari.bar_zamani AS bulunan_acilis_bari,

        kapanis_bari.bar_zamani AS bulunan_kapanis_bari

    FROM gunluk_veri_kalitesi gvk

    INNER JOIN piyasa_takvimi pt
        ON pt.islem_tarihi = gvk.islem_tarihi

    LEFT JOIN ham_fiyat_verileri acilis_bari
        ON acilis_bari.menkul_kiymet_id =
            gvk.menkul_kiymet_id
        AND acilis_bari.bar_zamani =
            pt.piyasa_acilis_zamani
        AND acilis_bari.zaman_araligi_dakika = 5

    LEFT JOIN ham_fiyat_verileri kapanis_bari
        ON kapanis_bari.menkul_kiymet_id =
            gvk.menkul_kiymet_id
        AND kapanis_bari.bar_zamani =
            (
                pt.piyasa_kapanis_zamani
                - INTERVAL '5 minutes'
            )
        AND kapanis_bari.zaman_araligi_dakika = 5

    WHERE gvk.kalite_durumu = 'DOLDURULABILIR'
)
SELECT
    COUNT(*) AS doldurulabilir_gun,

    COUNT(*) FILTER (
        WHERE bulunan_acilis_bari IS NULL
    ) AS acilis_bari_eksik,

    COUNT(*) FILTER (
        WHERE bulunan_kapanis_bari IS NULL
    ) AS kapanis_bari_eksik,

    COUNT(*) FILTER (
        WHERE bulunan_acilis_bari IS NULL
          AND bulunan_kapanis_bari IS NULL
    ) AS iki_sinir_bari_da_eksik

FROM sinir_bar_kontrolu;


-- 3. En fazla elenen gunu bulunan semboller
SELECT
    mk.sembol,
    mk.menkul_kiymet_adi,
    COUNT(*) AS elenen_gun_sayisi,
    ROUND(
        AVG(gvk.kapsama_orani) * 100,
        2
    ) AS ortalama_kapsama_yuzdesi
FROM gunluk_veri_kalitesi gvk
INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
        gvk.menkul_kiymet_id
WHERE gvk.kalite_durumu = 'ELENDI'
GROUP BY
    mk.sembol,
    mk.menkul_kiymet_adi
ORDER BY
    elenen_gun_sayisi DESC,
    mk.sembol
LIMIT 30;


-- 4. SPY gunluk kalite kontrolu
SELECT
    gvk.kalite_durumu,
    COUNT(*) AS gun_sayisi,
    SUM(gvk.eksik_bar_sayisi) AS eksik_bar_sayisi
FROM gunluk_veri_kalitesi gvk
INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
        gvk.menkul_kiymet_id
WHERE mk.sembol = 'SPY'
GROUP BY gvk.kalite_durumu
ORDER BY gvk.kalite_durumu;



-- 5. Arka arkaya gelen eksik bar serilerinin uzunlugu

WITH beklenen_barlar AS (
    SELECT
        gvk.menkul_kiymet_id,
        gvk.islem_tarihi,

        generate_series(
            pt.piyasa_acilis_zamani,
            pt.piyasa_kapanis_zamani
                - INTERVAL '5 minutes',
            INTERVAL '5 minutes'
        ) AS beklenen_bar_zamani

    FROM gunluk_veri_kalitesi gvk

    INNER JOIN piyasa_takvimi pt
        ON pt.islem_tarihi =
            gvk.islem_tarihi

    WHERE gvk.kalite_durumu =
        'DOLDURULABILIR'
),

eksik_barlar AS (
    SELECT
        bb.menkul_kiymet_id,
        bb.islem_tarihi,
        bb.beklenen_bar_zamani

    FROM beklenen_barlar bb

    LEFT JOIN ham_fiyat_verileri hfv
        ON hfv.menkul_kiymet_id =
            bb.menkul_kiymet_id
        AND hfv.bar_zamani =
            bb.beklenen_bar_zamani
        AND hfv.zaman_araligi_dakika = 5

    WHERE hfv.bar_zamani IS NULL
),

sirali_eksikler AS (
    SELECT
        menkul_kiymet_id,
        islem_tarihi,
        beklenen_bar_zamani,

        beklenen_bar_zamani
        - (
            ROW_NUMBER() OVER (
                PARTITION BY
                    menkul_kiymet_id,
                    islem_tarihi
                ORDER BY
                    beklenen_bar_zamani
            )
            * INTERVAL '5 minutes'
        ) AS seri_grubu

    FROM eksik_barlar
),

eksik_seriler AS (
    SELECT
        menkul_kiymet_id,
        islem_tarihi,
        seri_grubu,
        COUNT(*) AS seri_uzunlugu

    FROM sirali_eksikler

    GROUP BY
        menkul_kiymet_id,
        islem_tarihi,
        seri_grubu
),

gunluk_en_uzun_seri AS (
    SELECT
        menkul_kiymet_id,
        islem_tarihi,
        MAX(seri_uzunlugu) AS en_uzun_eksik_seri

    FROM eksik_seriler

    GROUP BY
        menkul_kiymet_id,
        islem_tarihi
)

SELECT
    COUNT(*) FILTER (
        WHERE geus.en_uzun_eksik_seri >= 4
    ) AS uzun_kesinti_nedeniyle_elenecek,

    COUNT(*) FILTER (
        WHERE NOT EXISTS (
            SELECT 1
            FROM ham_fiyat_verileri hfv
            WHERE hfv.menkul_kiymet_id =
                    geus.menkul_kiymet_id
              AND hfv.bar_zamani =
                    pt.piyasa_acilis_zamani
              AND hfv.zaman_araligi_dakika = 5
        )
    ) AS acilis_bari_nedeniyle_elenecek,

    COUNT(*) FILTER (
        WHERE geus.en_uzun_eksik_seri >= 4
          AND NOT EXISTS (
              SELECT 1
              FROM ham_fiyat_verileri hfv
              WHERE hfv.menkul_kiymet_id =
                    geus.menkul_kiymet_id
                AND hfv.bar_zamani =
                    pt.piyasa_acilis_zamani
                AND hfv.zaman_araligi_dakika = 5
          )
    ) AS iki_nedene_de_sahip,

    COUNT(*) FILTER (
        WHERE geus.en_uzun_eksik_seri >= 4
           OR NOT EXISTS (
               SELECT 1
               FROM ham_fiyat_verileri hfv
               WHERE hfv.menkul_kiymet_id =
                       geus.menkul_kiymet_id
                 AND hfv.bar_zamani =
                       pt.piyasa_acilis_zamani
                 AND hfv.zaman_araligi_dakika = 5
           )
    ) AS toplam_ilave_elenecek

FROM gunluk_en_uzun_seri geus

INNER JOIN piyasa_takvimi pt
    ON pt.islem_tarihi = geus.islem_tarihi;