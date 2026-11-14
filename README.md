# StatikAI — 3B masaüstü ve görüntü araştırma prototipi (0.4)

## Yeni (0.4): düzensiz aks, kat kat kesit, rijit diyafram, yük kombinasyonları

3B masaüstü çerçeve uygulaması (`StatikAI_Baslat.cmd` / `statikai_desktop.py`):

- **Geometri:** her açıklık ve kat yüksekliği ayrı girilir: `6;4.5;3`, `4;3@3`
  (`n@değer` = n kez tekrar). En çok 10 kat, her yönde 5 açıklık.
- **Kesitler kat kat:** `2@50x50;2@40x60`. Kolonda 1. değer global X, 2. değer
  global Z yönündeki boyuttur (yön her zaman açıktır). Kirişte b×h.
- **Yük durumları:** G (öz ağırlık + döşeme ölü yükü), Q (hareketli), EX, EZ (elle
  girilen kat yatay yükleri). Döşeme alan yükleri 45° zarf kuralıyla kirişlere
  üçgen/trapez yayılı yük olarak gider; kirişler açıklık momenti alır.
- **Kombinasyonlar:** varsayılan TS 500 / TBDY 2018 biçimi (G+Q, 1.4G+1.6Q, G+Q±E,
  0.9G±E), arayüzden düzenlenebilir. Sonuçlar tek kombinasyon ya da **zarf** olarak.
- **Rijit diyafram (seçmeli):** her kat kendi düzleminde rijit; kütle ve rijitlik
  merkezi farklıysa kat burulması da görünür.
- **Kat ötelemeleri:** her kat için Δx, Δz, Δ/h, uyarı sınırı ve grafik.
- Her kombinasyonda global kuvvet/moment dengesi denetlenir; tutmazsa sonuç reddedilir.

El çözümüyle karşılaştıran testler: ankastre kirişte trapez yük uç momenti,
rijit kirişli katta kolon yanal rijitliği (12EI/h³, iki kolon yönü), diyaframda
düzlem içi mesafelerin korunması, kombinasyonların süperpozisyonu.

**Hâlâ yok:** TBDY deprem yükü (spektrum/mod analizi), perde duvar, P-Delta,
hareketli yük dama yüklemesi, betonarme/ahşap boyutlandırma. Gerçek yapı
güvenliği kararı için kullanılamaz.

### 3B kodun yapısı

```
statikai/frame3d/   hesap motoru
  config.py         girdi modeli (şema v3), doğrulama, v1/v2 dosya dönüşümü
  loads.py          döşeme zarf yükü, tesir alanı dağıtımı
  model.py          PyNite modeli: düğüm, eleman, kesit, diyafram, yükler
  analysis.py       çözüm, denge denetimi, uç değerler, zarf, kat ötelemesi
statikai/gui/       Tkinter arayüzü
  parsing.py        "3@5", "2@50x50" metin ayrıştırma (birim testli)
  inputs.py         sol parametre paneli, kombinasyon penceresi
  results.py        sonuç sekmeleri, tablolar, grafikler
  app.py            ana pencere, arka plan hesap, dosya işlemleri
statikai_desktop.py başlatıcı
```

Eski `statikai_regular_frame_v1/v2` model dosyaları açılır ve otomatik dönüştürülür.

## Yeni: doğrulamadan sonra görüntüden mesnet tepkileri

`StatikAI_2B_Baslat.cmd` ayrı 2B görüntü yükleme penceresini açar.
Görüntü tespiti → OCR → ölçü grafı → kapsam/girdi doğrulaması → korunmuş
analitik çözücü → kuvvet/moment dengesi tek hatta bağlandı.
Eksik, uyarılı veya kapsamı doğrulanamayan veri hesaplanmaz; kısmi alanlar
çözücüye aktarılmaz. Yatay, solda mafsal/sağda hareketli mesnet ve iki
aşağı yönlü tekil yük dar alanı içindir. Denge doğru okuma kanıtı değildir.

```powershell
python -m pip install -r requirements.txt -r requirements-ocr.txt
python solve_beam_image.py --image dataset_dimensions_v2/images/beam_0000_v0.png --out work/ilk_cozum.json
python statikai_beam_app.py
```

[Çalıştırma ve JSON açıklaması](docs/Uctan_Uca_Kiris_Kullanimi.md),
[gerçek uçtan uca test raporu](UCTAN_UCA_RAPORU.md).
Eski 3B pencere ve OCR-only komutları ayrı ve korunmuş işlevlerdir.
Alt sürüm raporlarındaki “statik entegrasyon yok” cümleleri o sürümü anlatır.

## Yeni: OCR ve geometrik eşleştirme araştırma modülü

