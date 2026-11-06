# S&P 500 Sinyal Filtreleme Sistemi

Bu proje, S&P 500 hisselerinde teknik analiz ile uretilen alim
sinyallerinin piyasa ve hisse kosullarina gore filtrelenmesini
amaclayan bir karar destek sistemidir.

Calismada filtresiz sinyaller, kural tabanli filtre ve makine
ogrenmesi yontemleri basari, getiri ve risk olculeri acisindan
karsilastirilmaktadir.

## Arastirma Sorusu

Piyasa ve hisse kosullari kullanilarak dusuk kaliteli alim
sinyalleri onceden ayirt edilebilir mi?

Filtreleme islemi:

- Basari oranini artiriyor mu?
- Ortalama net getiriyi iyilestiriyor mu?
- Riskli sinyalleri azaltabiliyor mu?
- Farkli zaman donemlerinde tutarli sonuc veriyor mu?

## Veri Kapsami

- Veri kaynagi: Alpaca SIP
- Piyasa: ABD hisse senetleri
- Endeks: S&P 500
- Zaman araligi: 5 dakika
- Analiz donemi: 3 Ocak 2023 - 28 Mart 2024
- Ham fiyat verisi: Yaklasik 14,4 milyon satir
- Temiz analiz verisi: Yaklasik 12,1 milyon satir
- Uretilen toplam sinyal: 113.545
- Model analizinde kullanilan sinyal: 105.457

Analiz doneminde S&P 500 endeksinde bulunmus tum sirketler
tarihsel endeks uyelikleri dikkate alinarak belirlenmistir.
Bu sayede yalnizca bugun endekste bulunan sirketlerin
kullanilmasindan kaynaklanabilecek yanlilik azaltmistir.

## Kullanilan Teknolojiler

- Python 3.12
- PostgreSQL 18
- pgAdmin 4
- psycopg2
- Pandas
- NumPy
- scikit-learn
- Alpaca API
- pandas-market-calendars
- Git ve GitHub

## Veri Akisi

1. Tarihsel S&P 500 sembolleri belirlenir.
2. Menkul kiymet ve endeks uyelik bilgileri PostgreSQL'e aktarilir.
3. Alpaca SIP kaynagindan 5 dakikalik fiyat verileri indirilir.
4. NYSE islem takvimi ve erken kapanis gunleri olusturulur.
5. Ham fiyat verilerine kalite kontrolleri uygulanir.
6. Eksigi fazla olan gunler elenir.
7. Sinirli eksigi bulunan gunlerde eksik barlar doldurulur.
8. Temiz analiz fiyat tablosu olusturulur.
9. SMA20-SMA50 kesisiminden temel alim sinyalleri uretilir.
10. Piyasa ve hisse ozellikleri hesaplanir.
11. Kural tabanli ve makine ogrenmesi filtreleri uygulanir.
12. Sonuclar performans, risk ve istatistiksel anlamlilik acisindan karsilastirilir.

## Veri Kalitesi

Kalite kontrolunde:

- Tekrarli kayitlar
- Bos degerler
- Gecersiz fiyatlar
- Hatali 5 dakikalik zaman hizalari
- Normal piyasa seansi disindaki veriler
- Eksik barlar
- Erken kapanis gunleri
- Gunluk veri kapsama oranlari

incelenmistir.

Gunler veri durumuna gore:

- TUTULDU
- DOLDURULACAK
- ELENDI

olarak siniflandirilmistir.

Doldurulan barlardan etkilenen sinyaller makine ogrenmesi
verisinden cikarilmistir.

## Temel Alim Sinyali

Temel stratejide:

- SMA20, SMA50'yi yukari kestiginde alim sinyali olusur.
- Isleme sonraki 5 dakikalik barin acilis fiyatindan girilir.
- Islem 12 bar, yaklasik 60 dakika sonra kapatilir.
- Giris ve cikis ayni islem gununde gerceklesir.
- Ayni hissede cakisabilecek islemlere izin verilmez.
- Toplam yuzde 0,10 islem maliyeti uygulanir.
- Net getirisi pozitif olan sinyal basarili kabul edilir.

## Kural Tabanli Filtre

SPY'nin ayni islem gunundeki son 60 dakikalik getirisi
yuzde -0,10 degerinin altindaysa alim sinyali engellenir.

Bu kural, piyasanin kisa surede belirgin bicimde geriledigi
durumlarda yeni alim islemlerini azaltmayi amaclar.

## Makine Ogrenmesi Modelleri

Asagidaki siniflandirma yontemleri karsilastirilmistir:

- Logistic Regression
- Decision Tree
- Random Forest
- K-Nearest Neighbors
- Gaussian Naive Bayes
- Yapay sinir agi

Modeller iki zaman sirali dogrulama doneminde
karsilastirilmistir. Random Forest iki dogrulama donemi
birlikte degerlendirildiginde en tutarli basari artisini
sagladigi icin nihai testte degerlendirilecek makine
ogrenmesi modeli olarak secilmistir.

## Deney Donemleri

Veriler zaman sirasi korunarak dort bolume ayrilmistir:

- EGITIM
- DOGRULAMA
- IKINCIL_DOGRULAMA
- NIHAI_TEST

Random Forest genisleyen egitim pencereli walk-forward
yontemiyle degerlendirilmistir.

Her adimda yalnizca degerlendirme doneminden onceki veriler
egitimde kullanilmistir. Filtre esikleri de yalnizca gecmis
egitim verilerinden hesaplanmistir.

## Nihai Test Sonuclari

Mart 2024 nihai test doneminde:

| Yontem        | Engelleme Orani | Basari Orani | Ortalama Net Getiri |
| ------------- | --------------: | -----------: | ------------------: |
| Filtresiz     |           %0,00 |       %39,25 |            -%0,0870 |
| Kural tabanli |           %9,44 |       %39,36 |            -%0,0860 |
| Random Forest |          %12,30 |       %39,44 |            -%0,0913 |

Her iki filtre de nihai testte basari oranini sinirli
miktarda artirmistir.

Kural tabanli filtre ortalama net getiriyi cok az
iyilestirirken Random Forest ortalama net getiriyi
kotulestirmistir. Nihai testteki farklar istatistiksel
olarak anlamli bulunmamistir.

## Temel Bulgular

- Random Forest iki dogrulama doneminde basari oranini
  tutarli bicimde artirmistir.
- Yapay sinir agi Random Forest'a yakin sonuclar vermistir.
- KNN ve tek karar agaci belirgin fayda saglamamistir.
- Modelin nihai testteki ayirt etme gucu sinirlidir.
- Basari oranindaki artis her zaman ortalama getiri ve
  risk iyilesmesine donusmemistir.
- Yalnizca basari oranina bakmak finansal performansi
  degerlendirmek icin yeterli degildir.

## Proje Yapisi

```text
sql/              PostgreSQL sorgulari
src/              Python kaynak kodlari
veriler/          Tarihsel S&P 500 uyelik dosyalari
.env.example      Gerekli ortam degiskenlerinin ornegi
requirements.txt  Python kutuphaneleri
README.md         Projenin genel aciklamasi
```
