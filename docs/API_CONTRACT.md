# API sözleşmesi V1

Base URL: `http://127.0.0.1:8000/api/v1`. OpenAPI: `/openapi.json`. Tüm zaman damgaları UTC ISO 8601 veya Unix saniyesidir. `provider` alanı `mt5` ya da açıkça test amaçlı `fixture-test-only` olabilir. `data_status`: `OK`, `STALE`, `DATA_UNAVAILABLE`, `ERROR`. Gerçek veri yokluğu `WAIT` sinyaline dönüştürülmez.

| Rota | Parametre / gövde | Yanıt |
| --- | --- | --- |
| GET `/health` | Yok | `status`, `provider`, `timestamp` |
| GET `/symbols` | Yok | `symbols`, `provider`, `data_status` |
| GET `/symbols/{symbol}/metadata` | destekli sembol | `data` (contract, tick, point, volume, stops), `provider`, `data_status` |
| GET `/quotes/{symbol}` | sembol | `data` (bid, ask, time), `provider`, `data_status` |
| GET `/candles/{symbol}` | `timeframe=M15`, `count=220` (1..10000) | `data` (UTC open time, OHLC, tick_volume), `provider`, `data_status` |
| GET `/analysis/{symbol}` | `timeframe=M15` | `signal`, `plan`, `indicators`, `reasons`, `data_status`, `provider`, `timestamp` |
| GET `/signals/{symbol}` | analysis ile aynı | analysis ile aynı |
| POST `/risk/calculate` | `symbol`, `direction`, `balance`, `risk_pct`, `entry`, `stop_loss`, `account_currency` | `lots`, `estimated_risk`, `risk_cap`, `currency` |
| GET `/news` | Yok | `items=[]`, `data_status=DATA_UNAVAILABLE` |
| GET `/calendar` | Yok | `events=[]`, `data_status=DATA_UNAVAILABLE` |
| POST `/backtests` | `symbol`, `timeframe`, `direction`, `entry`, `stop_loss`, `take_profit`, `spread`, `count` (2..10000) | `result` (`trades`, `outcomes_r`, `max_drawdown_r`, `policy`), `provider`, `data_status` |

Örnek: `GET /api/v1/analysis/XAUUSD?timeframe=M15` için veri yoksa `{"symbol":"XAUUSD","signal":"WAIT","plan":null,"data_status":"DATA_UNAVAILABLE","reasons":["quote or metadata unavailable"],"provider":"mt5",...}`. Veri varsa BUY/SELL planında `entry`, `stop_loss`, `take_profit_1`, `take_profit_2`, `risk_reward`, `timestamp` bulunur. Plan oluşmuyorsa `WAIT` döner. `POST /risk/calculate` örnek gövde: `{"symbol":"XAUUSD","direction":"BUY","balance":10000,"risk_pct":1,"entry":2000,"stop_loss":1999,"account_currency":"USD"}`.

HTTP 422 geçersiz girdi veya broker veri hatası; 404 provider'da bulunmayan sembol; 503 MT5 paketi/terminal erişilemez. FastAPI Pydantic hataları standart `detail` dizisi kullanır. Veri hataları `detail.status` ve `detail.reason` döndürür. Bu sözleşme ilk sürümdür; PWA, `data_status=OK` dışında fiyatı canlı göstermemelidir.

## V1 sözleşme düzeltmesi (backend 0.2)

`/api/v1/analysis/{symbol}` ve `/signals/{symbol}` veri durumu `STALE` veya `DATA_UNAVAILABLE` ise önceki 200 yerine HTTP 503 döndürür. JSON gövdesindeki `signal`, `plan`, `data_status`, `provider`, `reasons` korunur. Bu geçişte PWA hem HTTP kodunu hem `data_status` alanını okumalıdır. `/health` MT5 terminalinin `connected` durumunu sorgular; bağlantı yoksa 503, fixture ile çalışıyorsa 200 ve `data_status=TEST_ONLY` döner. Sembol ve zaman dilimi hataları 422 döner. Risk ve backtest için OpenAPI yanıt modelleri eklendi.

Tek işlem tekrar oynatma yanıtında `result.status` değeri `STOP`, `TARGET` veya `OPEN`; `result.trades` kapandıysa 1, açıksa 0'dır. `result.result_r` kapanışta net R, açıkken son mumdaki gerçekleşmemiş R'dir. `outcomes_r` yalnızca kapanmış sonuç içerir. `entry_assumption=filled_at_first_bar_close` giriş dolumunu varsayar; veri bunu ispatlamaz. `policy=stop_first` aynı mum çakışmasını belirtir.

## V3 ek rotalar

`GET /api/v1/sessions/{symbol}` UTC zaman damgası, bilgilendirici global seanslar ve broker durumunu döndürür. `GET /api/v1/strategies` aktif üç strateji adını listeler. `GET /api/v1/scanner?symbols=XAUUSD,EURUSD&timeframes=M15,H1` en fazla 24 çiftin sıralı `results` ve ayrı `errors` listesini döndürür. Geçersiz sembol, zaman dilimi veya sınır aşımı 422'dir. Sinyal yanıtında geriye uyumlu alanlara ek olarak `strategies` ve `session` bulunabilir.

`POST /api/v1/strategy-backtests`: `symbol`, `timeframe` (varsayılan M15), `count` (220..2000), `spread`, `commission`, `slippage`, `holdout` (0..0.5), `seed` alır. Yanıt `result.trades`, `open_position`, `metrics`, `development`, `holdout`, `holdout_start_time`, `monte_carlo`, `policy`, `entry_assumption`, `provider`, `data_status` içerir. 422 veri veya limit hatasıdır. Bu araştırma çıktısı canlı emir veya doğrulanmış strateji başarısı değildir.

V3 yeni rotalar: `POST /api/v1/risk/policy` plan ve manuel günlük kayıtlarla `decision`, `reasons`, `fingerprint`, `sizing`, `records_source` döndürür. `GET /api/v1/alerts/{symbol}` backend uyarı olaylarını listeler. `/news` ve `/calendar` yalnızca uygulamaya açıkça veri sağlayıcı eklendiğinde `OK` döner; varsayılan `DATA_UNAVAILABLE` korunur. Takvim `symbol` filtresi alır. Harici haber/takvim kaynağı varsayılan olarak yapılandırılmamıştır.

V3 MT5 yapılandırması: `/symbols/{symbol}/metadata` artık `asset_type`, `source`, `digits`, `freeze_level`, `max_spread`, `broker_hours` gibi alanları döndürebilir. `max_spread` ve broker saat politikası eksikse `/analysis` plan üretmez. `/quotes` `spread`, `provider`, `freshness` alanlarını içerir. Bu alanlar brokerdan doğrulanan veriyle doldurulur; fixture sonuçları canlı gösterilmemelidir.
