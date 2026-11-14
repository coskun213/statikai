# StatikAI — SON DURUM DENETİMİ

Tarih: 08.11.2026 19:44 (Türkiye, UTC+03:00).
İncelenen güncel proje: `C:\Users\HP\Documents\Codex\2026-11-08\t\outputs\StatikAI`.
Ham denetim kanıtları: `audit_results/son_durum_20261108_01/`.

## 1. Sonuç

**41 otomatik test BAŞARILI. Ancak 2B görüntüden otomatik statik çözüm henüz mevcut değil.**
Tam görüntü sembol tespiti, önceden kesilmiş sembol sınıflandırması, analitik kiriş
hesabı ve elle tanımlanan 3B masaüstü analizi ayrı işlevlerdir.

**Kritik yeni bulgu:** eski pilotun 140/140 test kırpımı ve 280/280 validasyon
kırpımı, eğitimdeki kırpımlarla piksel düzeyinde aynı. Tam diyagram ve fiziksel
problem ayrımı temiz olsa da sınıflandırıcının gerçek girdilerinde ayrımlar arası
tam tekrar var. Pilotun %100 başarısı yeni sembol görüntülerine genelleme kanıtı değildir.

Yeni tam görüntü dedektörünün gerçek 256x160 girişlerinde train/val/test arasında
tam tekrar bulunmadı. Sabit test yeniden üretildi; B stilinde hareketli mesnet
recall yalnızca %2 (1/50), tüm dört nesneyi eksiksiz bulan görüntü oranı %2 (1/50).

**Bu aşamada yeni özellik, eğitim veya kod düzeltmesi yapılmadı.** README, kaynak
kod, testler, iki model ağırlığı ve eski deneyler korunmuştur. Başlangıçta kaydedilen
5,558 kalıcı dosyanın SHA-256 denetiminde değişen/silinen dosya yok.
Geçici `work/`, önbellek ve sanal ortam bu dosya karşılaştırmasının dışındadır.
3B denemeleri eski sonuçları yazmamak için kaynakların birebir yalıtılmış kopyasında yapıldı.

## 2. Kapsam ve klasör yapısı

README.md, AGENTS.md, KODEX_ILE_BASLA.md, GELISTIRME_PLANI.md ve altı docs belgesi
okundu. `statikai/` içindeki altı modül, iki giriş noktası, veri üretimi/eğitim/
değerlendirme araçları ve testler incelendi. 27 Python kaynağı AST ile ayrıştırıldı.
Eski deneylere ait 83 JSON/CSV/log dosyası okundu/ayrıştırıldı; sayımlar ve
kayıtlı sonuçlar kendi aralarında karşılaştırıldı. İki `.pt` dosyası
`weights_only=True`, CPU ile yüklenip gerçek ağlara uyumları kontrol edildi.

| Dizin | Başlangıç kalıcı dosya sayısı |
|---|---:|
| `(root)` | 29 |
| `audit_results` | 72 |
| `dataset` | 402 |
| `dataset_extended` | 5003 |
| `detector_results` | 29 |
| `docs` | 6 |
| `examples` | 3 |
| `pilot_results` | 5 |
| `statikai` | 6 |
| `tools` | 3 |

- `dataset/`: 40 aile, 200 tam görüntü, 800 kutu, 80 benzersiz fiziksel konfigürasyon.
- `dataset_extended/`: 500 aile, 2500 görüntü, 10000 kutu, 1000 fiziksel konfigürasyon.
- `pilot_results/`: kesilmiş sembol CNN'i, beş epok eğitim ve bozulma sonuçları.
- `detector_results/`: tam görüntü dedektörü, 20 epok geçmişi, donmuş protokol,
  kutu tahminleri, görüntü başına ölçümler ve hata örnekleri.
- `statikai/physics.py`: yalnız sayısal girdilerden dar kapsamlı analitik kiriş çözümü.
- `statikai/frame3d.py`, `statikai_desktop.py`: ayrı, elle tanımlanan 3B çerçeve hattı.
- `examples/`: üç örnek 3B model; görüntülerden çıkarılmış modeller değildir.
- `audit_results/`: tarihsel denetim/komut kayıtları; yeni denetim ayrı alt klasörde.
- `.statikai-python.txt`: bu bilgisayara özgü, proje dışındaki sanal ortama mutlak yol.

## 3. Bağımlılıklar ve çalıştırılan ortam

Windows, Python 3.13.12, CPU. Kullanılan Python:
`C:\Users\HP\Documents\Codex\2026-11-08\t\work\statikai_audit\StatikAI_Codex_Hazir\.venv\Scripts\python.exe`.
Paket kurulmadı veya yükseltilmedi; mevcut ortam doğrulandı. Genel `python` komutu
WindowsApps takma adına işaret ettiği için komutlar doğrulanmış sanal ortam
Python'u ile çalıştırıldı. Bu ortam projenin kendi `.venv` klasörü değildir.

