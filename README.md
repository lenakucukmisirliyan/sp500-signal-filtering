# S&P 500 Sinyal Filtreleme ve Karar Destek Sistemi

Bu proje, S&P 500 hisselerinde teknik analizle üretilen alım sinyallerini piyasa ve hisse koşullarına göre sınıflandıran bir karar destek sistemidir.

Amaç doğrudan hisse fiyatını tahmin etmek değil, oluşmuş bir alım sinyalinin göreli kalitesini değerlendirerek sinyali **AL**, **NÖTR** veya **ALMA** kategorilerinden birine ayırmaktır. Filtresiz sinyaller, kural tabanlı filtre, makine öğrenmesi modelleri ve performans ağırlıklı ensemble yöntemi karşılaştırılmıştır.

## Araştırma Sorusu

Piyasa ve hisse koşulları kullanılarak düşük kaliteli alım sinyalleri önceden ayırt edilebilir mi?

- Filtreleme başarı oranını artırıyor mu?
- Düşük kaliteli sinyaller ayırt edilebiliyor mu?
- Ortalama net getiri iyileşiyor mu?
- Farklı dönemlerde tutarlı sonuç elde ediliyor mu?
- Model kararları istatistiksel olarak anlamlı mı?

## Veri Kapsamı

- Veri kaynağı: Alpaca SIP
- Piyasa ve endeks: ABD hisse senetleri, S&P 500
- Zaman aralığı: 5 dakika
- Analiz dönemi: 3 Ocak 2023 – 28 Mart 2024
- Menkul kıymet sayısı: 528
- Ham fiyat kaydı: 14.373.792
- Temiz analiz kaydı: 12.060.768
- Üretilen toplam sinyal: 113.545
- Model analizinde kullanılan güvenilir sinyal: 105.457
- Doğrulama ve nihai testlerde değerlendirilen sinyal: 48.868

Analiz döneminde S&P 500 endeksinde bulunmuş şirketler tarihsel endeks üyelikleri dikkate alınarak belirlenmiştir. Böylece yalnızca günümüzde endekste bulunan şirketleri kullanmaktan kaynaklanabilecek hayatta kalma yanlılığı azaltılmıştır.

## Kullanılan Teknolojiler

- Python
- PostgreSQL ve pgAdmin
- Pandas ve NumPy
- scikit-learn ve SciPy
- Streamlit
- Alpaca API ve pandas-market-calendars
- Git ve GitHub

## Projenin Aşamaları

### 1. Veri Toplama

Analiz dönemindeki tarihsel S&P 500 şirketleri belirlenmiş, Alpaca SIP kaynağından beş dakikalık fiyat verileri indirilerek PostgreSQL'e kaydedilmiştir.

### 2. Veri Kalitesi ve Temizleme

Ham veride tekrarlı kayıt, boş değer, geçersiz fiyat, hatalı zaman hizası, seans dışı kayıt, eksik bar ve erken kapanış kontrolleri yapılmıştır. NYSE işlem takvimi kullanılarak her işlem gününde bulunması gereken bar sayısı hesaplanmıştır.

Günler veri kalitesine göre **TUTULDU**, **DOLDURULACAK** veya **ELENDİ** olarak sınıflandırılmıştır. Sınırlı sayıdaki eksik bar önceki kapanış fiyatıyla doldurulmuş ve ayrıca işaretlenmiştir. Bu barlardan etkilenen sinyaller makine öğrenmesi analizinden çıkarılmıştır.

### 3. Temel Alım Sinyali

- SMA20, son 20 adet beş dakikalık kapanışın ortalamasıdır.
- SMA50, son 50 adet beş dakikalık kapanışın ortalamasıdır.
- SMA20, SMA50'yi aşağıdan yukarı geçtiğinde alım sinyali oluşur.
- İşleme sinyalden sonraki barın açılış fiyatından girilir.
- İşlem 12 bar, yaklaşık 60 dakika sonra kapatılır.
- Giriş ve çıkış aynı işlem gününde gerçekleşir.
- Aynı hissede çakışan işlemlere izin verilmez.
- Toplam yüzde 0,10 işlem maliyeti uygulanır.
- Net getirisi pozitif olan sinyal başarılı kabul edilir.

