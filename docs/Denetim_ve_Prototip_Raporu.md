# StatikAI — Sistem denetimi ve ilk tam görüntü tespit prototipi

Tarih: 8 Kasım 2026 (Türkiye). Bu rapor çalıştırılmış komutlardan ve kaydedilmiş
JSON/CSV dosyalarından üretilmiştir. Kaynak ZIP korunmuştur; geliştirme bir kopyada yapılmıştır.

## Sonuç ve mevcut yetenek

Sağlanan pilot CNN yalnızca gerçek kutularla kesilmiş sembolleri sınıflandırır.
Yeni 77.683 parametreli dedektör, tam PNG'den mesnet/kuvvet kutularını kendisi
üretir; çıkarımda anotasyon dosyası veya gerçek kutu verilmez. Küçük OpenCV
temel yöntemiyle aynı testte karşılaştırılmıştır.

**OCR, kuvvet/uzunluk okuma, sembol–metin eşleştirme ve görüntüden otomatik
RA/RB çözümü henüz uygulanmamıştır.** Çıktılarda bu alanlar `null`, durumları
`not_implemented` olarak tutulur. Görseldeki sayıların görünmesi okunmuş
oldukları anlamına gelmez. Analitik yardımcı fonksiyonun mevcut olması,
görsel çözüm zincirinin tamamlandığı anlamına gelmez.

## İlk inceleme ve gerçek başlangıç testleri

AGENTS.md, README.md, GELISTIRME_PLANI.md, docs/Codex_Gelistirme_Talimati.md ve
pilot deney raporu tamamen incelendi. Python kodları, etiketler, CSV ve
checkpoint kontrol edildi. İlk sistem Python'unda pytest ve proje paketleri
yoktu; proje içinde ayrı `.venv` oluşturuldu, global Python değiştirilmedi.

Bağımlılıklar hazır olduğunda değişmemiş testlerde **3 başarısız, 1 başarılı**
sonucu alındı. Üç hata sabit Linux font yolundan kaynaklandı
(`baseline_dependencies_ready.log`). Düzeltmeler sonrası nihai otomatik
test komutu `python -m pytest -q`: **26 başarılı** (`full_suite_before_benchmark.log`).
`pip check`: bağımlılık sorunu bulunmadı.

Ara doğrulamada 15 test geçti, dört yeni testin kurulumu bu bilgisayarın ortak
pytest Temp dizinine erişim reddedildiği için hata verdi. Önce yerel basetemp
ile 19 test geçti; sonra conftest.py benzersiz proje-yerel geçici dizin oluşturacak
şekilde eklendi. Nihai düz pytest komutu bu ortamda başarılıdır. Başarısız ara
çalıştırmalar loglardan çıkarılmadı.

## Sağlanan pilot checkpointin yeniden değerlendirilmesi

Eski CNN: 23.844 parametre, checkpoint epoku 5, dört sınıf. Sınıf sırası:
background, pin_support, roller_support, point_load. Yeniden eğitim yapılmadan
verilen ağırlık kullanıldı; verilen raporla aynı yuvarlanmış sonuçlar elde edildi.
Paketin tarihsel eğitim süresi bu oturumda yeniden ölçülmedi.

| Koşul | Test kırpımı | Doğruluk | Macro-F1 |
|---|---:|---:|---:|
| normal | 140 | %100.00 | 1.0000 |
| greyscale | 140 | %100.00 | 1.0000 |
| low_light | 140 | %14.29 | 0.1000 |
| blur_sigma_2 | 140 | %45.71 | 0.2364 |
| contrast_low | 140 | %42.86 | 0.1531 |

Bu test yalnızca **4 temel problemden 140 oracle kırpımı** içerir. Diyagram
tespiti, OCR veya statik çözüm başarısı değildir. Arka plan örnekleri çoğunlukla
boş bir banttan alınmıştır; zor negatifleri temsil etmez. Eğitim/test aynı
çizim üreticisinden gelir; sabit sembol konumları kolaylaştırıcıdır.

## Veri sızıntısı ve veri/etiket denetimi

| Özellik | Sağlanan veri | Yeni veri |
|---|---:|---:|
| Temel problem | 40 | 500 |
| Görüntü | 200 | 2500 |
| Sembol kutusu | 800 | 10000 |
| Benzersiz fiziksel konfigürasyon | 80 | 1000 |
| Ayrımlar arası aynı fiziksel konfigürasyon | 0 | 0 |
| Ayrımlar arası aynı görüntü özeti | 0 | 0 |
| Farklı ailelerde tekrarlayan aynı fizik | 0 | 0 |

