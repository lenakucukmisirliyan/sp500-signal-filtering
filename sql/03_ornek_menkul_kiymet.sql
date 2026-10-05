INSERT INTO menkul_kiymetler (
    sembol,
    menkul_kiymet_adi,
    varlik_turu,
    borsa,
    para_birimi,
    aktif_mi
)
VALUES (
    'AAPL',
    'Apple Inc.',
    'HISSE',
    'NASDAQ',
    'USD',
    TRUE
)
ON CONFLICT (sembol) DO NOTHING;


SELECT *
FROM menkul_kiymetler
WHERE sembol = 'AAPL';