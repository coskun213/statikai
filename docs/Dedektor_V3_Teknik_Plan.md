# StatikAI V3 nesne tespiti — önceden tanımlı deney

Deney planı `experiments/detector_v3_20261108_01/preregistered_plan.json` içindedir.
Bu dosya eğitimden ve yeni test tahminlerinden önce yazıldı. Veri/çizim/kod özetleri
`data_protocol.json` içinde sabitlendi. Eski test verisine göre yeni eşik veya
mimari seçimi yapılmaz. Gerçek sonuçlar ayrıca raporlanır.

## Mimari seçimi

LiteFPNCenter-v1: 384x256 gri tam görüntü, 22.927 parametre. Depthwise/pointwise
katmanlarla hafif kodlayıcı; stride 16/8/4 özelliklerini yanal ve yukarı bağlantılarla
birleştiren FPN; stride 4 merkez ısı haritaları ve sınıfa özel kutu/ofset regresyonu.
Sınıflar: mafsallı mesnet, hareketli mesnet, tekil kuvvet oku. Çıktı orijinal görüntü
piksel kutularıdır. OCR veya RA/RB hesabı yapılmaz.

Bu özel ağ MobileNet, FPN ve Objects as Points fikirlerinden yararlanır;
resmi MobileNet/CenterNet uygulaması veya önceden eğitilmiş model değildir.
MobileNet'teki depthwise ayrıştırma hesap yükünü azaltmak için, FPN küçük sembol
ayrıntılarını daha derin bağlamla birleştirmek için seçildi. Sınıfa özel kutular
mesnet ve uzun kuvvet oklarının farklı geometrilerine izin verir. Bunlar tasarım
gerekçesidir; başarım artışı gerçek testle değerlendirilmelidir.

Ön eğitimli ağırlık kullanılmaz. Üç sınıflı dar çizim alanı ve küçük özel ağ için
kendi verimizle sıfırdan eğitim yapılır. Böylece transfer kaynak sürümü/alanı
karışmadan CPU denemesi yapılabilir. Transfer learning üstünlüğü denenmiş değildir.
Yeni üçüncü taraf bağımlılık yoktur; mevcut torch, NumPy, Pillow ve OpenCV kullanılır.

## Veriler ve karşılaştırma

Eğitim: V2'nin 350 ailesinden 1750 görüntü ve 96 eğitim negatifi.
Validasyon: V2'nin farklı 100 ailesinden 500 görüntü. Eski 50 test ailesi, eğitim,
validasyon seçimi ve yeni test skoruna dahil edilmez.

Yeni test: ayrı çizim kodundan 80 yeni fiziksel aile x 6 koşul + 40 negatif,
toplam 520 görüntü. Fiziksel konfigürasyonlar eski kaynakla tekrar etmez.
OpenCV Hershey yazı, farklı sembol çizim yordamları ve mafsalın iki yanda
bulunabildiği şemalar kullanılır. Koşullar temiz, eğik/sıkıştırılmış tarama,
düşük kontrast, gürültülü düşük ışık, düşük çözünürlük ve koyu arka plandır.
Bu veri aynı proje yazarı tarafından sentetik üretilmiştir; dış kaynak gerçek
çizim genellemesi değildir. Düşük çözünürlük/ışıkta semboller belirsizleşebilir;
etiketler amaçlanan bozulma öncesi nesne kapsamını korur.

Karşılaştırmalar: yeni ağ; aynı V2 verisi, artırma ve eğitim programıyla eski
TinyDetector mimarisinin yeni eğitimi; değişmemiş klasik OpenCV; ayrıca orijinal
TinyDetector ağırlığının donmuş hali. Orijinal ağırlık başka veri/etiket tanımıyla
eğitildiğinden mimari karşılaştırması için yeniden eğitilen Tiny sürümü esastır.
Yeni ve Tiny giriş çözünürlükleri/parametre sayıları farklıdır; mimarinin tek başına
nedensel üstünlüğü iddia edilemez.

## Eğitim ve seçim

Önce 160 eğitim/40 validasyon görüntüsü ve iki epok CPU denemesi. Kaynaklar
uygunsa 18 epok tam eğitim, batch 12, CPU'da iki iş parçacığı. Modeller sırayla
çalıştırılır. AdamW lr=0.001, weight decay=0.0001, kosinüs lr programı.
Yeni ağda sınıfları eşit katkılayan focal heatmap, log-boyut/ofset ve GIoU kaybı;
Tiny'de özgün kayıp kullanılır. Değerlendirmede sınıf farkı yaratacak ağırlık
eski test skorlarına göre ayarlanmaz.

Yalnız eğitimde: yatay çevirme, ±5° küçük dönüş, ölçek/öteleme, parlaklık,
kontrast, gamma, hafif bulanıklık/gürültü ve %8 görüntü tersleme. Kutu köşeleri
dönüştürülür; aşırı kırpılan örneklerde dönüşüm reddedilir. Yatay çevirme yazıyı
da ters çevirir; bu, OCR eğitimi değil nesne tespit artırmasıdır. Validasyon ve
yeni test sabittir; test bozunumları bir kez önceden oluşturulur.

Epok: validasyonda score=0.2 ile en yüksek F1; eşitlikte tüm-GT IoU, sonra ilk epok.
Skor eşiği yalnız validasyonda [0.1,0.2,0.35,0.5,0.65] arasından seçilir.
OpenCV doluluk eşiği yalnız validasyonda [0.55,0.65,0.75] arasından seçilir.
Bunlar test tahmini başlamadan ayrı frozen_thresholds.json içine yazılır.

## Ölçümler ve hata incelemesi

Doğru sınıf ve IoU>=0.5 ile skor sıralı bire bir eşleştirme; ayrıca IoU>=0.75.
Mikro ve sınıf bazlı precision/recall/F1. IoU iki ayrı payda ile verilir:
doğru eşleşmiş TP'lerde ortalama IoU ve her GT için en iyi aynı-sınıf IoU
(hiç tahmin yoksa 0). Negatif görüntülerde yanlış alarm oranı ayrıca verilir.
Önceden belirlenen koşullar ayrı raporlanır. 1000 aile bazlı eşlenik bootstrap;
aynı temel problemin altı görseli bağımsız problemler gibi örneklenmez.

Yeni modeldeki hareketli mesnet FN'leri düşük skor, yanlış sınıf, lokalizasyon ve
tam kaçırma olarak incelenir. Yanlış örnekler yeni ayar için kullanılmaz.
Yeni modelin hatalı ilk 20 pozitif görüntüsü sabit veri sırasıyla görselleştirilir;
hata sayısı 20'den azsa sayı dürüstçe raporlanır. Çizim/etiketler model sonucu
görüldükten sonra değiştirilmez. Tek eğitim tohumu ve sentetik kaynak sınırları korunur.

## Birincil kaynaklar

- [MobileNets](https://arxiv.org/abs/1704.04861)
- [Feature Pyramid Networks](https://arxiv.org/abs/1612.03144)
- [Objects as Points](https://arxiv.org/abs/1904.07850)


Donanım ek doğrulaması: RTX 4060 Laptop GPU mevcut. İlk CUDA=false kaydı kurulu
PyTorch +cpu ortamını belirtir; fiziksel GPU yokluğu anlamına gelmez. Önceden
sabitlenmiş bu karşılaştırma CPU ortamında yürütülür, GPU hızlandırması denenmedi.