Yeni veri: 350/100/50 train/val/test ailesi; 1750/500/250 PNG. Her ailede dört
fiziksel eşdeğer ve yalnızca x1'i değiştiren bir müdahale vardır. Kiriş konumu,
tuval boyutu, sembol boyutları ve yazı konumu değişir. Referans tepkiler her
fiziksel durumda yeniden hesaplanır. Sınıf kimliği, kutu sınırları, nesne sayısı,
etiket içindeki mürekkep varlığı, tam aile yapısı ve analitik referanslar denetlendi.

Mürekkep denetimi semantik etiket doğruluğunun kesin kanıtı değildir. Örnek
görseller ayrıca incelendi. B stili ayrı sembol çizim kuralları kullanır ancak
iki stil de bu projede üretilmiş sentetiktir; dış kaynak bağımsız çizim değildir.
Tam tekrar bulunmaması, gerçek dünya genellemesini kanıtlamaz.

## Statik hesaplar: doğrulananlar ve düzeltilenler

Desteklenen fizik: solda mafsal, sağda hareketli mesnet; iki aşağı yönlü tekil
yük; 0 < x1 < x2 < L. Birimler m ve kN. RB=(P1*x1+P2*x2)/L,
RA=P1+P2-RB bu kapsamda doğrudur. Orijinal CSV'de en büyük moment artığı
6.00000001e-06 kNm; yeni CSV'de
7.82000029e-08 kNm. Bunlar kaydedilen sayıların
yuvarlanmasıyla uyumludur; model tahmini değildir.

- Girdi `assert` kontrolleri Python `-O` ile kayboluyordu. Kapsam dışı yük
  konumuyla hesap yapılabildiği gerçekten gösterildi; kalıcı ValueError doğrulaması eklendi.
- Eski denetleyici NaN tahmininde çözümü doğru saymıyor, fakat fizik uyarısı da
  vermiyordu. NaN/sonsuz girişler artık açıkça reddedilir.
- Eksik tahminlerde kapsama raporlanmıyordu. Kapsama, eksik tahmin sayısı,
  koşullu doğruluk ve tüm referans seti üzerindeki doğruluk ayrı verilir.
- Yinelenen/bilinmeyen görüntüler, boş tahmin CSV'si ve yanlış analitik
  referanslar reddedilir. Kuvvet ve moment toleransları ayrı birimlerle tutulur.
- Simetri, aynalama, geçersiz girdiler ve yanlış okunmuş yük konumunda
  öz-tutarlı ama yanlış çözüm örneği otomatik testlerle sınandı.

Fizik kontrolü doğru girdiye ihtiyaç duyar. Birimlerin otomatik okunması ve
doğrulanması, genel kiriş/çerçeve çözümü, yayılı yükler, moment yükleri,
ankastre mesnet ve hiperstatik sistemler bu sürümün kapsamı değildir.

## Yeni dedektör eğitimi ve sabit test protokolü

CPU, tohum 2209, 20 epok, 77683 parametre,
eğitim döngüsü yaklaşık 304.6 saniye. A stilinden
1400 eğitim görüntüsü ve 30 boş negatif kullanıldı.
Model sıfırdan eğitildi; ön-eğitimli ağırlık kullanılmadı. Merkez ısı haritası
ve kutu regresyonu yaklaşımı küçük bir özel mimariyle uygulandı; resmi
CenterNet modelinin birebir uygulaması olduğu iddia edilmez.

Model epoku ve eşikler yalnızca 100 validasyon ailesinden 400 A görüntüsünde
seçildi. Seçilen epok: 17; öğrenilmiş eşik:
0.2; klasik doluluk eşiği:
0.55. Parametreler testten önce
`frozen_protocol.json` içine yazıldı. Test sonucuna göre yeniden eğitim veya
eşik ayarı yapılmadı. Aynı 50 test ailesinin aynı 250 görüntüsü kullanıldı.

## Gerçek tam görüntü tespit sonuçları

Doğru sınıf + IoU >= 0.50 ile bire bir eşleştirme. Aşağıdaki F1 değerleri
**sembol tespitine** aittir; OCR veya mesnet tepkisi çözüm doğruluğu değildir.

