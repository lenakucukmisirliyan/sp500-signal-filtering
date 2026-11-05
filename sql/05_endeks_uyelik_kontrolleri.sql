-- 1. Genel uyelik bilgileri
SELECT
    COUNT(*) AS toplam_uyelik_kaydi,
    COUNT(DISTINCT menkul_kiymet_id) AS benzersiz_menkul_kiymet,
    MIN(baslangic_tarihi) AS ilk_baslangic,
    MAX(bitis_tarihi) AS son_bitis
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500';


-- 2. Analiz doneminin basinda ve sonunda uye sayisi
SELECT
    COUNT(*) FILTER (
        WHERE baslangic_tarihi <= DATE '2023-01-03'
          AND bitis_tarihi > DATE '2023-01-03'
    ) AS baslangictaki_uye_sayisi,

    COUNT(*) FILTER (
        WHERE baslangic_tarihi <= DATE '2024-03-28'
          AND bitis_tarihi > DATE '2024-03-28'
    ) AS bitisteki_uye_sayisi
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500';


-- 3. Donem icinde endekse giren ve endeksten cikan sayisi
SELECT
    COUNT(*) FILTER (
        WHERE baslangic_tarihi > DATE '2023-01-03'
    ) AS donem_icinde_giren,

    COUNT(*) FILTER (
        WHERE bitis_tarihi < DATE '2024-03-29'
    ) AS donem_icinde_cikan
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500';


-- Ayni menkul kiymete ait cakisan uyelik donemlerini kontrol eder.
-- Sonucun bos olmasi beklenir.

SELECT
    mk.sembol,
    eu1.baslangic_tarihi AS birinci_baslangic,
    eu1.bitis_tarihi AS birinci_bitis,
    eu2.baslangic_tarihi AS ikinci_baslangic,
    eu2.bitis_tarihi AS ikinci_bitis
FROM
    endeks_uyelikleri eu1,
    endeks_uyelikleri eu2,
    menkul_kiymetler mk
WHERE eu1.menkul_kiymet_id = eu2.menkul_kiymet_id
  AND mk.menkul_kiymet_id = eu1.menkul_kiymet_id
  AND eu1.endeks_uyelik_id < eu2.endeks_uyelik_id
  AND eu1.baslangic_tarihi < eu2.bitis_tarihi
  AND eu2.baslangic_tarihi < eu1.bitis_tarihi
  AND eu1.endeks_kodu = 'SP500';