| Etkin gereksinim | Kurulu sürüm | Sonuç |
|---|---|---|
| `pillow>=10.1` | 13.0.0 | BAŞARILI |
| `pytest>=8` | 9.2.0 | BAŞARILI |
| `numpy>=1.24` | 2.5.4 | BAŞARILI |
| `pandas>=2` | 3.1.1 | BAŞARILI |
| `scikit-learn>=1.3` | 1.9.1 | BAŞARILI |
| `torch>=2.1` | 2.15.0+cpu | BAŞARILI |
| `opencv-python-headless>=4.8,<6` | 5.0.0.93 | BAŞARILI |
| `PyniteFEA==3.2.1` | 3.2.1 | BAŞARILI |
| `matplotlib>=3.9,<4` | 3.11.2 | BAŞARILI |

Dokuz doğrudan etkin gereksinim sürüm koşullarını karşılıyor. PIL, NumPy, pandas,
scikit-learn, torch, cv2, Pynite, Matplotlib ve tkinter import kontrolleri BAŞARILI.
`python -m pip check`: **BAŞARILI — No broken requirements found.**
Tkinter standart Python bileşenidir; pip gereksinim dosyasında olmaması hata değildir.

- Intel macOS'a koşullu üç gereksinim Windows'ta etkin değil: o platform kurulumu
  **ÇALIŞTIRILAMADI**. Kurulu PyNite 3.2.1 metadata'sı NumPy>=2.4.0 istiyor;
  Intel Mac CNN gereksinimi NumPy<2. İki dosya o platformda aynı ortamda çözülemez.
- Linux, Apple Silicon macOS ve Intel macOS çalıştırmaları **ÇALIŞTIRILAMADI**.
- Temiz ortamda sıfırdan kurulum **ÇALIŞTIRILAMADI**; kurulu ortamın uyumluluğu
  temiz kurulum testi sayılmaz. GPU/MPS testi yapılmadı.
- Aralıkla tanımlanan paketler yeniden kurulumda farklı sürüm seçebilir.
  Önceki kilit dökümü 3B kurulumu öncesindendir; bu denetimin birleşik ortam dökümü
  `environment_freeze.txt` dosyasında, salt yeniden üretim kanıtı olarak kaydedildi.
- Yalnız masaüstü bağımlılıklarıyla 3B kullanılabilir; sembol demosu ayrıca 2B
  bağımlılıklarını ister. Başlatıcı import kontrolü yapar, tam sürüm doğrulaması yapmaz.

## 4. README iddiaları ile gerçek işlevler

| İddia / beklenti | Kod ve çalıştırma kanıtı | Değerlendirme |
|---|---|---|
| Eski pilot kesilmiş sembolleri sınıflandırır | `Patches` GT kutularından 48x48 RGB kırpım çıkarır; dört sınıf | Doğru; tam diyagram okuma değildir |
| Tam PNG'den sembol kutuları bulunur | `detect_image.py` + TinyDetector / OpenCV; etiketsiz klasörde çalıştı | Dar sentetik alanda mevcut |
| OCR ve görüntüden RA/RB yok | JSON: `ocr_status=not_implemented`, RA/RB=null | README ile uyumlu |
| Analitik kiriş çözümü var | `physics.reactions` doğru sayısal girdilerle çalışır | Görüntüden çözüm bağlantısı yok |
| Sayılar görüntüden okunabilir | Ayrı OCR/sayı çıkarma/eşleştirme modülü yok | Böyle bir yetenek yok; README de iddia etmiyor |
| A/B tespit skorları | 250 görüntü, donmuş eşikler, yeniden aynı TP/FP/FN | README'deki yuvarlanmış skorlarla uyumlu |
| Pilot %100 skoru | Yeniden üretildi fakat tüm test girdileri eğitimde aynen var | Kritik ek açıklama gerekli; yeni bulgu eski raporlarda yok |
| Veri ayrımı sorunsuz | Problem/tam PNG düzeyi temiz; pilot kırpımı düzeyi temiz değil | Genel bir “sızıntı yok” sonucu çıkarılamaz |
| 3B masaüstü hesapları | PyNite, kullanıcı/örnek parametreleri; GUI ve üç örnek doğrulandı | Görüntü AI'ı veya gerçek bina modeli değildir |
| Eski sonuçlar korunur | Yeni üretici/dedektör değerlendirmesinde koruma var; eski araçlarda yok | Korumanın kapsamı dar; bütün araçlara genellenemez |
| Platform taşınabilirliği | Windows çalıştı; diğerleri yalnız kod/metadata incelemesi | Test edilmiş çoklu platform iddiası yok |

