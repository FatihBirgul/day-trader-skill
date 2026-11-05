# Frontend teslimi

Backend: Windows MT5 terminali yanında `pip install -r requirements-api.txt MetaTrader5` ve `uvicorn forex.api:app --host 127.0.0.1 --port 8000`. Base URL `http://127.0.0.1:8000/api/v1`. Ayrıntılı rota ve JSON alanları `docs/API_CONTRACT.md` içindedir. Tarayıcı farklı origin kullanırsa CORS ve kimlik doğrulama ayrıca tasarlanmalıdır; API varsayılan olarak yalnızca loopback'te hizmet vermelidir.

Sinyal: `BUY`, `SELL`, `WAIT`; ayrı `data_status` veri sağlığını belirtir. `plan=null` işlem önerisi yok demektir. MT5 erişiminde `DATA_UNAVAILABLE`, eski tick veya mumda `STALE` bekleyin. Fixture provider yalnızca test içindir; canlı ekran için kullanmayın. Haber ve takvim rotaları şu anda veri sağlamaz. Gerçek Windows demo terminal bağlantısı ve broker sembol eşlemeleri henüz doğrulanmadı. PWA herhangi bir emir akışı bağlamamalıdır.

V2 geçişi: Analiz veri yokluğu ve stale durumunda HTTP 503 döner; önceki JSON alanları korunur. `WAIT` yalnızca sağlıklı veriyle kararsız teknik sinyal içindir. Sağlık 200 yanıtı için gerçek MT5 terminal bağlantısı gerekir. Fixture yanıtında `data_status=TEST_ONLY` gösterilir; bu veri canlı fiyat olarak sunulmamalıdır. Backtest sonucu artık tek plan için en fazla bir kapanış içerir. Açık plan `status=OPEN` ve `trades=0` döndürür.

V3: Seans rozetleri için `/sessions/{symbol}`, çoklu tarama için `/scanner`, strateji adları için `/strategies` kullanın. `session.broker.status=UNKNOWN` olduğunda canlı işlem planı sunulmaz. `scanner.errors` her başarısız sembol/zaman çifti için ayrı gösterilmelidir.
