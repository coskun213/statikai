# StatikAI — Codex proje kuralları

Bu proje TÜBİTAK 2209-A kapsamında araştırma amaçlı bir prototiptir. İnşaat mühendisliği ve statik hesapların doğruluğu önceliklidir.

## Mevcut durum
- `generate_dataset.py` 40 temel kiriş + 200 sentetik görüntü, etiket ve analitik referans sonuçları üretir.
- `train_pilot.py` yalnızca **önceden gerçek kutularla kesilmiş sembol parçalarını** sınıflandıran 4 sınıflı CNN'i eğitir. Uçtan uca görüntü okuma, OCR, nesne tespiti veya kiriş çözümü YOKTUR.
- `evaluate_equilibrium.py` dışarıdan gelen tepki tahminlerini denetler.
- Pilot veri aynı üreticiden geldiği için gerçek dünyada genellenebilirlik kanıtlanmamıştır.
- Daha fazla ayrıntı için `README.md`, `docs/Codex_Gelistirme_Talimati.md`, `docs/Pilot_Deney_Raporu.md` dosyalarını oku.

## Bilimsel kurallar
- Eğitilmemiş bir modeli eğitilmiş gibi, test edilmemiş bir özelliği tamamlanmış gibi gösterme.
- Gerçek test sonucunu kaydetmeden başarı yüzdesi uydurma.
- `problem_id` gruplarını train/validation/test arasında karıştırma; fiziksel eşdeğer varyasyonlar aynı grupta kalsın.
- `RA`, `RB`, `L`, `P1`, `P2`, `x1`, `x2` arasındaki fiziksel dengeyi doğrula. Yanlış okunan girdiyle tutarlı denge sağlanması, çıktının doğru olduğunu kanıtlamaz.
- Model karşılaştırmalarını aynı sabit test grubu üzerinde yap. Test verisinden hiperparametre veya eşik seçme.
- Her aşamada çalıştırılan komutları, gerçek çıktıları ve sınırlılıkları raporla.
- Önerilen sistem gerçek yapı tasarımı veya güvenlik kararı için kullanılmaz.

## Kod geliştirme
- Önce mevcut testleri çalıştır: `python -m pytest -q`.
- Geliştirme küçük, test edilebilir aşamalardan oluşsun. Her aşama bir sonraki başlamadan doğrulansın.
- Rastgelelik tohumlarını ve Python/PyTorch sürümlerini kaydet.
- Windows/macOS/Linux taşınabilirliğini değerlendir; font yolları Linux'a özgü olabilir.
- Yeni üçüncü taraf paketleri gerçekten gerekiyorsa `requirements.txt` içine gerekçesiyle ekle.
- Modüllere test, README'ye çalıştırma komutları ekle. Model ağırlıklarını ve sonuçları açık isimlendir.

## Yeni sürüm hakkında ek not (8 Kasım 2026)

Yukarıdaki mevcut durum eski pilotu açıklar. Yeni `train_detector.py` ve
`statikai/detector_model.py` tam görüntü sembol kutuları üretir; eski pilotun
kutuları otomatik bulduğu iddia edilmez. Yeni dedektörün ikinci sentetik stilde
önemli mesnet hataları vardır. OCR ve görüntüden RA/RB hâlâ uygulanmadı.
Sabit test protokolü `detector_results/evaluation/frozen_protocol.json`
içindedir; test skoruna bakarak bu protokole yeniden ayar yapma. Yeni deney
çıktılarını ayrı klasöre yaz. Son durumu rapordan oku.

## Ayrı 3B masaüstü hattı (kullanıcının ek isteği)

`statikai_desktop.py` ve `statikai/frame3d.py` elle girilen düzenli 3B çerçeveyi
PyNite ile çözer. Görüntüden yapı analizi veya eski CNN'in yeni kabiliyeti değildir.
Alan yükünün düğümlere eşdeğerlendiğini ve kirişte döşeme yükü eğilmesini
hesaplamadığını koru. Kaynak ve kanıt: `docs/3B_Masaustu_Raporu.md`.


## Ölçülendirilmiş V2 veri hattı

`generate_extended_dataset.py --version dimensions-v2` ayrı klasöre çizim üretir.
Eski `dataset_extended/` ve sabit testleri değiştirme. V2 aynı fiziksel aileleri ve
split atamalarını taşır; bağımsız yeni bir test problemi seti gibi sunma.
`style=D2` eski A/B eğitim protokolünden ayrıdır. `annotations/`, `masks/` ve CSV
çıkarım girdisi değildir. Gerçek kontrol/sınırlar için `VERI_SETI_V2_RAPORU.md` oku.


## Ayrı V3 dedektör deneyi

`train_detector_v3.py`, `statikai/lite_detector.py` ve ilgili veri/ölçüm modülleri
önceden kaydedilmiş `experiments/detector_v3_20261108_01/preregistered_plan.json`
planını izler. Yeni bağımsız fizik aileleri ayrı sentetik çizim kodundan gelir;
dış kaynak gerçek çizim diye sunma. `data_protocol.json` ve frozen_thresholds.json
sabitlerini test skoruna göre değiştirme. Eski model/veri/sonuçları koru.

## Ayrı OCR/ölçü grafı modülü (sonraki geliştirme)

`read_beam_diagram.py` ve `statikai/ocr_*.py`, `diagram_reading.py`,
`symbol_reader.py` gerçek yerel OCR ve ölçü zinciri çıkarımı içerir. Statik
motoru çağırmaz, masaüstü arayüzüne bağlanmadı. V1 yanlış ölçü birimi güvenlik
hatası ve eski sonuçları korunmuştur; V1.1 düzeltmesi eğitim kopyasındaki
örnekten gelir. Yeni 50 fizik ailesiyle ayrı son test ve sürüm gerekçesi
`experiments/ocr_v1_1_20261108_01/` içindedir. V2 renderer kullanılan sentetik
testi dış kaynak mühendislik çizimi diye sunma. `frozen_ocr_protocol.json`
sonrası aynı test skoruna göre OCR, geometri veya eşik ayarlama.
Yeni bulgular ve gerçek test sonuçları `OCR_VE_GEOMETRI_RAPORU.md` içinde.

## Doğrulanmış uçtan uca kiriş hattı

Yeni `beam_pipeline.py`, `beam_scope.py`, `solve_beam_image.py` ve ayrı
`statikai_beam_app.py` görüntüden analitik tepkilere dar kapsamlı bağlantıyı
kurar. Eski physics/OCR/3B kaynakları ve ağırlıkları değişmedi. İncelemeli
okumalar veya kısmi alanlar çözücüye gönderilmez. Denge sağlanması doğru
görüntü yorumu kanıtı değildir. `experiments/end_to_end_v1_20261108_01/`
kilitli planı, 30 yeni fiziksel problem/120 çizim ve gerçek sonuçları içerir;
testten eşik/kod seçme. Güncel kapsam ve kanıt `UCTAN_UCA_RAPORU.md` içindedir.