README'nin başında 3B modülün bulunması, araştırmanın ana 2B hedefini arka planda
bırakabiliyor. Ayrıca `statikai.__version__` 0.2.0 iken README 0.3 diyor. Bunlar
belgeleme/tanıtım tutarlılığı konusudur; bu denetimde düzeltilmedi.
Eski rapordaki “arayüz yok” satırı 2B görüntü çözüm arayüzünün tarihsel durumudur;
sonradan eklenen ayrı 3B pencereyle aynı özellik sayılmamalıdır.

## 5. Gerçek model dosyaları

| Model | Gerçek görev | Parametre | Checkpoint |
|---|---|---:|---|
| `pilot_results/best_patch_cnn.pt` | GT kırpımı, 48x48 RGB, background/pin/roller/load sınıflandırma | 23844 | epok 5 |
| `detector_results/best_full_image_detector.pt` | 256x160 gri tam görüntü; merkez ısı haritası ve kutu regresyonu | 77683 | epok 17, seed 2209 |

Pilot sınıf sırası: background, pin_support, roller_support, point_load.
Dedektör sırası: pin_support, roller_support, point_load. Bu sıralar aynı değildir.
Yeni ağ sıfırdan eğitilmiştir; metadata'da pretrained_weights=false.

SHA-256:

```text
pilot:    f95c01ae1ea81e015d421f1c6e70ce65f02af9cc4332e9045fdaa8504d182adb
detector: f06b823e8c4d07b9c4816506cf800c7ac601a9b7f9f0c520585f1f64b5476a56
```

Dedektör/checkpoint ve veri CSV özetleri donmuş protokolle eşleşti. Protokol
validasyon A üzerinde seçilmiş eşik 0.2 ve klasik doluluk eşiği 0.55 içeriyor.
Bu denetimde yeniden seçim, eğitim veya test sonucuna göre ayar yapılmadı.
Log ve metadata geçmiş çalışma düzenini destekler; tek başına bağımsız, değişmez
bir ön kayıt kanıtı değildir. Protokol CSV'yi bağlıyor; tüm PNG/etiketleri ve
kaynak kodu tek bir veri sürümü manifestiyle bağlamıyor.

## 6. Veri sızıntısı, fizik ve bilimsel sınırlılıklar

### 6.1 Kritik: eski pilotun gerçek girdileri ayrık değil

`train_pilot.py:25-59`: GT kutusuyla kesme, %22 çevre payı, 48x48 yeniden
boyutlandırma; ayrıca sabit üç konumdan arka plan örnekleri. Farklı temel
problemler, aynı şablon sembolünü tekrar üretir. Fiziksel değerleri değiştirmek
sınıflandırıcının baktığı kırpımı değiştirmeyebilir.

| Karşılaştırma | Eğitimde de bulunan sonraki ayrım girdisi | Ortak benzersiz kırpım özeti |
|---|---:|---:|
| train → val | 280/280 (%100) | 34 |
| train → test | 140/140 (%100) | 30 |

Testte tekrarın sınıf dağılımı: 60 arka plan, 20 mafsal, 20 hareketli mesnet,
40 kuvvet oku; yalnız arka plan sorunu değildir. 420 val/test örneği için
`numpy.array_equal` ile doğrudan eşitlik de doğrulandı. Eşleşen eğitim ve
val/test örneklerinin problem ID'leri farklı; etiket çatışması yok.

**Etki:** %100 skor yeni giriş örnekleri üzerinde genelleme ölçmüyor. Bu, modelin
kesinlikle ezberlediğini kanıtlamaz; değerlendirme girdilerinin eğitim girdilerinden
bağımsız olmadığını kanıtlar. Önceki tam PNG/fizik denetiminin geçmesi bunu yakalamıyor.
Kanıt: `patch_input_duplicates.json`, `patch_duplicate_proof.csv`.

Sonraki çalışma için ayrı bir veri sürümü ve çizim kaynağı/aile düzeyinde ayrım,
son ön işleme sonrası tam tekrar kontrolü ve yeni kilitli test önerilir. Eski
sabit testi sonuca göre temizleyip aynı deneyin skoru gibi sunmak uygun olmaz.

### 6.2 Yeni dedektör: tam tekrar bulunmadı; genelleme kanıtı sınırlı

