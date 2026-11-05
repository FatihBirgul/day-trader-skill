# V4 backtest doğrulaması

Tek plan replay en fazla bir çıkış üretir. Araştırma backtest'i her kapanmış mumdan sonra sonraki mum açılışında yeni pozisyon varsayar; açık pozisyon varken ikinci giriş yoktur. Fiyat modeli `forex.microstructure` içinde tek işlem ve araştırma için ortaktır. Bid bazlı mumda BUY ask giriş/bid çıkış, SELL bid giriş/ask çıkış kullanır. Gap stopu aşarsa açılış fiyatı uygulanır; aynı mumda iki sınır görülürse stop önce sayılır.

Strateji karşılaştırması artık her stratejiyi kendi sinyalleri ve bağımsız pozisyon durumu ile ayrı tekrar oynatır. Kombine motorun işlem listesiyle bağımsız strateji listeleri eşit olmak zorunda değildir. Geliştirme/holdout kronolojik ayrılır. Sabit kural kayan pencereler parametre eğitimi yapmaz. Gelecekteki mumların geçmiş sonuçları değiştirmemesi test edilir. Gerçek tick ve broker fill verisi yoktur; spread sabit varsayımdır.

V4 bootstrap 200 tekrarlı gözlenmiş işlem R örneklemesiyle toplam R yüzde 5/50/95, medyan ve en kötü drawdown, medyan en uzun kayıp serisi döndürür. Sabit seed tekrar üretilebilirlik sağlar. Gelecekteki piyasa dağılımı veya gerçek kazanma olasılığı iddiası yoktur.
