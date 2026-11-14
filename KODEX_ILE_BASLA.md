# StatikAI geliştirmeye başlama

1. AGENTS.md, README.md, GELISTIRME_PLANI.md ve docs/Denetim_ve_Prototip_Raporu.md dosyalarını oku.
2. Ayrı sanal ortam kur; `python -m pip check` ve `python -m pytest -q` çalıştır.
3. Sağlanan sonuçları koru. Yeni üretim/eğitim/değerlendirme için ayrı çıktı klasörü kullan.
4. `detect_image.py` tam görüntüden sembol kutuları üretir; OCR ve otomatik statik çözüm yapmaz.
5. Ayrı OCR/ilişkilendirme modülü `read_beam_diagram.py` içindedir. Önce
   `docs/OCR_ve_Geometrik_Eslestirme.md` ve `OCR_VE_GEOMETRI_RAPORU.md` oku.
   Yeni doğrulanmış çözüm entegrasyonu `statikai/beam_pipeline.py`, komut
   `solve_beam_image.py`, ayrı 2B pencere `statikai_beam_app.py` içindedir.
   `UCTAN_UCA_RAPORU.md` ve `docs/Uctan_Uca_Kiris_Kullanimi.md` oku. Analitik
   motor değiştirilmedi; aynı test sonuçlarına göre eşik/kod ayarlama.
6. B stili sabit testtir; bu testteki hataları görüp aynı test için eşik ayarlama.

Windows/macOS/Linux açıklamaları: docs/Platform_Uyumlulugu.md.
Gerçek eğitim ve test kayıtları: audit_results/logs/.