Gerçek yeniden boyutlandırılmış gri float32 girişleri hash'lendi:
1400 train A, 400 val A, 250 test A+B. Train–val, train–test, val–test ortak
hash sayısı **0/0/0**. Ek 30 boş eğitim negatifi mevcut tam diyagram testiyle
aynı görev örnekleri değildir. Temel problem ID'leri ve eşdeğer/müdahale varyantları
aynı ayrımda tutuluyor; iki veri setinin QA kontrolleri geçti.

Bununla birlikte bütün çizimler aynı proje tarafından üretiliyor; B dış kaynak
bağımsız bir gerçek çizim seti değildir. Yakın benzerlik/şablon etkisi, tek eğitim
tohumu, 50 test ailesi ve yalnız üç basit tarihsel negatif örneği sınırlılıkları
sürüyor. Aile bootstrap aralığı eğitim tohumu ve dış kaynak çeşitliliğini kapsamaz.
Test B'de görülen hatalar gelecekte aynı testi ayarlamak için kullanılmamalıdır.

### 6.3 Eksik 2B çözüm zinciri

OCR, sayısal değer/birim alanları, metin–ok/mesafe eşleştirme, mesnet koordinat
sistemi çıkarımı, piksel–mühendislik konumu dönüşümü, belirsiz girdiyi reddeden
bir ayrıştırma şeması ve görüntüden çözücüye bağlantı yok.
`detect_image.py:33-36` bu alanları açıkça boş bırakıyor.

`evaluate_equilibrium.py:34` değerlendirmede fizik girdilerini ground-truth CSV'den
alır. Bu değerlendirme için referanstır; görüntüden okuma değildir. Tahmin yerine
referans RA/RB'yi verip %100 almak yalnız denetleyiciyi sınar. OCR hatasıyla
öz-tutarlı yanlış fizik çözümü üretilebileceği mevcut testle gösteriliyor.
Bu nedenle küçük denge artığı tek başına görsel okumanın doğru olduğunu kanıtlamaz.

### 6.4 Statik hesaplama denetimi

Desteklenen 2B model: solda mafsal, sağda hareketli mesnet, iki aşağı yönlü tekil
yük; 0<x1<x2<L, P1/P2>0; m ve kN. RB=(P1*x1+P2*x2)/L, RA=P1+P2-RB doğru.
Bu desteklenen alanda yeni bir formül hatası saptanmadı. Kalıcı doğrulama,
NaN/Inf reddi, -O altında geçerlilik, simetri/aynalama testleri geçti.

Referans CSV maksimum moment artığı eski veride 6.00000001e-06 kNm, yeni veride
7.82000029e-08 kNm; kaydedilen ondalıkların yuvarlanmasıyla uyumlu. Birimlerin
OCR ile okunması/doğrulanması ise uygulanmış değil. Değerlendirme kapsama ve
koşullu/tüm referans doğruluğunu ayrı raporluyor; eksik tahminler saklanmıyor.

3B modül birinci mertebe, küçük deplasmanlı, izotrop doğrusal elastik çubuk
modelidir. Öz ağırlık ve düğüm yükleriyle global kuvvet/moment dengesi kontrol edilir.
Alan yükü düğümlere tesir alanıyla verildiği için döşemenin kirişte oluşturduğu
eğilme yoktur. Döşeme/perde/rijit diyafram, P-Delta, çatlama, ahşap anizotropisi,
yönetmelik yükleri ve boyutlandırma yoktur; bunlar README'de de açıklanıyor.
Çok katlı sonuçlar bağımsız ikinci bir çözücüyle karşılaştırılmış değil.

### 6.5 Deney sonuçlarının üzerine yazma riski

- `generate_dataset.py:69-104` eski dizin varsa CSV/PNG/etiketleri tekrar yazar.
  Denetime ait küçük bir geçici veri setinde var olan CSV işaretçisi gerçekten
  üzerine yazıldı: koruma beklentisi **BAŞARISIZ**. Gerçek veri setine dokunulmadı.
- `train_pilot.py:103,120,133` eski çıktı dizinini kabul edip ağırlık/rapor yazar.
  Kod incelemesi bulgusudur; eski ağırlığı riske atacak eğitim çalıştırılmadı.
- `test_visual_shift.py`, `evaluate_equilibrium.py`, `detect_image.py` aynı --out
  yolunu yeniden yazabilir. `tools/verify_desktop.py` ve GUI --smoke-test de sabit
  rapor yolları kullanır. Denetim çıktıları yeni dizine veya yalıtılmış kopyaya yönlendirildi.
- Yeni `generate_extended_dataset.py`, `train_detector.py`, `evaluate_detectors.py`
  belirli mevcut deney dosyalarında koruma uyguluyor; bu bütün proje araçları için
  genel bir koruma değildir.

### 6.6 Daha düşük öncelikli teknik açıklar

