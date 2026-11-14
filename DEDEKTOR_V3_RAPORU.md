# StatikAI — V3 nesne tespiti gerçek deney raporu

Tarih: 8 Kasım 2026 (Türkiye). Deney: `experiments/detector_v3_20261108_01/`.
Rapor tamamlanan eğitim/değerlendirme dosyalarından üretilmiştir. Eski ağırlık,
veri ve sonuçlar değiştirilmedi. OCR veya görüntüden otomatik statik çözüm yapılmaz.

## Sonucun yorumu

Bu testte toplam F1 bakımından yeniden eğitilen TinyDetector daha iyi ölçüldü:
0.9036, yeni LiteFPNCenter 0.8667. Yeni mimarinin genel üstünlüğü gösterilemedi.
Eski donmuş ağırlık 0.4403, klasik OpenCV 0.3338 F1 verdi. Yeni veri/eğitim/artırma
ve etiket kapsamı birlikte değiştiğinden fark tek bileşene atfedilemez.

LiteFPN roller FN sayısını 62'den 35'e düşürdü; roller recall 0.9271, Tiny 0.8708.
Ancak roller FP 100'e karşı 67; roller precision 0.8165'e karşı 0.8619. Roller
F1 değerleri 0.8683 ve 0.8663 ile yakındır. Daha az FN, tek başına genel olarak
daha güvenilir bir dedektör demek değildir; sınıflar ve FP/FN birlikte ele alınmalıdır.
Hiçbir ağırlık/eşik/veri bu test sonuçlarıyla yeniden ayarlanmadı.

## Gerçek test sonucu

Aynı yeni 520 görüntüde doğru sınıf + IoU>=.50 ile skor sıralı bire bir eşleştirme.
Bunlar sembol tespit skorlarıdır; OCR, RA/RB veya gerçek yapı güvenliği başarısı değildir.

| Yöntem | Precision | Recall | F1 | Ortalama IoU, yalnız TP | Her GT için en iyi aynı-sınıf IoU; kaçırma=0 |
|---|---:|---:|---:|---:|---:|
| LiteFPNCenter yeni | 0.9370 | 0.8063 | 0.8667 | 0.7764 | 0.6268 |
| Tiny aynı V2 ile yeniden eğitim | 0.9443 | 0.8661 | 0.9036 | 0.7406 | 0.6466 |
| Eski Tiny donmuş ağırlık | 0.6604 | 0.3302 | 0.4403 | 0.6639 | 0.2494 |
| OpenCV değişmemiş yöntem | 0.9138 | 0.2042 | 0.3338 | 0.8822 | 0.1810 |

Yeni modelin aynı V2 ile yeniden eğitilen Tiny karşısındaki F1 farkı: **-0.0368**.
1000 aile bazlı eşlenik bootstrap %95 aralıkları:

- Yeni model F1: [0.8494827326979576, 0.8840305936870357].
- Tiny F1: [0.8918031647223104, 0.9146833223308531].
- Eşlenik F1 farkı: [-0.05406258026243181, -0.018940282698733078].

Fark aralığı sıfırı içeriyorsa genel/istatistiksel üstünlük iddiası yapılmamalıdır.
Aralıklar bu sentetik test ailelerini kapsar; eğitim tohumu veya gerçek kaynak
çeşitliliğini kapsamaz. Eski donmuş ağırlık farklı veri ve kutu tanımıyla eğitildi;
aynı V2 verisinde yeniden eğitilen Tiny esas mimari karşılaştırmasıdır.

## Mimari ve gerekçe

LiteFPNCenter-v1, **22.927 parametreli**, özel 384x256 gri tam görüntü ağıdır.
Depthwise/pointwise kodlayıcı, stride 16→8→4 yanal/yukarı FPN bağlantıları,
stride 4 merkez ısı haritası ve sınıfa özel kutu/ofset regresyonu kullanır.
Hafif katmanlar CPU maliyetini sınırlamak, daha yüksek çözünürlük ve FPN küçük
mesnet ayrıntılarını bağlamla birleştirmek, ayrı kutular uzun ok/kompakt mesnet
geometrilerini ayırmak için seçildi. Resmi MobileNet veya CenterNet uygulaması değildir.

