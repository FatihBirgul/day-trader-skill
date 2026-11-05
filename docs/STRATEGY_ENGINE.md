# Forex stratejileri

`forex/strategies.py` üç kapanmış mum kuralı içerir. Trend following, EMA20/50/200 sıralaması ile RSI ve MACD yönünü birleştirir. Breakout, mevcut entry Skill'inin `closed_bar_breakout` hesabını önceki 20 mum aralığına uygular. Pullback, önceki mumun EMA20'ye dokunup son mumun yönünde kapanışla tepki vermesini arar. Bütün adaylar H4 yönüyle karşılaştırılır; çelişki `WAIT` üretir. Sonuçlar olasılık veya yatırım tavsiyesi değildir.

`GET /api/v1/strategies` adları, `GET /api/v1/scanner` çoklu sembol/zaman dilimi sonuçlarını verir. Tek tarama 24 sembol-zaman çifti ile sınırlıdır. Başarısız çiftler `errors` içinde ayrı gösterilir. Broker saatleri bilinmiyorsa plan üretilmez.