OpenCV tespit skoru tüm adaylarda sabit 0.9'dur (`detection.py:72`); güven olasılığı
olarak kullanılamaz. Öğrenilmiş skorlar da kalibre edilmiş hata olasılığı değildir.
CLI `review_required=true` döndürüyor, fakat doğrulanmış otomatik ret/kabul politikası yok.
Ölçümlerde “tam doğru görüntü” koşulu sabit dört nesne bekliyor; farklı kiriş tiplerine
genellenmiş bir ölçüm değildir. Mevcut dosya hash koruması ve testler bunu değiştirmez.

GUI çalışma alanı ve Matplotlib importları başlangıç try bloğundan önce kuruluyor;
bağımlılık/yazma izni hatası pythonw ile görünmeyebilir. Tk callback hataları ayrı
bir merkezi hata kancasına bağlanmamış. Bunlar kod incelemesi bulgularıdır;
normal örnek çözümü geçti, hata dalları kapsamlı arıza enjeksiyonuyla test edilmedi.

## 7. Gerçek yeniden değerlendirme sonuçları

### 7.1 Tam görüntü tespiti — mevcut donmuş protokol, yeniden eğitim yok

Doğru sınıf, IoU>=0.50, bire bir eşleştirme. Tespit F1'i OCR veya statik çözüm başarısı değildir.

| Yöntem | Stil | Görüntü | TP / FP / FN | Tespit F1 | Tam 4 nesne doğru, fazladan kutu yok |
|---|---|---:|---:|---:|---:|
| OpenCV | A | 200 | 794 / 0 / 6 | %99.6236 | %97.00 |
| OpenCV | B | 50 | 150 / 50 / 50 | %75.0000 | %0.00 |
| OpenCV | Tümü | 250 | 944 / 50 / 56 | %94.6841 | %77.60 |
| Öğrenilmiş | A | 200 | 800 / 0 / 0 | %100.0000 | %100.00 |
| Öğrenilmiş | B | 50 | 122 / 9 / 78 | %73.7160 | %2.00 |
| Öğrenilmiş | Tümü | 250 | 922 / 9 / 78 | %95.4946 | %80.40 |

B'de öğrenilmiş mafsal recall %42; hareketli mesnet recall %2; kuvvet oku recall %100.
Aynı stilde klasik hareketli mesnet recall %0. Ortak toplam skorun yüksek görünmesi,
B başarısızlığını ortadan kaldırmaz. Yöntemler arası genel/istatistiksel üstünlük
iddiası çıkarılmadı. 500 satırlık kayıtlı görüntü-yöntem ölçümlerinin toplamları da doğrulandı.

### 7.2 Eski pilot bozulma tanılaması — aynı ağırlık, GT kırpımları

| Koşul | Kırpım | Accuracy | Macro-F1 |
|---|---:|---:|---:|
| normal | 140 | 1.0 | 1.0 |
| greyscale | 140 | 1.0 | 1.0 |
| low_light | 140 | 0.1429 | 0.1 |
| blur_sigma_2 | 140 | 0.4571 | 0.2364 |
| contrast_low | 140 | 0.4286 | 0.1531 |

Bu değerler eski `shift_results.csv` ile aynen eşleşti. Normaldeki tam tekrar
bulgusunu ve küçük test ailesini dikkate almadan genelleme sonucu olarak sunulmamalı.
Bozulma skorları da tam görüntü algılama veya hesaplama başarısı değildir.

### 7.3 Giriş noktaları ve 3B örnekler

Etiket/CSV bulunmayan klasöre A/B PNG kopyalandı. Her iki CLI yöntemi çalıştı.
A'da iki yöntem de dört kutu, B'de klasik dört ve öğrenilmiş üç kutu döndürdü.
**Kutu sayısının dört olması doğru sınıflarla dört doğru nesne bulunduğunu göstermez.**
B'nin gerçek doğruluğu yukarıdaki tüm test ölçümündedir. Bütün JSON'larda OCR ve
RA/RB boş kaldı. Yanlış checkpoint/protokol özeti, beklenen ValueError ile reddedildi.

Yalıtılmış 3B GUI testi dört sekmeyi açtı; 63 düğüm, 126 eleman, 9 mesnet satırı,
31 noktalı diyagram ve büyütülmüş düğüm deplasmanı çizimi oluştu. Üç örnek:

| Örnek | Düğüm / eleman | En büyük düğüm deplasmanı (mm) | Toplam düşey tepki (kN) |
|---|---:|---:|---:|
| Beton için örnek E, 6 kat | 63 / 126 | 6.5053943157 | 4263.000 |
| Ahşap için örnek E, 2 kat | 18 / 26 | 2.2137736855 | 225.650 |
| Mafsallı taban, çift yatay yön | 12 / 16 | 1.8444299406 | 431.000 |

