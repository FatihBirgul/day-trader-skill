# Güvenlik denetimi

Forex API içinde emir gönderme veya pozisyon kapatma rotası yoktur. `forex/` kodu MT5 `order_send` çağırmaz. Eski hisse broker Skill'i korunur fakat Forex API tarafından yüklenmez. Varsayılan çalıştırma komutu `127.0.0.1` adresine bağlanır; farklı ağdan erişim için kimlik doğrulama tasarlanmadı ve önerilmez. CORS etkinleştirilmedi. Gerçek şifre veya API anahtarı depoya eklenmedi. İstek başına scanner 24 çift, araştırma backtest'i 2000 mum ve eski replay 10000 mum ile sınırlıdır. Canlı kaynak yapılandırılmadığında haber/takvim veri üretmez.

Açık riskler: API istemci yapılandırması ağdan erişime açılırsa kimlik doğrulama yoktur; MT5 terminal paketinin gerçek Windows davranışı test edilmedi; risk günlüğü manuel ve eksik olabilir; haber/takvim kaynağı entegrasyonu uygulama dışından sağlanır. Dış ağa açmadan önce auth, CORS, rate limit ve proxy mimarisi gerekir.
