# Finansal fiyat doğrulaması

MT5 tarihsel OHLC için varsayılan temel `bid` kabul edilir. `mid` yalnızca açıkça belirtilirse kullanılır. Bilinmeyen temel reddedilir. BUY giriş ask = bid + spread, çıkış bid; SELL giriş bid, çıkış ask = bid + spread. Stop/target seviyeleri seçilen grafik fiyat temelindedir. Sabit spread gerçek geçmiş spreadi temsil etmez. Gap stopu aşarsa stop fiyatı garanti edilmez; ters yönde açılış fiyatı kullanılır. Aynı mumda stop ve hedef görülürse Time Machine'in stop-first kuralı uygulanır.

R = (gerçekleştiği varsayılan çıkış - uygulanabilir giriş) × yön / uygulanabilir stop mesafesi. `commission` ve `slippage` yapılandırma varsayımıdır. Bağımsız testler BUY/SELL giriş, stop, hedef, gap, bid/mid ve spread etkisini denetler. Gerçek broker fill verisiyle doğrulama yapılmadı.