Değerler önceki örnek kayıtlarıyla eşleşti. Bunlar fotoğraftaki yapıların sonuçları değildir.
GUI testi insan eliyle her dosya diyaloğunu/alanı denemek veya bağımsız mühendislik
onayı anlamına gelmez. 3B modülü ve önceki örnek sonuçları değiştirilmedi.

## 8. Her otomatik testin sonucu

İstenen komut, doğrulanmış Python ile `python -m pytest -q`: **41 passed in 15.79s**, çıkış 0.
Her testin ayrı kaydı için `--junitxml` ile ikinci çalıştırma: **41 passed in 9.17s**, çıkış 0.
İlk rapor birleştirmede XML dosyası bulunamadığı için ayrıntı kaydı ikinci komutla alındı;
ürün testlerinde başarısızlık yok. Ham çıktı: `pytest.log`, `pytest_details.log`;
tek tek sonuçlar: `pytest.xml` ve `test_results.json`.
26 test 2B/veri/analitik yardımcılar, 15 test ayrı 3B hattındadır.
`test_visual_shift.py` adı test_ ile başlasa da pytest test fonksiyonu içermez;
beş bozulma tanılaması ayrıca CLI ile çalıştırıldı.

| No | Test | Sonuç |
|---:|---|---|
| 1 | `test_detection::test_one_to_one_matching_counts_duplicate_as_false_positive` | BAŞARILI |
| 2 | `test_detection::test_box_geometry_round_trip_and_empty_image` | BAŞARILI |
| 3 | `test_detection::test_classical_finds_arrow_from_pixels_without_annotation_access` | BAŞARILI |
| 4 | `test_detection::test_full_image_model_loss_backprop_and_inference_have_no_oracle` | BAŞARILI |
| 5 | `test_experiments::test_patches_and_model_shapes` | BAŞARILI |
| 6 | `test_experiments::test_oracle_prediction_evaluation` | BAŞARILI |
| 7 | `test_extended_data::test_extended_qa_and_controlled_interventions` | BAŞARILI |
| 8 | `test_extended_data::test_qa_detects_cross_split_family_leakage` | BAŞARILI |
| 9 | `test_extended_data::test_qa_rejects_wrong_reference_and_invalid_box` | BAŞARILI |
| 10 | `test_frame3d::test_cantilever_matches_independent_hand_solution[FY-DY-Iz]` | BAŞARILI |
| 11 | `test_frame3d::test_cantilever_matches_independent_hand_solution[FZ-DZ-Iy]` | BAŞARILI |
| 12 | `test_frame3d::test_axial_and_torsion_hand_solutions` | BAŞARILI |
| 13 | `test_frame3d::test_rectangle_square_and_axis_swap` | BAŞARILI |
| 14 | `test_frame3d::test_grid_load_area_and_global_force_moment_balance` | BAŞARILI |
| 15 | `test_frame3d::test_zero_load_and_linear_load_scaling` | BAŞARILI |
| 16 | `test_frame3d::test_isotropic_square_plan_rotates_symmetrically` | BAŞARILI |
| 17 | `test_frame3d::test_invalid_input_rejected[changes0]` | BAŞARILI |
| 18 | `test_frame3d::test_invalid_input_rejected[changes1]` | BAŞARILI |
| 19 | `test_frame3d::test_invalid_input_rejected[changes2]` | BAŞARILI |
| 20 | `test_frame3d::test_invalid_input_rejected[changes3]` | BAŞARILI |
| 21 | `test_frame3d::test_invalid_input_rejected[changes4]` | BAŞARILI |
| 22 | `test_frame3d::test_invalid_input_rejected[changes5]` | BAŞARILI |
| 23 | `test_frame3d::test_invalid_input_rejected[changes6]` | BAŞARILI |
| 24 | `test_frame3d::test_invalid_input_rejected[changes7]` | BAŞARILI |
| 25 | `test_generator::test_reactions` | BAŞARILI |
| 26 | `test_generator::test_dataset` | BAŞARILI |
| 27 | `test_hardening::test_invalid_physics_is_rejected[values0]` | BAŞARILI |
| 28 | `test_hardening::test_invalid_physics_is_rejected[values1]` | BAŞARILI |
| 29 | `test_hardening::test_invalid_physics_is_rejected[values2]` | BAŞARILI |
| 30 | `test_hardening::test_invalid_physics_is_rejected[values3]` | BAŞARILI |
| 31 | `test_hardening::test_invalid_physics_is_rejected[values4]` | BAŞARILI |
| 32 | `test_hardening::test_invalid_physics_is_rejected[values5]` | BAŞARILI |
| 33 | `test_hardening::test_invalid_physics_is_rejected[values6]` | BAŞARILI |
| 34 | `test_hardening::test_validation_survives_python_optimized_mode` | BAŞARILI |
| 35 | `test_hardening::test_symmetric_and_mirror_properties` | BAŞARILI |
| 36 | `test_hardening::test_wrong_reading_can_be_self_consistent` | BAŞARILI |
| 37 | `test_hardening::test_nonfinite_predictions_rejected[values0]` | BAŞARILI |
| 38 | `test_hardening::test_nonfinite_predictions_rejected[values1]` | BAŞARILI |
| 39 | `test_hardening::test_duplicate_and_empty_predictions_rejected` | BAŞARILI |
| 40 | `test_hardening::test_missing_predictions_do_not_inflate_full_accuracy` | BAŞARILI |
| 41 | `test_hardening::test_font_is_available_without_linux_path` | BAŞARILI |