### 4. Sinyal Filtreleme

#### Kural Tabanlı Filtre

SPY'nin aynı işlem günündeki son 60 dakikalık getirisi yüzde -0,10'un altındaysa alım sinyali engellenmiştir. Başka bir ifadeyle genel piyasa son bir saatte yüzde 0,10'dan fazla gerilemişse yeni alım işlemine izin verilmemiştir.

#### Makine Öğrenmesi Modelleri

- Logistic Regression
- Decision Tree
- Random Forest
- K-Nearest Neighbors
- Gaussian Naive Bayes
- Yapay sinir ağı

Modeller accuracy, precision, recall, F1, F1-Macro, ROC-AUC, confusion matrix, engelleme oranı, başarı oranı ve ortalama net getiri açısından değerlendirilmiştir.

#### AL – NÖTR – ALMA Kararları

Karar eşikleri yalnızca geçmiş eğitim verilerindeki tahmin dağılımından hesaplanmıştır:

- En düşük yüzde 20: **ALMA**
- Orta yüzde 60: **NÖTR**
- En yüksek yüzde 20: **AL**

AL, modelin görece güçlü; NÖTR, belirsiz; ALMA ise görece zayıf bulduğu sinyali gösterir. AL kararı kesin kazanç veya yüzde 50'den yüksek başarı garantisi değildir.

#### Ağırlıklı Ensemble

Altı modelin kararları performans ağırlıklı ensemble yöntemiyle birleştirilmiştir. Ağırlık puanı `maksimum(ROC-AUC - 0,50, 0)` formülüyle hesaplanmış ve bütün ağırlıkların toplamı 1 olacak şekilde normalize edilmiştir.

- Ağırlıklı AL oyları yüzde 50'yi aşarsa karar AL olur.
- Ağırlıklı ALMA oyları yüzde 50'yi aşarsa karar ALMA olur.
- Hiçbiri yüzde 50'yi aşmazsa karar NÖTR olur.

İlk doğrulamada geçmiş sonuç bulunmadığından modeller eşit ağırlıkla kullanılmıştır. Sonraki dönemlerde yalnızca geçmiş doğrulama sonuçları kullanılmış; nihai test verileri ağırlık belirlemeye katılmamıştır.

### 5. Performans ve İstatistiksel Analiz

Filtresiz sinyaller, kural tabanlı filtre, Random Forest ve ağırlıklı ensemble; engelleme oranı, başarı oranı, getiri, risk ve istatistiksel anlamlılık açısından karşılaştırılmıştır.

## Deney Dönemleri

- Eğitim: 3 Ocak 2023 – 31 Ağustos 2023
- Birinci doğrulama: 1 Eylül 2023 – 29 Aralık 2023
- İkinci doğrulama: 2 Ocak 2024 – 29 Şubat 2024
- Nihai test: 1 Mart 2024 – 28 Mart 2024

Genişleyen eğitim pencereli walk-forward yöntemi kullanılmıştır. Her adımda yalnızca değerlendirme döneminden önceki veriler eğitimde kullanılarak geleceğe ait bilginin modele sızması engellenmiştir.

## Nihai Test Sonuçları

| Yöntem             | Engelleme Oranı | Başarı Oranı | Ortalama Net Getiri |
| ------------------ | --------------: | -----------: | ------------------: |
| Filtresiz          |           %0,00 |       %39,25 |            -%0,0870 |
| Kural tabanlı      |           %9,44 |       %39,36 |            -%0,0860 |
| Random Forest      |          %22,68 |       %39,95 |            -%0,0920 |
| Ağırlıklı ensemble |          %17,16 |   **%40,12** |            -%0,0878 |

