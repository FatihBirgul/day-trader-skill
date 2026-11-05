# Forex mimarisi

`forex.providers.MT5Provider` yerel Windows MT5 terminalinden salt okunur quote, broker metadata ve kapanmış OHLC getirir. `FixtureProvider` yalnızca test içindir. `forex.core.analyze` eski scanner RSI, entry bar kırılımı ve Time Machine stop önceliği kuralını kullanır. M15 gibi alt zaman dilimini H4 ile karşılaştırır. Veri yok veya eskiyse sinyal üretmez. BUY/SELL için tick fiyatına yuvarlanmış giriş, stop, iki hedef ve broker metadata ile hesaplanan lot döndürür. Otomatik emir işlevi ve API rotası yoktur.

H4 ve seçilen zaman diliminde 200 kapanmış mum gerekir. Fiyat için 120 saniye eskime sınırı, mum için iki zaman dilimi sınırı vardır. MT5 tick volume gerçek işlem hacmi kabul edilmez. London, New York, Asya seans kuralları ve broker işlem saatleri henüz sinyale dahil değildir; kapalı piyasa eski tick olarak reddedilir. Bu yüzden 24/5 seans doğrulaması tamamlanmış değildir.

İlk sürümde cache yok; her istek provider'a gider. Bu, eski veriyi canlı gösterme riskini azaltır fakat MT5 çağrı yükünü artırır. Provider kilidi MT5 erişimini serileştirir. Yüksek hacimli kullanım için sonraki aşamada zaman damgalı, kısa ömürlü cache gerekir.

## V2 veri güvenliği

MT5 alias eşlemesi yalnızca `MT5_SYMBOL_MAP` içinde açıkça belirtilmiş broker adıyla yapılır. Terminal bağlantısı sağlık isteğinde sınanır; kopuk bağlantıda tekrar başlatma denenir. Metadata, quote ve kapanmış OHLC denetlenir. Sinyal planı, işlem izni kapalıysa veya H4 mumları eskiyse üretilmez. Brokerın tatil ve özel işlem saatleri için ayrıca takvim API'si yoktur; taze tick ve işlem izni gerekli ama tek başına tam seans doğrulaması değildir.