## 9. Ek denetim ve çalıştırılamayan kontroller

“BAŞARILI”, yalnız belirtilen kontrolün beklentisinin karşılandığı anlamındadır.
Örneğin CLI'nin JSON üretmesi, OCR veya kiriş çözümünün başarılı olduğu anlamına gelmez.

| Kontrol | Sonuç | Gerekçe / kanıt |
|---|---|---|
| 27 Python kaynağı ayrıştırma | BAŞARILI | `dependencies.json` |
| İki requirements dosyası, Windows etkin sürümler | BAŞARILI | Dokuz koşul sağlandı |
| pip check, dokuz import | BAŞARILI | `pip_check.log`, `dependencies.json` |
| İki gerçek checkpointin yüklenmesi | BAŞARILI | `checkpoints.json` |
| Orijinal tam veri QA | BAŞARILI | 200 görüntü; problem/fizik/tam PNG ayrımı temiz |
| Genişletilmiş veri QA | BAŞARILI | 2500 görüntü; referanslar/etiketler/split kontrolü |
| Pilot kırpımlarının train–val/test ayrılığı | BAŞARISIZ | Val 280/280, test 140/140 girdisi eğitimde de var |
| Dedektör gerçek girişlerinde tam tekrar ayrılığı | BAŞARILI | Train–val/test ve val–test ortak hash 0 |
| Donmuş 250 görüntü tespit sonucunu yeniden üretme | BAŞARILI | TP/FP/FN/F1/tam görüntü oranları eşleşti |
| Beş pilot bozulma sonucunu yeniden üretme | BAŞARILI | CSV aynen eşleşti |
| Etiketsiz A / classical CLI sözleşmesi | BAŞARILI | Komut/JSON; OCR ve RA/RB üretilmedi |
| Etiketsiz A / learned CLI sözleşmesi | BAŞARILI | Komut/JSON; OCR ve RA/RB üretilmedi |
| Etiketsiz B / classical CLI sözleşmesi | BAŞARILI | Komut/JSON; bu satır tespit doğruluğu testi değil |
| Etiketsiz B / learned CLI sözleşmesi | BAŞARILI | Komut/JSON; üç kutu, eksik nesne var |
| Yanlış checkpoint/protokol reddi | BAŞARILI | Çıkış 1 beklenen ret; `cli_mismatch_guard.json` |
| Üç 3B örnek, yük ve global denge | BAŞARILI | Yalıtılmış `desktop_integration.log` |
| 3B GUI dört sekme/diyagram açılışı | BAŞARILI | Yalıtılmış `desktop_gui.log` ve smoke JSON |
| Eski üreticide var olan veriyi koruma | BAŞARISIZ | Yalnız oyuncak kopyada CSV üstüne yazıldı |
| Eski ölçüm/JSON/CSV tutarlılığı | BAŞARILI | 83 deney artefaktı; ölçüm toplamları doğrulandı |
| Eski kod/veri/ağırlık/sonuç bütünlüğü | BAŞARILI | 5558 dosya; değişen/silinen 0 |
| OCR alan doğruluğu | ÇALIŞTIRILAMADI | OCR modülü ve alan anotasyon/eşleştirme zinciri yok |
| Görüntüden uçtan uca RA/RB doğruluğu | ÇALIŞTIRILAMADI | Çözüm bağlantısı yok; RA/RB=null |
| Gerçek/dış kaynak çizim genellemesi | ÇALIŞTIRILAMADI | Ayrı kaynaklı etiketli test seti yok |
| Linux çalıştırması | ÇALIŞTIRILAMADI | Bu ortam Windows |
| Apple Silicon macOS çalıştırması | ÇALIŞTIRILAMADI | Bu ortam Windows |
| Intel macOS kurulum/çalıştırma | ÇALIŞTIRILAMADI | Ortam yok; birleşik NumPy koşulları çelişiyor |
| Temiz ortamdan bağımlılık kurulumu | ÇALIŞTIRILAMADI | Var olan ortam incelendi; kurulum yapılmadı |
| GUI dosya diyaloglarının insan etkileşim testi | ÇALIŞTIRILAMADI | Smoke testi bu etkileşimleri kapsamıyor |
| Çok katlı modeli bağımsız çözücüyle karşılaştırma | ÇALIŞTIRILAMADI | İkinci çözücü/referans mühendislik modeli yok |

