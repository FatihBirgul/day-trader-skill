# V4 mühendislik denetimi

Başlangıç: `06b9ac2`, 361 test başarılı. Çalışma branch'i `codex/forex-xauusd-backend-v1` ve PR #1 başlığı doğrulandı.

| Önem | Modül | Problem ve tekrar üretim | Etki | Düzeltme ve doğrulama |
| --- | --- | --- | --- | --- |
| Kritik | `forex/research.py`, `forex/core.py` | OHLC bid/mid temeli yoktu. Sabit spread BUY ve SELL çıkışına simetrik ve doğru uygulanmıyordu. | R ve SL/TP sonucu yanlış yorumlanabilir. | Ortak `forex/microstructure.py` fiyat modeli, bid/mid seçimi, executable entry/exit ve stop-first; bağımsız BUY/SELL/gap testleri. |
| Yüksek | `forex/sessions.py` | Gece yarısını aşan broker penceresi reddediliyor, pazar erken açılışı sabit UTC kapanışıyla engelleniyordu. | Açık piyasada yanlış CLOSED veya yanlış plan. | Açık broker politikası, önceki gün penceresi, tarih istisnası ve DISABLED durumu; seans testleri. |
| Yüksek | `forex/research.py` | Strateji etiket karşılaştırması bağımsız strateji performansı gibi okunabilir. | Araştırma sonucu yanıltıcı olabilir. | Belgede etiketlerin örtüştüğü açıklandı; bağımsız strateji deneyleri hâlâ açık. |
| Orta | `forex/api.py` | API girdi fiyat temeli belirsizdi. | Frontend yanlış spread hesabı yapabilir. | `price_basis` alanı eklendi; eski isteklerin varsayılanı `bid` olarak belgelendi. |

Açık denetim konuları: gerçek MT5 Windows terminal testi, broker bazlı tick value doğrulaması, bağımsız strateji backtest'i, tam parametre ayarlamalı walk-forward, canlı haber/takvim kaynağı ve genel ağa açık API güvenliği.
| Yüksek | `forex/core.py:risk_check` | Broker minimum stop seviyesi entry-stop farkıyla karşılaştırılıyordu; spread, çıkış tarafındaki mesafeyi azaltır. | Brokerın reddedeceği stop geçerli sanılabilir. | Stop mesafesinden spread düşülür; BUY/SELL sınır testleri. |
| Yüksek | `forex/policy.py` | Negatif manuel planlanan risk kaydı günlük toplamı azaltabiliyordu. | Günlük risk sınırı aşılabilir. | Negatif ve sonlu olmayan kayıtlar reddedildi; regresyon testi. |
| Yüksek | `forex/providers.py` | MT5 kütüphanesi istisnası Python hatası olarak API'ye yayılabilirdi; fixture nesneleri değiştirilebilir referans döndürüyordu. | 500 ve test durumları arasında veri sızıntısı. | MT5 çağrıları DataError'a normalize edildi, fixture dönüşleri kopyalandı, eşzamanlı quote çağrıları serileştirildi; regresyon testleri. |
| Yüksek | `forex/core.py:analyze` | Üst zaman dilimi son mumu birincil kapanıştan sonra olabilir; API yanıt modeli strateji/seans alanlarını düşürüyordu. | Gelecek bilgi ve eksik frontend kanıtı. | As-of kesimi ve yanıt modelinde confirmations/strategies/session; regresyon testleri. |
| Orta | `forex/core.py` | Basit 20 mum tepe/dip göstergeleri gerçek swing onayını ve tespit/onay zamanını taşımıyordu. | Geçmiş analizde erken seviye varsayımı. | Sağdaki mumlarla onaylanan pivot modülü, yapı kırılımı ve anti-lookahead testleri eklendi. |
| Orta | `forex/strategies.py` | Pullback önceki mumun EMA temasını son mumun EMA20'siyle kıyaslıyordu. | Önceki olaya sonraki mum değeri sızabilir. | Önceki kapanışlara ait EMA20 kullanıldı; regresyon testi. |
| Orta | `forex/core.py:backtest` | İstenen giriş, ilk mum kapanışıyla ilgisiz olabiliyordu. | Tek işlem dolum varsayımı tutarsızlaşır. | İlk kapanışla giriş referansı uyuşmuyorsa reddedilir; test. |
