# Forex skill denetimi

Başlangıç: `work` branch, `3d0f4ef`; 315 test geçti. Orijinal hisse akışı korunur. Forex katmanı `forex/core.py` içinden mevcut Python dosyalarını yükler. Aşağıdaki kararlar SKILL.md, işlevler ve testler incelenerek verilmiştir.

| Skill | Karar | Yeniden kullanım ve sınır |
| --- | --- | --- |
| trader-scanner | Kısmen kullanıldı | `rsi` doğrudan Forex göstergesinde. Nasdaq listesi, NYSE seansı, hacim ve ORB kuralları Forex'e taşınmadı. EMA ve seans dışı teknik filtreler eklendi. |
| trader-news | Kısmen kullanıldı | RSS ayrıştırma ve `parse_time` uygun; Forex RSS kaynağı doğrulanmadığı için API haber verisi sunmuyor. SEC/earnings Forex zincirinde yok. |
| trader-entry | Uyarlandı | Mevcut bar mantığına `closed_bar_breakout` eklendi ve Forex analizi çağırıyor. NYSE takvimi kullanılmıyor. |
| trader-exit | Kısmen kullanıldı | `atr_of` doğrudan Forex ATR hesabında kullanıldı; fiyat planlama yapısı incelendi, sent hassasiyeti Forex'e uymadığından Forex stop/TP tick ile hesaplanıyor. |
| trader-timemachine | Uyarlandı | Stop öncelikli mum çakışma kuralı `first_exit` olarak paylaşıldı. Eski simülasyon korunuyor; Forex backtest ayrı, sınırlı ilk sürüm. |
| trader-risk | Kısmen kullanıldı | Eski emir denetimi korundu. Forex'te emir nesnesi farklı olduğundan ayrı salt okunur `risk_check` kullanılıyor. Açık pozisyon sayısı yalnızca çağıranın verdiği bilgiye dayanır. |
| trader-budget | Kısmen kullanıldı | Hisse `size_trade` yaklaşımı incelendi. Lot için broker tick değeri, lot adımı ve MT5 `order_calc_profit` kullanılıyor. Hisse hesabı aynen korunuyor. |
| trader-broker | Korundu, Forex'te kapsam dışı | Emir gönderme yolu Forex API'ye bağlı değil. |
| trader-alerts | Korundu, Forex'te kapsam dışı | Hisse fiyat uyarıları korunur. Forex olay üretimi henüz tamamlanmadı. |
| trader-analyst | Korundu, Forex'te kapsam dışı | SEC şirket finansalları Forex yön tahmini için kullanılmaz. |
| trader-pelosi | Korundu, Forex'te kapsam dışı | Kongre hisse bildirimleri Forex zincirinde kullanılmaz. |

Forex analizi için `forex/` paketi gerekiyor: ortak provider arayüzü, MT5 yaşam döngüsü ve API mevcut hisse dosyalarına yerleştirilirse NYSE ve hisse emir kodlarıyla karışır. Bu paket mevcut analiz işlevlerini yükler; tüm eski algoritmaların Forex'e taşındığı iddia edilmez.

## V2 yeniden kullanım sınırı

Fiilen çalışan ortak işlevler: `trader-scanner/scan.py:rsi`, `trader-entry/entry.py:closed_bar_breakout`, `trader-exit/exit.py:atr_of`, `trader-timemachine/timemachine.py:first_exit`. Hisse `risk.check` ve `budget.size_trade` Forex işlem nesnesinde çalıştırılmıyor; bu iki modül Forex akışına bağlı değildir. Forex risk ve lot kontrolleri broker metadata ve hesap para birimine bağlı olduğu için ayrı tutuldu. Haber ve uyarı işlevleri de henüz Forex akışında çağrılmıyor.

V3 haber katmanı mevcut `trader-news/news.py:parse_rss` ve `dedupe` işlevlerini gerçekten çalıştırır. Uyarı katmanı hisse `alerts.evaluate` işlevini doğrudan kullanmaz; NYSE ve hisse fiyatı varsayımları nedeniyle Forex olay üretimi ayrıdır.

V3 karar güncellemesi: scanner RSI ve mevcut entry breakout tarama/strateji akışında, exit ATR risk mesafesinde, Time Machine stop-first hem tek hem çok işlemli araştırmada kullanılır. News RSS ayrıştırma/deduplication açık kaynaklı ingestion'da çalışır. Broker yürütme, Analyst ve Pelosi salt okunur Forex analiz zincirinin dışında tutulur. Risk/budget hisse nesnelerini Forex'e yapay bağlamak yerine broker sözleşmesine dayanan ayrı hesaplamalar korunur.