Çalıştırılamayan OCR/çözüm kontrollerine %0 veya %100 gibi deneysel başarı yüzdesi atanmadı.
Eski loglardaki 2 başarısız ve 1 kurulum/collection hatası tarihsel kayıt olarak
korundu; bunlar güncel 41 başarılı testin yerine geçmez.

## 10. Sonraki çalışma önceliği — yalnız öneri

1. Eski pilotun başarı iddiasına kırpım tekrarını ekleyerek araştırma kanıtını düzeltmek;
   yeni veri sürümünde kaynak/aile ve gerçek model girdisi düzeyinde ayrımı doğrulamak.
2. 2B hedef için yeni, bağımsız çizim kaynakları ve ayrı eğitim/validasyon kaynakları
   hazırlamak; mevcut B testine göre eşik ayarlamamak.
3. Faz 3: OCR ve birim/alan anotasyonları, yük–etiket/mesafe eşleştirme; her alanı
   ayrı ölçmek. Fiziksel sayıları CSV'den okuyup OCR sonucu diye sunmamak.
4. Faz 4: doğrulanmış sayısal şema ve belirsiz veriyi ret davranışıyla analitik
   çözücü bağlantısı. Faz 5: aynı sabit testte tam RA/RB hatası, kapsama ve yanlış
   kabul/ret ölçümleri. Faz 6: bu 2B zincir doğrulandıktan sonra görüntü çözüm arayüzü.
5. Deneyler için üzerine yazma koruması ve veri/kod/etiket/paket sürüm manifestini
   genişletmek. Bu denetimde hiçbir koruma veya yeni özellik eklenmedi.

3B masaüstü mevcut ayrı modül olarak korunmalı; öncelik TÜBİTAK araştırmasının
2B görüntüden statik çözüm hattıdır. Şu an savunulabilir tanım: **dar kapsamlı
sentetik kiriş sembol tespit prototipi ve ayrıca kullanıcı tanımlı 3B analiz demosu**.
Tam otomatik statik yapay zekâ veya gerçek yapı güvenliği sistemi tamamlanmış değildir.

## 11. Kanıt ve tekrar çalıştırma

Bütün yeni dosyalar `audit_results/son_durum_20261108_01/` içindedir. Önemli dosyalar:

- `manifest_before.json`, `integrity_after.json`: eski dosyaların korunması.
- `dependencies.json`, `environment_freeze.txt`, `pip_check.log`: ortam.
- `pytest.log`, `pytest_details.log`, `pytest.xml`, `test_results.json`: testler.
- `patch_input_duplicates.json`, `patch_duplicate_proof.csv`: kritik tekrar bulgusu.
- `full_image_input_duplicates.json`, iki `dataset_*_audit.json`: veri incelemesi.
- `frozen_test_recomputed.json`, `frozen_test_predictions.json`, `checkpoints.json`:
  model yükleme ve değişmeyen protokolle ölçüm.
- `pilot_shift.csv`, `inference_summary.json`, `cli_*`: çıkarım/bozulma kayıtları.
- `overwrite_guard.json`, `existing_artifacts_inventory.json`: koruma ve geçmiş kayıtlar.
- `desktop_copy/`: kaynakları değiştirilmemiş yalıtılmış 3B test kopyası ve yeni sonuçları.
- `audit_replay.py`: denetime özel yardımcı; uygulamanın parçası veya yeni araştırma
  özelliği değildir. Mevcut makine/proje ve bu denetimin çıktı yollarına bağlıdır.

İstenen temel komut proje kökünde, doğru ortam Python'uyla:

```powershell
& 'C:\Users\HP\Documents\Codex\2026-11-08\t\work\statikai_audit\StatikAI_Codex_Hazir\.venv\Scripts\python.exe' -m pytest -q
```

Bu raporun oluşturulması eski raporları güncellemez; tarihsel belgeler korunmuştur.
Yeni bulguların sonraki geliştirme aşamasında dikkate alınması gerekir.
