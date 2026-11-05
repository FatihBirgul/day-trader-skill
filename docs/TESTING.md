# Testler

`python3 -m unittest discover -s tests -q` tüm çevrimdışı testleri çalıştırır. İlk durum: 315 geçti. Geliştirme sonrası: 324 geçti, 0 başarısız, 0 atlanan. Forex testleri sinyal, eski tick, kapanmamış mum, lot sınırı, stop önceliği ve sahte MT5 bağlantısını kapsar. Gerçek Windows MT5 demo testi yapılmadı. API, `fastapi` ve `httpx` test bağımlılığı gerektirir; `requirements-api.txt` kurun. Linux CI bu testleri gerçek terminal olmadan çalıştırabilir.

V2 doğrulaması: `python3 -m unittest discover -s tests -q` ile 334 test geçti, 0 başarısız, 0 atlanan. On yeni test tek kapanış, stop/target sırası, açık sonuç, SELL, spread, zaman sırası, broker kâr işareti, lot grid'i, para birimi ve sağlık bağlantısını kapsar. Gerçek MT5 Windows demo testi hâlâ yapılmadı.

V3 seans aşaması: 338 test geçiyor. Dört yeni test Londra DST, Londra/New York kesişimi, hafta sonu, işlem izni ve açık saat politikasını kapsar.

V3 scanner aşaması: 341 test geçti. Scanner kısmi başarısızlık, strateji oyları ve ek API rotaları test edildi.

V3 araştırma aşaması: 346 test geçti. Çoklu işlem, kronolojik giriş, holdout, deterministik bootstrap, istek sınırı ve ters gap kaybı doğrulandı.

V3 bilgi ve risk aşaması: 352 test geçti. RSS ayrıştırma eski News Skill işleviyle, olay filtreleme, uyarı cooldown ve manuel risk politikası test edildi.

V3 gösterge aşaması: 354 test geçti. Wilder RSI referansı, sabit seri, MACD ve yetersiz veri denetlendi.

V3 metadata aşaması: 356 test geçti. Yanlış sembol eşlemesi ve eksik spread politikasıyla plan üretmeme test edildi.

V3 son yerel doğrulama: 357 test geçti, 0 başarısız ve 0 atlanan. Gösterge hesabı yaklaşık 0,029 saniye, 2000 mumluk araştırma backtest'i yaklaşık 0,321 saniye, fixture tarama yaklaşık 0,002 saniye sürdü; bu ölçümler tek Cloud örneğinde yapıldı ve MT5 ağ/terminal gecikmesini kapsamaz. CI artık Python 3.10 ve 3.12 için offline test, bağımlılık kurulumu ve compileall çalıştırır.

V3 MT5 tanılama aşaması: 358 test geçti. Tanılama mock provider ile test edildi; Cloud'da gerçek MT5 paketi olmadığından canlı test yapılmadı.

V3 strateji etiket karşılaştırması sonrası 359 test geçti.

V3 kayan değerlendirme: 361 test geçti. Gelecekte eklenen mumların geçmiş işlem sonuçlarını değiştirmemesi ve ardışık pencere sınırları doğrulandı.

V4 ilk kalite kapısı: 368 test geçti. Fiyat modeli, bid/mid, iki yön, stop-first ve gap; ayrıca broker gece yarısı, pazar ve tarih istisnası test edildi.

V4 bağımsız strateji tekrar oynatma sonrası 368 test geçti. `strategy_comparison` her strateji için kendi işlem listesi ve metriklerini doğrular.

V4 risk sınırı aşaması: 370 test geçti. Negatif manuel kayıt ve spread sonrası broker stop mesafesi regresyonları eklendi.
