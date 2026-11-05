# V4 mühendislik denetimi

Başlangıç: `06b9ac2`, 361 test başarılı. Çalışma branch'i `codex/forex-xauusd-backend-v1` ve PR #1 başlığı doğrulandı.

| Önem | Modül | Problem ve tekrar üretim | Etki | Düzeltme ve doğrulama |
| --- | --- | --- | --- | --- |
| Kritik | `forex/research.py`, `forex/core.py` | OHLC bid/mid temeli yoktu. Sabit spread BUY ve SELL çıkışına simetrik ve doğru uygulanmıyordu. | R ve SL/TP sonucu yanlış yorumlanabilir. | Ortak `forex/microstructure.py` fiyat modeli, bid/mid seçimi, executable entry/exit ve stop-first; bağımsız BUY/SELL/gap testleri. |
| Yüksek | `forex/sessions.py` | Gece yarısını aşan broker penceresi reddediliyor, pazar erken açılışı sabit UTC kapanışıyla engelleniyordu. | Açık piyasada yanlış CLOSED veya yanlış plan. | Açık broker politikası, önceki gün penceresi, tarih istisnası ve DISABLED durumu; seans testleri. |
| Yüksek | `forex/research.py` | Strateji etiket karşılaştırması bağımsız strateji performansı gibi okunabilir. | Araştırma sonucu yanıltıcı olabilir. | Belgede etiketlerin örtüştüğü açıklandı; bağımsız strateji deneyleri hâlâ açık. |
| Orta | `forex/api.py` | API girdi fiyat temeli belirsizdi. | Frontend yanlış spread hesabı yapabilir. | `price_basis` alanı eklendi; eski isteklerin varsayılanı `bid` olarak belgelendi. |

Açık denetim konuları: gerçek MT5 Windows terminal testi, broker bazlı tick value doğrulaması, bağımsız strateji backtest'i, tam parametre ayarlamalı walk-forward, canlı haber/takvim kaynağı ve genel ağa açık API güvenliği.
