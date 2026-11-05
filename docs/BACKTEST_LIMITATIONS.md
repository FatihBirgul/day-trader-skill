# Backtest sınırları

Forex `backtest` kapanmış mumları işler ve aynı mumda stop ile hedefe değildiğinde stopu önce sayar. Spread maliyeti R sonucundan düşülür. Sonuçlar gerçekleşmiş işlem veya kazanma olasılığı değildir. İlk sürüm sadece verilen tek girişin sonraki mumlarını tarar; çoklu strateji örneklemesi, out-of-sample, slippage, gap, swap, komisyon, look-ahead ve survivorship denetimi tamamlanmadı. Gerçek tick sırası bulunmaz. Bu nedenle yatırım kararı için yeterli doğrulama değildir.

V2 tek plan tekrar oynatma: giriş ilk mum kapanışında gerçekleşmiş varsayılır; ilk mumun fiyatı ile istenen girişin gerçekten eşleştiği doğrulanamaz. Sonraki mumlarda ilk stop veya hedef sonucu alınır ve işlem kapatılır. Açık kalan işlem `OPEN` ve gerçekleşmemiş R ile döner. `max_drawdown_r` tek kapanmış işlem için sıfır veya zarar büyüklüğüdür; çok işlemli strateji drawdown'ı değildir. Girişleri tarihsel olarak üreten çok işlemli strateji backtest'i henüz yoktur. Spread R'den düşülür; ek broker komisyonu, swap ve slippage modellenmez.

V3 araştırma backtest'i `forex/research.py` içinde çoklu bağımsız işlem üretir. Sinyal yalnızca önceki kapanmış mumlarla hesaplanır; giriş sonraki mumun açılış fiyatında spread ve yapılandırılmış slippage ile varsayılır. Aynı mumda stop/target çakışırsa stop seçilir. Stop yönünde gap varsa çıkış açılış fiyatına kaydırılır. Bir seferde tek pozisyon açıktır. Geliştirme ve son yüzde 25 holdout dönemleri kronolojik ayrılır; parametre arama veya gerçek walk-forward yoktur. Bootstrap sonucu yalnızca gözlenmiş R örneklerinin tekrar örneklenmesidir, kazanma olasılığı değildir. Son bar açık pozisyon `open_position` ile raporlanır.

V3 strateji karşılaştırması, bir işlemin sinyalinde bulunan strateji etiketlerine göre metrikleri gruplar. Aynı işlem birden fazla etikette sayılabilir; sonuçlar bağımsız strateji portföyleri değildir. Parametrelerin kayan pencerelerde yeniden seçildiği gerçek walk-forward hâlâ uygulanmadı.

V3 sabit kural kayan değerlendirmesi `walk_forward` ile 2..5 ardışık pencere üretir. Her pencerenin eğitim bitişi test başlangıcından öncedir ve veri o pencerenin sonuna kadar kesilir. Parametre seçimi veya yeniden eğitim yapılmaz; bu tam strateji optimizasyonu walk-forward değildir. Gelecek mumlar geçmiş işlem sonuçlarını değiştirmemelidir; test bunu doğrular.

V4 fiyat modeli: OHLC ve grafik seviyeleri aynı `price_basis` (`bid` veya `mid`) taşır. Varsayılan `bid` MT5 geçmiş mumları içindir. Sabit spread kullanılır; tarihsel dinamik spread henüz yok. BUY/SELL uygulanabilir giriş ve çıkış fiyatları ortak `microstructure` hesabından gelir. Gerçek tick sırası, fill, likidite ve kısmi gerçekleşme doğrulanmadı.

V4 düzeltmesi: `strategy_comparison` artık yalnızca kombine işlemleri etiketlere ayırmaz; her stratejinin sinyalini ve pozisyon durumunu bağımsız tekrar oynatır. Önceki V3 etiket karşılaştırması açıklaması tarihsel davranıştır, güncel API sonucu değildir.
