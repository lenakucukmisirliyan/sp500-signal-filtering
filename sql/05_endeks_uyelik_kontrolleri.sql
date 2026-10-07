-- S&P 500 tarihsel uyelik verilerinin kalite kontrolleri.


-- 1. Genel uyelik bilgileri
SELECT
    COUNT(*) AS toplam_uyelik_kaydi,
    COUNT(DISTINCT menkul_kiymet_id) AS benzersiz_menkul_kiymet,
    MIN(baslangic_tarihi) AS ilk_baslangic,
    MAX(bitis_tarihi) AS son_bitis,
    COUNT(*) FILTER (
        WHERE bitis_tarihi IS NULL
    ) AS bitis_tarihi_bos
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500';


-- 2. Analiz baslangic tarihindeki uye sayisi
SELECT COUNT(*) AS uye_sayisi
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500'
  AND baslangic_tarihi <= DATE '2023-01-03'
  AND bitis_tarihi > DATE '2023-01-03';


-- 3. Analiz bitis tarihindeki uye sayisi
SELECT COUNT(*) AS uye_sayisi
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500'
  AND baslangic_tarihi <= DATE '2024-03-28'
  AND bitis_tarihi > DATE '2024-03-28';


-- 4. Donem icinde endekse giren ve endeksten cikan sembol sayisi
SELECT
    COUNT(*) FILTER (
        WHERE baslangic_tarihi > DATE '2023-01-03'
    ) AS donem_icinde_giren,

    COUNT(*) FILTER (
        WHERE bitis_tarihi < DATE '2024-03-29'
    ) AS donem_icinde_cikan
FROM endeks_uyelikleri
WHERE endeks_kodu = 'SP500';


-- 5. Donem icinde endekse giren menkul kiymetler
SELECT
    mk.sembol,
    mk.menkul_kiymet_adi,
    eu.baslangic_tarihi
FROM endeks_uyelikleri eu
INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id = eu.menkul_kiymet_id
WHERE eu.endeks_kodu = 'SP500'
  AND eu.baslangic_tarihi > DATE '2023-01-03'
ORDER BY eu.baslangic_tarihi, mk.sembol;


-- 6. Donem icinde endeksten cikan menkul kiymetler
SELECT
    mk.sembol,
    mk.menkul_kiymet_adi,
    eu.bitis_tarihi
FROM endeks_uyelikleri eu
INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id = eu.menkul_kiymet_id
WHERE eu.endeks_kodu = 'SP500'
  AND eu.bitis_tarihi < DATE '2024-03-29'
ORDER BY eu.bitis_tarihi, mk.sembol;


-- 7. SPY, S&P 500 uyesi olmadigi icin sonuc donmemelidir
SELECT
    mk.sembol,
    eu.baslangic_tarihi,
    eu.bitis_tarihi
FROM endeks_uyelikleri eu
INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id = eu.menkul_kiymet_id
WHERE mk.sembol = 'SPY';


-- 8. Ayni sembol icin cakisan uyelik araliklari
-- Sonucun bos olmasi beklenir.
SELECT
    mk.sembol,
    eu1.baslangic_tarihi AS birinci_baslangic,
    eu1.bitis_tarihi AS birinci_bitis,
    eu2.baslangic_tarihi AS ikinci_baslangic,
    eu2.bitis_tarihi AS ikinci_bitis
FROM endeks_uyelikleri eu1
INNER JOIN endeks_uyelikleri eu2
    ON eu1.menkul_kiymet_id = eu2.menkul_kiymet_id
    AND eu1.endeks_kodu = eu2.endeks_kodu
    AND eu1.endeks_uyelik_id < eu2.endeks_uyelik_id
    AND eu1.baslangic_tarihi < eu2.bitis_tarihi
    AND eu2.baslangic_tarihi < eu1.bitis_tarihi
INNER JOIN menkul_kiymetler mk
    ON mk.menkul_kiymet_id = eu1.menkul_kiymet_id
WHERE eu1.endeks_kodu = 'SP500'
ORDER BY mk.sembol;