| Test koşulu | Görüntü | OpenCV F1 | Öğrenilmiş F1 | Öğrenilmiş: 4 nesne doğru, fazladan kutu yok |
|---|---:|---:|---:|---:|
| A: eğitimde görülen gösterim | 200 | %99.62 | %100.00 | %100.00 |
| B: eğitimde kullanılmayan gösterim | 50 | %75.00 | %73.72 | %2.00 |
| Birlikte | 250 | %94.68 | %95.49 | %80.40 |

Birleşik testte öğrenilmiş yöntem: TP=922, FP=9,
FN=78; precision %99.03, recall
%92.20. Aile bazında 1000 bootstrap tekrarından F1 için
%95 aralık: %94.96–%96.01. Bu aralık yalnızca bu sentetik
aile örneklemesini kapsar; eğitim tohumu ve gerçek kaynak değişkenliğini kapsamaz.

**Önemli başarısızlık:** B stilinde hareketli mesnet recall değeri öğrenilmiş
yöntemde %2.00;
klasik yöntemde %0.00.
Öğrenilmiş yöntemin B stilinde tüm dört nesneyi doğru bulduğu görüntü oranı
yalnızca %2.00.
Bu sonuç genel diyagram okuyucusunun tamamlandığı şeklinde sunulamaz.
Yöntemler arasındaki küçük toplam F1 farkı için genel üstünlük veya
istatistiksel anlamlılık iddiası yapılmaz.

Boş, yalnız kiriş çizgisi ve yalnız yazı içeren üç basit negatifte her iki
yöntem de sıfır kutu verdi. Üç örnek, geniş kapsamlı yanlış alarm ölçümü değildir.
Skorlar kalibre edilmiş doğru olma olasılıkları değildir.

## Tek görüntü ve on aile tanılaması

`detect_image.py` etiket dosyası bulunmayan ayrı bir klasöre kopyalanan tek
PNG üzerinde gerçekten çalıştırıldı ve dört kutu üretti; OCR ve RA/RB alanları
boş kaldı (`audit_results/inference_image_only.json`). Bu yeni bir bağımsız
test örneği değil, sabit testteki bir görüntünün çıkarım arayüzü kontrolüdür.

Teslim ZIP'i açılarak çıkarılan kopyada aynı çıkarım komutu ayrıca çalıştırıldı
ve başarılı oldu (`packaged_inference_smoke.log`). Paket içindeki model,
protokol ve kaynakların bir arada çalışması doğrulandı. Bu kontrol mevcut
sanal ortamı kullanır; farklı işletim sisteminde temiz kurulum testi değildir.
Kaynak ZIP'teki veri ve pilot sonuçlarına ait 407 dosyanın aynı kaldığı SHA-256
ile doğrulandı (`audit_results/source_zip_integrity.json`).

Önceden tanımlı ilk on test ailesi: [9, 19, 29, 39, 49, 59, 69, 79, 89, 99].
Her ailenin beş varyantı için toplam 50 görüntüde iki yöntemin sonuçları
`diagnostic_10_families.json` içindedir. Her satırda OCR/çözümün eksik olduğu
açıkça belirtilir. Bu, tam otomatik statik çözüm deneyinin tamamlandığı anlamına gelmez.
En düşük F1'li on görüntü/yöntem ve on kanonik aile örneği için kutulu PNG'ler kaydedildi.

## Windows, macOS, Linux

Gerçekte ölçülen ortam: Windows-11-10.0.26200-SP0, Python 3.13.12,
PyTorch 2.15.0+cpu, OpenCV 5.0.0; GPU kullanılmadı.
Sabit Linux font yolu giderildi; başlık/etiket fontu manifestte kayıtlı.
`pathlib`, UTF-8, CPU checkpoint yükleme, OpenCV headless ve sıfır worker veri
yükleme kullanılır. Ortak pytest Temp izin sorunu proje-yerel dizinle çözüldü.

**Linux ve macOS çalıştırılmadı.** Kod incelemesi yapılmıştır. Intel macOS için
resmi yeni PyTorch wheel desteğinin sonlanması nedeniyle Python 3.11,
PyTorch <2.3, NumPy <2, OpenCV <4.12 yolu koşullu gereksinimlere eklendi;
bu kombinasyon ve yeni checkpointin eski PyTorch'ta açılması sınanmadı.
Apple Silicon MPS hızlandırması uygulanmadı. Ayrıntı: docs/Platform_Uyumlulugu.md.

## Geliştirme planı durumu ve bir sonraki çalışma

