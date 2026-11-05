# Forex risk modeli

`forex.core.size_lots` brokerın minimum/maximum/step grid'i, tick değeri, hesap para birimi ve MT5 `order_calc_profit` ile zarar doğrulaması yapar. Pozitif stop kârını reddeder. `forex.policy.assess` işlem başına risk, günlük planlanan risk, gerçekleşen günlük kayıp, işlem ve açık pozisyon sayısı, spread, minimum R ve yinelenen planı denetler. Kayıtlar API çağıranın manuel sağladığı verilerdir; sistem gerçek broker pozisyonlarını otomatik izlemez. Eksik kayıtla günlük risk değerlendirmesi eksik olabilir.

V4: Broker minimum stop mesafesi giriş ve stop arasındaki farktan spread çıkarıldıktan sonra değerlendirilir. Manuel günlük kayıtlarda negatif tutarlar geçersizdir. Gerçek emir kabulü MT5 demo terminalinde yine doğrulanmalıdır.