`read_beam_diagram.py` görüntüden kuvvet/ölçü metinlerini okuyup korunmuş V3
dedektörünün sembolleriyle eşleştirir. `N/kN` ve `mm/cm/m` açık birimleriyle
çalışır; mesafeleri ölçü zincirlerinden türetir. Her değer için kaynak kutuları,
metin kimlikleri ve mevcut güven skorları JSON'a kaydedilir. Eksik veya belirsiz
girdi inceleme ister; değerler piksel ölçeğinden tamamlanmaz.

```powershell
python -m pip install -r requirements.txt -r requirements-ocr.txt
python read_beam_diagram.py --image dataset_dimensions_v2/images/beam_0000_v0.png --out work/ilk_ocr.json
```

Kapsam yatay, solda mafsallı/sağda hareketli mesnetli ve iki düşey tekil yüklü
sentetik 2B çizimlerdir. Bu modül henüz masaüstü arayüzünde değildir; **statik
motoru çalıştırmaz**, RA/RB `null` kalır. Önceden eğitilmiş OCR kullanılır;
kendi verilerimizle yeni OCR eğitimi yapılmış gibi sunulmaz.

Kurulum, JSON şeması, ölçüm tanımları ve gerçek sınırlar:
[OCR_ve_Geometrik_Eslestirme.md](docs/OCR_ve_Geometrik_Eslestirme.md).
Gerçek deney sonuçları: [OCR_VE_GEOMETRI_RAPORU.md](OCR_VE_GEOMETRI_RAPORU.md).
V1 ve güvenlik düzeltmeli V1.1 deneyleri ayrı klasörlerde korunur.
Alt bölümlerdeki “OCR yok” ifadeleri ilgili eski sürüm/komutları anlatır.

## Yeni nesne tespiti deneyi — V3

`train_detector_v3.py` eski dedektörleri değiştirmeyen ayrı bir deney hattıdır.
LiteFPNCenter-v1 (22.927 parametre), V2 eğitim/validasyon verisi ve yeni fiziksel
problemlerden oluşan önceden kilitlenmiş sentetik test kullanır. Eski TinyDetector
aynı veride yeniden eğitilen bir karşılaştırma modeli ve ayrıca donmuş eski
ağırlığıyla korunur. Klasik OpenCV de aynı yeni testte değerlendirilir.

Mimari, kaynaklar, seçim/ayrım ve sınırlılıklar:
[Dedektor_V3_Teknik_Plan.md](docs/Dedektor_V3_Teknik_Plan.md).
Yeni ağırlıklar, gerçek eğitim kayıtları ve değerlendirme:
`experiments/detector_v3_20261108_01/`. Gerçek sonuçlar [DEDEKTOR_V3_RAPORU.md](DEDEKTOR_V3_RAPORU.md) içinde. Yeni testte
yeniden eğitilen Tiny F1=0.9036, LiteFPN F1=0.8667; yeni mimari üstün çıkmadı.
62 otomatik test geçti. İki adayı ayrı kullanmak için:

```powershell
python detect_trained_symbols.py --model tiny --run experiments/detector_v3_20261108_01 --image yol/goruntu.png --out work/yeni_tespit.json
```

Bu komut tam görüntüden piksel kutuları verir. OCR ve otomatik statik çözüm değildir.
Ağırlık ve validasyonda sabitlenen eşik birlikte kullanılır; mevcut masaüstü
sembol demosu ayrı, eski giriş noktasıdır. Eski test protokolleri değişmez.

## 2B araştırma verisi — ölçülendirilmiş V2

**Gerçek doğrulama:** 54 test geçti; 2500 görüntünün tam QA denetimi geçti.

Yeni `dataset_dimensions_v2/` sürümü, eski 500 problem/2500 görüntüyü koruyarak
ayrı çizimler üretir. Hazır L/x1/x2 satırının yerine ölçü çizgileri ve farklı
birim/font/sembol düzenleri kullanır. Kaynak problem kimlikleri ve veri ayrımları
korunur; yeni model eğitimi, OCR veya otomatik çözüm bu aşamanın kapsamı değildir.
Üretim, etiket sözleşmesi ve bilimsel sınırlar:
[Veri_Seti_V2_Kullanimi.md](docs/Veri_Seti_V2_Kullanimi.md).
Gerçek veri/test sonuçları: [VERI_SETI_V2_RAPORU.md](VERI_SETI_V2_RAPORU.md).


## Uygulamayı açma

Windows'ta **StatikAI_Baslat.cmd** dosyasına çift tıklayın. Açılışta örnek beton
çerçeve hesaplanır. **Örnek ahşap** ve **Düzensiz örnek** düğmeleri diğer örnekleri
yükler. Soldan açıklık, kat yüksekliği, malzeme, kesit, yük ve kombinasyonları
değiştirip **3B HESAPLA** düğmesine basın. Sonuçlar sağdaki beş sekmede görünür:
3B model, düğüm deplasmanları, mesnet tepkileri, eleman kuvvetleri, kat ötelemeleri.
Sol paneli aşağı kaydırarak model kaydet/aç ve JSON dışa aktarmaya ulaşılır.