| Faz | Durum |
|---|---|
| 0 | Denetim, bağımlılıklar, düzeltmeler ve otomatik testler yapıldı |
| 1 | 500 ailelik sentetik veri ve iki gösterim stili, QA ve testler yapıldı; dış kaynak gerçek çizim henüz yok |
| 2 | Bir tam görüntü dedektörü eğitildi, bir OpenCV yöntemi çalıştırıldı ve sabit testte kıyaslandı; stil aktarımı yetersiz |
| 3 | OCR ve geometrik ilişkilendirme uygulanmadı |
| 4 | Analitik yardımcı fonksiyon sağlamlaştırıldı; görüntüden çözüm zinciri uygulanmadı |
| 5 | Tam çözüm kıyaslaması ve dış kaynak bilimsel deney henüz yapılmadı |
| 6 | Arayüz yapılmadı |

Önerilen sonraki deney: test B üzerinde ayar yapmadan, yeni eğitim/validasyon
kaynaklarında mesnet biçimlerini çeşitlendirmek; yeni ve kilitli dış kaynak
test seti hazırlamak. Ardından faz sırasına göre OCR ve metin–sembol eşleştirme.
Güvenlik kararı veya gerçek yapı tasarımı için kullanılmaz.

## Gerçek komut kayıtları

Her JSON kaydı komutu, başlangıç zamanını (UTC), çıkış kodunu, süreyi ve Python
kaynak özetlerini içerir. Ham stdout/stderr yanındaki `.log` dosyasındadır.
Başarısız başlangıç/ara kayıtları korunmuştur.

| Çalıştırma | Çıkış kodu | Süre (s) | Ham çıktı |
|---|---:|---:|---|
| `baseline_dependencies_ready` | 1 | 18.913 | `audit_results/logs/baseline_dependencies_ready.log` |
| `baseline_original` | 2 | 2.416 | `audit_results/logs/baseline_original.log` |
| `dependency_check_final` | 0 | 1.643 | `audit_results/logs/dependency_check_final.log` |
| `detector_training_cpu` | 0 | 315.422 | `audit_results/logs/detector_training_cpu.log` |
| `detector_unit_tests` | 0 | 4.432 | `audit_results/logs/detector_unit_tests.log` |
| `final_extended_qa` | 0 | 6.870 | `audit_results/logs/final_extended_qa.log` |
| `final_original_qa` | 0 | 0.925 | `audit_results/logs/final_original_qa.log` |
| `fixed_test_benchmark` | 0 | 20.778 | `audit_results/logs/fixed_test_benchmark.log` |
| `full_suite_before_benchmark` | 0 | 24.892 | `audit_results/logs/full_suite_before_benchmark.log` |
| `inference_without_label_files` | 0 | 2.933 | `audit_results/logs/inference_without_label_files.log` |
| `original_adversarial_probes` | 0 | 0.231 | `audit_results/logs/original_adversarial_probes.log` |
| `original_optimized_assert_probe` | 0 | 1.004 | `audit_results/logs/original_optimized_assert_probe.log` |
| `packaged_inference_smoke` | 0 | 3.149 | `audit_results/logs/packaged_inference_smoke.log` |
| `phase0_dataset` | 0 | 1.668 | `audit_results/logs/phase0_dataset.log` |
| `phase0_tests` | 1 | 10.825 | `audit_results/logs/phase0_tests.log` |
| `phase0_tests_local_temp` | 0 | 9.239 | `audit_results/logs/phase0_tests_local_temp.log` |
| `phase1_dataset_qa` | 0 | 67.456 | `audit_results/logs/phase1_dataset_qa.log` |
| `phase1_generate_500` | 0 | 45.915 | `audit_results/logs/phase1_generate_500.log` |
| `phase1_tests` | 0 | 15.696 | `audit_results/logs/phase1_tests.log` |
| `pilot_checkpoint_recheck` | 0 | 5.478 | `audit_results/logs/pilot_checkpoint_recheck.log` |

## Teknik kaynaklar

- Merkez tabanlı tespit fikri: https://arxiv.org/abs/1904.07850
- OpenCV bağlı bileşenler: https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html
- Font yükleme: https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
- Checkpoint yükleme: https://docs.pytorch.org/docs/2.15/generated/torch.load.html
- Intel macOS desteği: https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690
- NumPy/OpenCV sürüm ilişkisi: https://github.com/opencv/opencv-python/issues/1122
