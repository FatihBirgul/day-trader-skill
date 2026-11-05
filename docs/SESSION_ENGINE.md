# Forex seansları ve broker saatleri

`forex.sessions.active_sessions` Tokyo, Londra ve New York yerel saatlerini IANA saat dilimleriyle hesaplar. Yaz saati geçişleri `zoneinfo` tarafından uygulanır. Bunlar bilgilendirme amaçlıdır; broker işlem izni yerine geçmez.

`broker_status` hafta sonunu `CLOSED`, işlem izni kapalıysa `CLOSED`, broker saat politikası yoksa `UNKNOWN` döndürür. Açık politika `OPEN`, `OPENING_SOON`, `CLOSING_SOON` veya `CLOSED` döndürür. XAUUSD için özel broker ara saatleri ancak açık politika içinde tanımlanır. Tatil takvimi bilinmediğinde kesin açıklık iddia edilmez.

`MT5_BROKER_HOURS` ortam değişkeni JSON nesnesidir: `{"XAUUSD":{"timezone":"Europe/London","weekly":{"0":[["08:00","17:00"]]}}}`. Gün anahtarları Pazartesi 0 ile Pazar 6 arasındadır. Başlangıç dahil, bitiş hariçtir; aynı günü aşan aralıklar ayrı gün pencerelerine bölünmelidir. Bu saatler brokerdan otomatik okunmuş sayılmaz; demo terminalde doğrulanmalıdır. Politika yoksa analiz BUY/SELL planı üretmez.

V4 politika pencereleri gece yarısını aşabilir: Cuma `22:00`-`02:00` Cumartesi 02:00'ye kadar sürer. `date_overrides` içinde `YYYY-MM-DD:null` kapalı gün, pencere listesi özel açık saat anlamına gelir. Broker saatleri yapılandırılmışsa pazar açılışı bu politikaya göre değerlendirilir. İşlem izni kapalıysa durum `DISABLED` olur. Bu ayarlar broker tatil takviminin otomatik keşfi değildir.