Birincil kaynaklar:
[MobileNets](https://arxiv.org/abs/1704.04861),
[Feature Pyramid Networks](https://arxiv.org/abs/1612.03144),
[Objects as Points](https://arxiv.org/abs/1904.07850).

Ön eğitim/transfer learning kullanılmadı. Küçük üç sınıflı ağ yalnız kendi çizim
verimizle sıfırdan eğitildi; ImageNet aktarımıyla karşılaştırma yapılmadı.
TinyDetector-v1 77.683 parametre/256x160 girişiyle ve kaynak koduyla korundu.
Yeni üçüncü taraf bağımlılık gerekmedi. Giriş çözünürlüğü, kapasite ve kayıp da
farklı olduğundan mimarinin tek başına etkisi ayrıştırılamaz.

## Eğitim ve gerçek süre

V2 eğitim: 350 aileden **1750 görüntü +96 negatif**. Validasyon: farklı 100 aileden
**500 görüntü**. Eski 50 test ailesi eğitim/model/eşik seçiminde ve yeni test
skorunda kullanılmadı. Önceki test skorlarına göre yeni parametre araması yapılmadı.

Yalnız eğitimde: yatay çevirme, ±5 derece dönüş, 0.8–1.12 ölçek, %6 öteleme,
parlaklık/kontrast/gamma, hafif bulanıklık/gürültü ve %8 renk tersleme.
Kutu köşeleri aynı dönüşümden geçirilir; aşırı kırpılan dönüşüm reddedilir.
Yatay çevirme metni de ters çevirir; bu OCR değil tespit artırmasıdır.
Validasyon değişmez; test bozunumları eğitimden önce bir kez oluşturuldu.

Windows 11, Ryzen 9 8945HS (8/16), Python 3.13.12, PyTorch 2.15.0+cpu.
Bilgisayarda RTX 4060 vardır; kurulu PyTorch +cpu sürümü CUDA sunmuyor. Bu önceden kaydedilmiş deney CPU'da tamamlandı; GPU kurulumu/eğitimi denenmedi. Eğitimler sırayla CPU'da iki iş parçacığı/batch 12 ile yapıldı.
Uint8 önbellek kullanıldı. GT kutusuyle önceden kesilmiş parçalar ağ girdisi değildir.

İlk CPU pilotu: 160 eğitim +96 negatif, 40 validasyon, iki epok.
Epok/validasyon döngüsü 18.36 s, önbellek dahil
19.71 s. Pilot validasyon F1=0; başarı diye sunulmadı.
Sonlu kayıp ve uygun kaynak kullanımı sonrası tam eğitimler yeniden başlatıldı;
pilot ağırlığı başlangıç olarak kullanılmadı.

İki model de önceden belirlenen 18 epok; AdamW lr .001, weight decay .0001,
kosinüs lr programı. Yeni modelde sınıf katkıları eşitlenen focal, boyut/ofset
ve GIoU kaybı; Tiny'de özgün kayıp. Epok validasyon F1@score .2, eşitlikte
bütün-GT IoU ile seçildi. Test sonuçları bu seçime girmedi.

| Model | Parametre | Epok | Seçilen epok | Eğitim+validasyon döngüsü (s) | Önbellek dahil (s) |
|---|---:|---:|---:|---:|---:|
| LiteFPNCenter yeni | 22927 | 18 | 13 | 1723.99 | 1733.88 |
| Tiny aynı V2 ile yeniden eğitim | 77683 | 18 | 18 | 344.72 | 356.03 |

Süreler gerçek duvar saatidir, salt model hesaplama süresi değildir. Lite eğitiminde 10. epok 620.18 saniye ile belirgin uzadı; nedeni doğrulanmadı ve bu süre kayıttan çıkarılmadı.

## Yeni, önceden sabitlenmiş test

**80 yeni fiziksel aile x6 koşul =480 pozitif +40 negatif =520 görüntü**.
Kimlikler 10000–10079; negatifler 18000–18039. Eski 1000 fizik konfigürasyonuyla
kesişim yok. Yeni çizim yordamı önceki iki üreticiyi içe aktarmaz; Hershey metin,
ayrı sembol kodu ve mafsalın iki yanda bulunabildiği çizimler kullanır.
Bu, fiziksel aile ve çizim kodu açısından ayrıdır; **aynı yazarın sentetik verisidir,
bağımsız dış kaynak gerçek çizim testi değildir**.

Gerçek 384x256 ve 256x160 gri giriş hash'lerinde eski eğitim/validasyonla tekrar 0.
Plan, veri ve kaynak özetleri eğitimden önce `preregistered_plan.json` ve
`data_protocol.json` ile sabitlendi. Yeni test dosyaları deney sonunda da aynı kaldı.

Koşullar: temiz, ±3.5 derece/JPEG tarama, düşük kontrast, gürültülü düşük ışık,
128x88'e indirgenip büyütülmüş düşük çözünürlük ve koyu arka plan. Negatifler boş
kağıt, yalnız kiriş, metin/ölçü ve ızgara. Ağır bozunumlarda sınıf insan için de
belirsizleşebilir; etiketler bozulma öncesi amaçlanan nesne kapsamını korur.
Koşullar model sonucuna göre zorlaştırılmadı veya değiştirilmedi.

Skor adayları [.1,.2,.35,.5,.65], OpenCV doluluk adayları [.55,.65,.75] yalnız
validasyonda seçildi. Yeni/Tiny skor eşikleri: **{'lite': 0.5, 'tiny': 0.35}**;
OpenCV doluluk: **0.55**. Seçimler yeni test tahmininden
önce `frozen_thresholds.json` içine yazıldı. Test sonucuyla eğitim/eşik ayarı yapılmadı.

## Sınıf bazlı ölçümler

| Yöntem | Sınıf | TP / FP / FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| LiteFPNCenter yeni | pin_support | 308 / 2 / 172 | 0.9935 | 0.6417 | 0.7797 |
| LiteFPNCenter yeni | roller_support | 445 / 100 / 35 | 0.8165 | 0.9271 | 0.8683 |
| LiteFPNCenter yeni | point_load | 795 / 2 / 165 | 0.9975 | 0.8281 | 0.9050 |
| Tiny aynı V2 ile yeniden eğitim | pin_support | 436 / 19 / 44 | 0.9582 | 0.9083 | 0.9326 |
| Tiny aynı V2 ile yeniden eğitim | roller_support | 418 / 67 / 62 | 0.8619 | 0.8708 | 0.8663 |
| Tiny aynı V2 ile yeniden eğitim | point_load | 809 / 12 / 151 | 0.9854 | 0.8427 | 0.9085 |
| Eski Tiny donmuş ağırlık | pin_support | 99 / 146 / 381 | 0.4041 | 0.2062 | 0.2731 |
| Eski Tiny donmuş ağırlık | roller_support | 13 / 92 / 467 | 0.1238 | 0.0271 | 0.0444 |
| Eski Tiny donmuş ağırlık | point_load | 522 / 88 / 438 | 0.8557 | 0.5437 | 0.6650 |
| OpenCV değişmemiş yöntem | pin_support | 25 / 35 / 455 | 0.4167 | 0.0521 | 0.0926 |
| OpenCV değişmemiş yöntem | roller_support | 2 / 2 / 478 | 0.5000 | 0.0042 | 0.0083 |
| OpenCV değişmemiş yöntem | point_load | 365 / 0 / 595 | 1.0000 | 0.3802 | 0.5509 |

## Koşullar ve negatif görüntüler

Yeni model:

| Koşul | Görüntü | Precision | Recall | F1 | Roller FN |
|---|---:|---:|---:|---:|---:|
| affine_scan | 80 | 0.9745 | 0.9563 | 0.9653 | 1 |
| clean | 80 | 0.9792 | 0.8844 | 0.9294 | 3 |
| dark_background | 80 | 0.8440 | 0.5750 | 0.6840 | 18 |
| low_contrast | 80 | 0.8679 | 0.7594 | 0.8100 | 6 |
| low_resolution | 80 | 0.9480 | 0.7969 | 0.8659 | 5 |
| noisy_low_light | 80 | 0.9823 | 0.8656 | 0.9203 | 2 |

| Yöntem | Tam doğru pozitif görüntü oranı | 40 negatifte yanlış alarm oranı | F1 @ IoU .75 |
|---|---:|---:|---:|
| LiteFPNCenter yeni | 0.4271 | 0.0000 | 0.5582 |
| Tiny aynı V2 ile yeniden eğitim | 0.6667 | 0.0000 | 0.4455 |
| Eski Tiny donmuş ağırlık | 0.0229 | 0.0000 | 0.0917 |
| OpenCV değişmemiş yöntem | 0.0000 | 0.0000 | 0.3184 |

TP IoU yalnız doğru eşleşmeleri kapsadığı için ayrıca kaçırmaları sıfır sayan
bütün-GT IoU verildi. Doğru negatifler P/R/F1'i doğrudan yükseltmez; negatif
FP'leri toplam FP sayısına eklenir. Skorlar kalibre edilmiş güven olasılığı değildir.

## Hareketli mesnet FN ve hata görselleri

Yeni modelde **35 roller FN** kaydedildi:

| Tanılama | Sayı |
|---|---:|
| below_score_threshold | 29 |
| missed | 6 |

below_score_threshold: düşük skorlu ham doğru-sınıf kutusunda IoU>=.5;
class_confusion: farklı sınıfta IoU>=.5; localization: aynı sınıfta IoU .1–.5;
missed: kalanlar; .05 altı ham kutular saklanmadığından çok düşük skor da bu gruba girebilir. Bunlar kutu/score tanılamasıdır, nedensellik kanıtı değildir.
`evaluation/roller_false_negatives.json` Lite kayıtlarını, `roller_false_negatives_tiny.json` aynı biçimde Tiny kayıtlarını içerir. Bu incelemeden
sonra model/eşik yeniden ayarlanmadı.

**275 hatalı pozitif görüntüden 20 tanesi**,
sabit veri sırasındaki ilk örnekler olarak çizildi. Yeşil GT, kırmızı tahmin.
`evaluation/failures/` ayrı PNG; `failure_contact_sheet.png` toplu görünüm;
`failure_selection.json` seçilen dosyalar ve TP/FP/FN değerleridir.

## Çıktılar, kullanım ve testler

`lite/best.pt`, `tiny/best.pt`: yeni ağırlıklar. `history.json`, `metadata.json`:
gerçek epok/kayıp/süre ve checkpoint özetleri. Eski ağırlıklar korunmuştur.
`evaluation/predictions_original_pixels.json`: bütün yöntem ve görüntülerde
class_id, score ve orijinal görüntü koordinatında [x0,y0,x1,y1]. Sınıf kimlikleri 0=mafsal, 1=hareketli mesnet, 2=kuvvet oku.
`evaluation/detections.csv`: aynı piksel koordinatlarının tablo biçimi. Kaydedilmiş kutulardan bütün yöntemlerin P/R/F1 ve IoU değerleri yeniden hesaplanıp eşleşti; model tekrar test edilmedi.
`raw_predictions.json`: Lite/Tiny için .05 alt sınırından itibaren ham kutular.
`metrics.json`, `per_image_metrics.json`: toplu ve görüntü başına sonuçlar.

```powershell
python train_detector_v3.py prepare
python train_detector_v3.py pilot
python train_detector_v3.py train-lite
python train_detector_v3.py train-tiny
python train_detector_v3.py evaluate
python detect_trained_symbols.py --model tiny --run experiments/detector_v3_20261108_01 --image yol/resim.png --out work/yeni_tespit.json
```

Mevcut aşamaların üzerine yazılmaz; tekrar için yeni run ve plan gerekir.
Çıkarım yalnız görüntü alır; CSV/anotasyon okumaz. Checkpoint ve eşik protokolü
hash ile eşleşir. OCR uygulanmadı, RA/RB boş ve review_required=true kalır.
Yeni çıkarım komutu ayrıdır; mevcut masaüstü sembol demosu eski giriş noktasıdır.
`detect_trained_symbols.py --model lite` veya `--model tiny` iki bitmiş adayı açıkça
seçtirir; varsayılan yöntem seçimi yapmaz. Bu dışa aktarma giriş noktası testten
sonra eklendi; model, ön işleme ve eşikler değiştirilmedi. İki yöntemde de GT anotasyon/CSV
bulunmayan klasörden gerçek CLI çıkarımı yapılıp kilitli toplu çıkarımla kutu
IoU>.999 uyumu doğrulandı (`inference_image_only/verification.json`).

**62 otomatik test BAŞARILI.** Yeni sekiz test: sınıfa özel kutu dönüşümü,
gradient/boş görüntü kaybı, etiketsiz çıkarım, artırma tohum/kutu sınırları,
IoU/sınıf karışıklığı/negatif sayımı, yeni test aile/profilleri, validasyonda
artırma olmaması ve eşlenik bootstrap eşitliği. Önceki 54 test de geçti.
JUnit: `final_tests.xml`; tek tek durumlar: `test_results.json`.

| Yöntem | I/O dahil test çıkarımı (s) | Görüntü başına (ms) |
|---|---:|---:|
| LiteFPNCenter yeni | 7.16 | 13.76 |
| Tiny aynı V2 ile yeniden eğitim | 3.61 | 6.94 |
| Eski Tiny donmuş ağırlık | 3.67 | 7.05 |
| OpenCV değişmemiş yöntem | 3.90 | 7.50 |

Farklı giriş çözünürlükleri ve işlem havuzları nedeniyle bu süreler saf FLOP
veya adil donanım FPS karşılaştırması sayılmaz.

## Sınırlılıklar

- Sentetik, yatay/az döndürülmüş iki mesnetli ve iki yüklü kiriş alanı. Gerçek
  çizim/fotoğraf, CAD, el yazısı veya başka mesnet/yük türleri yok.
- Yeni aile/kod ayrılığı gerçek dış kaynak genellemesi değildir. Tek eğitim tohumu;
  artırmasız/eşit çözünürlüklü ablasyon yapılmadı. Fark tek bileşene atfedilemez.
- Validasyon temiz V2 pozitifleridir. Negatif/bozunum dağılımını tam temsil etmez;
  güven kalibrasyonu veya güvenli otomatik kabul politikası doğrulanmadı.
- Ağır düşük çözünürlük/ışık roller dairelerini görünmez kılabilir; amaçlanan GT
  kutusu korunur. Bu stres koşullarının başarısı insan belirsizliğini de içerir.
- OCR, yük/birim okuma, eşleştirme ve görüntüden statik çözüm geliştirilmedi.
  Gerçek yapı tasarımı veya güvenlik kararı için kullanılamaz.
- Linux/macOS/GPU çalıştırılmadı; CPU/Windows ortamı ölçüldü.

Sonraki geliştirme bu testte ayar yapmak olmamalıdır; yeni eğitim/validasyon ve
ayrı, önceden kilitli gerçek çizim testiyle yeni deney sürümü açılmalıdır.
