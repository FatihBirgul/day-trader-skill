# Veri sağlayıcıları

`MT5Provider` yalnızca salt okunur `initialize`, `shutdown`, `terminal_info`, `account_info`, `symbol_info`, `symbol_info_tick`, `copy_rates_from_pos`, `symbol_select` ve `order_calc_profit` kullanır. `FixtureProvider` test içindir. MT5 çağrıları kilitle serileştirilir; kopuk terminalde yeniden bağlanma denenir. Gerçek Windows demo terminali Cloud'da doğrulanmadı.

`MT5_SYMBOL_MAP` kanonik sembolü brokerın tam adına eşler. Adın içinde XAUUSD/EURUSD/GBPUSD/USDJPY bulunmalı; broker base/profit currency alanları varsa bunlar da uyuşmalıdır. `MT5_BROKER_HOURS` açık işlem saati politikasıdır. `MT5_MAX_SPREAD` örneği: `{"XAUUSD":0.5,"EURUSD":0.0002}`. Bu değerler broker doğrulaması olmadan varsayılmaz. Üçü de JSON ortam değişkenidir; şifre içermez. Eksik saat veya spread politikasıyla yeni işlem planı üretilmez. Bunlar brokerın gerçekten emir kabul edeceğinin garantisi değildir.

`forex.mt5_diagnostic` gerçek Windows demo terminalinde bağlantı ve veri kontrolü için salt okunur tanılama komutudur. Terminal erişimi yoksa açık `DATA_UNAVAILABLE` raporlar.