Ağırlıklı ensemble filtresize göre başarı oranını 0,87 puan artırmış, Random Forest'tan daha yüksek başarıya daha düşük engelleme oranıyla ulaşmıştır. Ancak ortalama net getiri pozitif olmamıştır.

## Ensemble İstatistiksel Anlamlılık Sonuçları

Nihai test döneminde:

- Kullanılan sinyallerin başarı oranı: %40,12
- Engellenen sinyallerin başarı oranı: %35,07
- Başarı farkı: +5,05 puan
- Başarı oranı p-değeri: 0,000853
- AL–NÖTR–ALMA ilişki p-değeri: 0,006912
- Getiri karşılaştırması p-değeri: 0,763590

Ensemble'ın izin verdiği sinyallerin başarı oranı, engellediği sinyallerden istatistiksel olarak anlamlı biçimde yüksektir. Üçlü karar ile gerçekleşen başarı arasında da anlamlı ilişki bulunmuştur. Buna karşın ortalama net getiride anlamlı iyileşme elde edilmemiştir.

## Temel Bulgular

- Ensemble üç dönemde de düşük başarı oranına sahip sinyalleri ayırmıştır.
- Nihai testte AL, NÖTR ve ALMA başarıları sırasıyla %40,54, %40,00 ve %35,07 olmuştur.
- Random Forest doğrulama dönemlerinde güçlü sonuç vermiştir.
- Logistic Regression ve Naive Bayes nihai testte üçlü karar sıralamasını korumuştur.
- KNN belirgin bir ayırt etme gücü göstermemiştir.
- Başarı artışı ortalama getiri iyileşmesi anlamına gelmemiştir.
- İşlem maliyeti sonrasında temel stratejinin ortalama getirisi negatif kalmıştır.

## Geçmiş Sinyal İncelemesi

Streamlit arayüzünde sembol, tarih ve sinyal saati seçilebilmektedir. Seçilen sinyal için kural tabanlı karar, altı modelin kararları ve olasılıkları, ensemble oyları, nihai karar, giriş ve çıkış fiyatı, net getiri ve gerçekleşen sonuç gösterilmektedir.

## Streamlit Arayüzü

1. Genel Bakış
2. Yöntem Karşılaştırması
3. Model Performansları
4. Ensemble Analizi
5. Geçmiş Sinyal İncelemesi

## Projenin Çalıştırılması

Sanal ortamı oluşturma:

    python -m venv .venv

Sanal ortamı etkinleştirme:

    .venv\Scripts\Activate.ps1

Kütüphaneleri kurma:

    python -m pip install -r requirements.txt

`.env.example` örnek alınarak `.env` dosyası oluşturulmalı ve PostgreSQL bağlantı bilgileri girilmelidir.

Bağlantıyı kontrol etme:

    python -m src.veritabani

Arayüzü başlatma:

    python -m streamlit run app.py

## Proje Yapısı

    app.py              Streamlit analiz ve karar destek arayüzü
    src/                Python kaynak kodları
    sql/                PostgreSQL sorguları ve görünümleri
    requirements.txt    Python kütüphaneleri
    .env.example        Örnek PostgreSQL bağlantı ayarları
    README.md           Projenin açıklaması ve sonuçları

## Sonuç

Ağırlıklı ensemble, başarı ihtimali düşük sinyalleri istatistiksel olarak anlamlı biçimde ayırmıştır. Ancak sınıflandırma başarısı ortalama net getiride anlamlı bir iyileşmeye dönüşmemiştir.

Bu nedenle proje, doğrudan kârlı işlem üreten veya yatırım tavsiyesi veren bir sistem olarak değil, teknik analiz sinyallerinin göreli kalitesini değerlendiren bir karar destek sistemi olarak yorumlanmalıdır.

## Uyarı

Bu proje akademik amaçla hazırlanmıştır. AL, NÖTR ve ALMA kararları yatırım tavsiyesi değildir.
