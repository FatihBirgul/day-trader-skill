# Testler

`python3 -m unittest discover -s tests -q` tüm çevrimdışı testleri çalıştırır. İlk durum: 315 geçti. Geliştirme sonrası: 321 geçti, 0 başarısız, 0 atlanan. Forex testleri sinyal, eski tick, kapanmamış mum, lot sınırı, stop önceliği ve sahte MT5 bağlantısını kapsar. Gerçek Windows MT5 demo testi yapılmadı. API, `fastapi` ve `httpx` test bağımlılığı gerektirir; `requirements-api.txt` kurun. Linux CI bu testleri gerçek terminal olmadan çalıştırabilir.