**Gönderilen iki resmin gerçek hesabı yapılmadı.** Bu uygulama ortogonal akslı
bir çerçeveyi elle girilen/örnek parametrelerle kurar. Görüntüden 3B geometri,
ölçü, malzeme veya yük çıkarmaz. 3B çözüm PyNite sayısal analiz motorudur;
yapay zekâ tahmini değildir. Eski kiriş sembol tespit demosu ayrı bir modüldür.

Birinci mertebe, izotrop doğrusal elastik çubuk modeli kullanılır. Kapsam ve
eksikler yukarıdaki 0.4 bölümündedir; gerçek yapı güvenliği için kullanılamaz.

### Yalnızca masaüstü uygulaması kurulumu

Normal Tcl/Tk içeren Python 3.12/3.13 önerilir. Windows başlatıcı gerekirse
`.venv` oluşturup `requirements-desktop.txt` kurar. Görsel yapay zekâ demosu için
ayrıca aşağıdaki eski araştırma bağımlılıkları gereklidir; 3B uygulama PyTorch
kurulumu gerektirmez. Terminalden:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe statikai_desktop.py
```

Linux/macOS: `.venv/bin/python -m pip install -r requirements-desktop.txt`,
ardından `.venv/bin/python statikai_desktop.py`; Tk ve grafik oturumu gerekir.
Bu platformlarda çalıştırılmadı. Intel macOS'taki eski CNN bağımlılıklarıyla
aynı ortama kurulması NumPy sürüm çakışmasına yol açar; ayrı ortam kullanın.

### Doğrulama

Her iki bağımlılık dosyası kurulu Windows ortamında 197 test geçti (0.4). Yalnız
eski bağımlılıklar kuruluysa 3B test modülü açıklamalı olarak atlanır.

```powershell
python -m pip install -r requirements.txt -r requirements-desktop.txt
python -m pytest -q
python tools/verify_desktop.py
python statikai_desktop.py --smoke-test
```

Gerçek komutlar/çıktılar `audit_results/logs/desktop_*.log` ve `.json` dosyalarında.
Yeni kapsam, sonuçlar ve sınırlılıklar: `docs/3B_Masaustu_Raporu.md`.
`examples/` altında düzenlenebilir dört örnek model JSON'u (şema v3) bulunur.

### Depoya alınmayanlar

`work/` (geçici çalışma dosyaları) ve `experiments/` altındaki PNG tanı
görüntüleri (~118 MB) boyut nedeniyle depoda yoktur. Model ağırlıkları, OCR
modelleri, protokoller ve metrik JSON'ları depodadır; görüntüler ilgili
değerlendirme komutlarıyla yeniden üretilebilir.

---

# StatikAI — denetlenmiş araştırma prototipi (0.2)

Bu sürüm tam PNG üzerinde mafsallı mesnet, hareketli mesnet ve aşağı yönlü
kuvvet oku kutularını bulmayı dener. İki yöntem vardır: OpenCV temel yöntemi
ve sıfırdan CPU'da eğitilmiş küçük bir dedektör.

**OCR, kuvvet/uzunluk okuma, sembol–metin eşleştirme ve görüntüden otomatik
statik çözüm henüz yoktur.** Çıkarım JSON'unda RA/RB boş bırakılır. Görselde
bulunan sayılar okunmuş çıktı değildir. Gerçek yapı tasarımı veya güvenlik
kararı için kullanılamaz.

Sağlanan eski `train_pilot.py` ve `pilot_results/best_patch_cnn.pt`, gerçek
kutularla kesilmiş 48x48 sembolleri dört sınıfa ayıran ayrı bir pilottur.
Yeni dedektörle karıştırılmamalıdır. Eski veri ve pilot ağırlığı korunmuştur.

## Gerçek sonuçlar

Aynı 50 test ailesinden 250 görüntü; doğru sınıf ve IoU >=0.50; model/eşik
seçimi yalnızca A-validasyon grubunda. A: eğitimde görülen gösterim.
B: eğitimde kullanılmayan ikinci sentetik gösterim; dış kaynak gerçek çizim değildir.

| Stil | Görüntü | OpenCV tespit F1 | Öğrenilmiş tespit F1 | Öğrenilmiş: tüm 4 nesne doğru |
|---|---:|---:|---:|---:|
| A | 200 | %99.62 | %100.00 | %100.00 |
| B | 50 | %75.00 | %73.72 | %2.00 |

B stilinde hareketli mesnet recall değeri öğrenilmiş yöntemde yalnızca %2'dir.
Bu nedenle aynı üreticinin kolay görüntülerindeki yüksek skor genelleme
başarısı olarak sunulamaz. Tam sonuçlar, hata örnekleri, aile bazında güven
aralıkları: `detector_results/evaluation/`. Bunlar statik çözüm doğruluğu değildir.

## Kurulum — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Linux / Apple Silicon macOS için `python3 -m venv .venv` ve
`.venv/bin/python -m pip install -r requirements.txt` kullanılır. Intel macOS
ayrı sürüm koşulları gerektirir; `docs/Platform_Uyumlulugu.md` okunmalıdır.
Yalnız Windows çalıştırılmıştır; macOS/Linux için test edilmişlik iddiası yoktur.

## Tek görüntüden sembol tespiti

Ortam etkinleştirildikten sonra aşağıdaki `python` komutları kullanılabilir.
Windows'ta ortamı etkinleştirmek yerine `python` yerine
`.\.venv\Scripts\python.exe` yazılabilir.

```bash
python detect_image.py --image dataset_extended/images/beam_0009_v0.png --method learned --out work/tespit.json
python detect_image.py --image dataset_extended/images/beam_0009_v0.png --method classical --out work/klasik.json
```

Görüntünün yanında etiket/CSV bulunması gerekmez. Seçilen checkpoint ve
protokol varsayılan olarak pakettedir. Yeni ağırlık kullanılıyorsa onunla
uyumlu donmuş eşik protokolü de verilmelidir. Çıktıda sembol kimliği ve piksel
kutusu bulunur: 0=mafsal, 1=hareketli mesnet, 2=kuvvet oku.
Bu sınıf sırası eski dört sınıflı pilotun sırasından farklıdır.

## Yeniden üretim — mevcut sonuçları koruyan yeni klasörler

```bash
python audit_dataset.py --dataset dataset --out work/orijinal_qa.json
python generate_extended_dataset.py --n 500 --seed 20261108 --out dataset_yeniden
python audit_dataset.py --dataset dataset_yeniden --out work/yeni_qa.json
python train_detector.py --dataset dataset_yeniden --epochs 20 --seed 2209 --out experiments/detector_run_2
python evaluate_detectors.py --dataset dataset_yeniden --checkpoint experiments/detector_run_2/best_full_image_detector.pt --out experiments/detector_run_2/evaluation
```

Üretici ve değerlendirme aracı mevcut sonuçları üzerine yazmayı reddeder;
her deney için yeni klasör kullanılır. Aynı test sonuçlarına bakarak eşik
ve hiperparametre ayarlanmaz. Font ve paket sürümü değişirse görüntü pikselleri
ve eğitim sonuçları da değişebilir. Ölçülen Windows ortamı
`audit_results/environment-windows-py313.lock.txt` dosyasındadır.

## Dosyalar ve geliştirme sırası

- `docs/Denetim_ve_Prototip_Raporu.md`: gerçek test sonuçları, denetim ve sınırlar.
- `docs/Faz2_Teknik_Plan.md`: tespit yaklaşımı ve veri ayrımı protokolü.
- `docs/Platform_Uyumlulugu.md`: platform değerlendirmesi ve kurulum.
- `generate_dataset.py`, `dataset/`: korunmuş pilot veri akışı; font ve girdi doğrulaması düzeltildi.
- `generate_extended_dataset.py`, `dataset_extended/`: 500 aile, 2500 görüntü, iki sentetik stil.
- `statikai/detector_model.py`, `train_detector.py`: tam görüntü dedektörü.
- `statikai/detection.py`: klasik yöntem ve bire bir kutu ölçümü.
- `detect_image.py`: etiketsiz tek görüntü çıkarımı.
- `evaluate_detectors.py`: validasyonda seçim, donmuş ortak test ve tanılama.
- `evaluate_equilibrium.py`: dışarıdan verilmiş tepkilerin referansla denetimi; görsel çözüm değildir.
- `audit_results/logs/`: başarısız ara denemeler dahil gerçek komut çıktıları.
- `detector_results/evaluation/diagnostic_10_families.json`: önceden belirlenen on ailenin 50 görüntüsü;
  OCR/çözüm eksikliği açıkça işaretlenir.

Faz 0 denetimi ve Faz 1 sentetik veri genişletmesi yapıldı. Faz 2 sınırlı
prototip olarak ölçüldü. Sıradaki Faz 3 OCR ve geometrik eşleştirmedir; bundan
sonra Faz 4 görsel girdiden statik çözüm entegrasyonu gelir. Faz 5 tam çözüm
kıyaslaması ve Faz 6 arayüz yapılmadı. Ayrıntılı sıra `GELISTIRME_PLANI.md` içindedir.
