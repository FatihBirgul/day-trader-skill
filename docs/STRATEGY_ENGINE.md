# Forex stratejileri

`forex/strategies.py` üç kapanmış mum kuralı içerir. Trend following, EMA20/50/200 sıralaması ile RSI ve MACD yönünü birleştirir. Breakout, mevcut entry Skill'inin `closed_bar_breakout` hesabını önceki 20 mum aralığına uygular. Pullback, önceki mumun EMA20'ye dokunup son mumun yönünde kapanışla tepki vermesini arar. Bütün adaylar H4 yönüyle karşılaştırılır; çelişki `WAIT` üretir. Sonuçlar olasılık veya yatırım tavsiyesi değildir.

`GET /api/v1/strategies` adları, `GET /api/v1/scanner` çoklu sembol/zaman dilimi sonuçlarını verir. Tek tarama 24 sembol-zaman çifti ile sınırlıdır. Başarısız çiftler `errors` içinde ayrı gösterilir. Broker saatleri bilinmiyorsa plan üretilmez.

V4 piyasa yapısı `forex/structure.py` içinde iki sol ve iki sağ kapanmış mumla swing onaylar. `detected_at` tepe/dip mumu, `confirmed_at` sağdaki son mumdur. Son onaylı swingler destek/direnç ve kapanışla yapısal kırılım hesaplar; ters trend kırılımı açıkça change-of-character olarak etiketlenir. Bunlar analize açıklama olarak eklenir, tek başına emir planı oluşturmaz.

V4 pullback kuralı, önceki mumun EMA temasını yalnızca o mum kapanışında bilinen EMA20 ile kontrol eder; son mum EMA'sı geriye uygulanmaz.
