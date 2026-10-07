-- PARA sembolu analiz doneminde Paramount Global'a aitti.
-- Sembol daha sonra baska bir sirket tarafindan yeniden kullanildigi
-- ve Alpaca verisi yeterli kapsama sahip olmadigi icin analizden cikarilir.

UPDATE gunluk_veri_kalitesi gvk

SET
    nihai_kalite_durumu = 'ELENDI',
    eleme_nedeni = 'SEMBOL_YENIDEN_KULLANIMI'

FROM menkul_kiymetler mk

WHERE mk.menkul_kiymet_id =
        gvk.menkul_kiymet_id
  AND mk.sembol = 'PARA';


-- Sonucu kontrol eder.

SELECT
    mk.sembol,
    gvk.nihai_kalite_durumu,
    gvk.eleme_nedeni,
    COUNT(*) AS gun_sayisi

FROM gunluk_veri_kalitesi gvk

INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id =
        gvk.menkul_kiymet_id

WHERE mk.sembol = 'PARA'

GROUP BY
    mk.sembol,
    gvk.nihai_kalite_durumu,
    gvk.eleme_nedeni;