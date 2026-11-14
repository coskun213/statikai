# StatikAI — ölçülendirilmiş sentetik veri seti V2

Bu sürüm 2B görüntüden statik çözüm araştırması için veri hazırlığıdır.
Eski `dataset_extended/` değiştirilmez. `dataset_dimensions_v2/` aynı temel
problem kimliklerini ve aynı eğitim/doğrulama/test atamalarını yeni çizimlerle taşır.
Eski 50 test ailesi yeni eğitim verisine alınmaz. Yeni çizimler, bağımsız yeni
fiziksel problemler veya dış kaynaktan gerçek mühendislik çizimleri değildir.

## Üretme ve denetleme

Proje kökünde, mevcut sanal ortamın Python'u ile:

```powershell
python generate_extended_dataset.py --version dimensions-v2 --source dataset_extended --out dataset_dimensions_v2 --seed 20261109
python audit_dataset.py --dataset dataset_dimensions_v2 --out work/v2_qa_yeni.json
python -m pytest -q
```

V2 üreticisi var olan çıktı klasörünü kabul etmez. Tekrarlamak için `--out`
ile yeni bir klasör seçin. Kaynak veri önce denetlenir; manifest yalnız bütün
üretim bittiğinde yazılır. Font dosyaları ve Pillow sürümü değişirse aynı tohum
aynı pikselleri garanti etmez; manifest gerçek font özetlerini ve sürümleri kaydeder.
Yeni pip bağımlılığı eklenmedi: Pillow ve NumPy kullanılır; testler pytest ister.

## Görsel tasarım

Alt taraftaki `L=... | x1=... | x2=...` metni kaldırıldı. Görsellerde
kuvvet okları, solda mafsal, sağda iki makaralı mesnet, ölçü yardımcı çizgileri,
iç ok/tik uçları ve etiketlerin yanındaki birimler vardır. Bütün nesneler aynı
mürekkep rengini kullanır; kuvvetleri ayrı renkle kodlayan sınıf kısayolu yoktur.
Dört font, üç çözünürlük, dört sembol stili, değişen kesit/sembol çizgi kalınlıkları
ve ondalık nokta/virgül düzenleri kullanılır. Gerçek sayılar raporda yer alır.

- `chain_total`: A–yük1, yük1–yük2, yük2–B segmentleri ve ayrıca toplam açıklık.
- `chain_only`: yalnız üç segment; L bu değerlerin toplamından, x2 ilk iki segmentten bulunur.
- `datum`: A referansından yük1, yük2 ve B'ye üç kademeli ölçü çizgisi.
- `mixed`: A–yük1, yük1–yük2 ve toplam açıklık farklı seviyelerde.

Kuvvetler kN veya N; uzunluklar m, cm veya mm olarak yazılır. CSV'deki bütün
fizik değerleri ise m ve kN'dir. 0–3 varyantları fiziksel eşdeğerdir; 4. varyantta
yalnız x1 değişir. 0 ve 4'te çizim/font/birim parametreleri aynı tutulur.

## Veri sözleşmesi

- `images/*.png`: yalnız görüntü girdileri. Hesap girdisi özeti veya RA/RB görüntüye yazılmaz.
- `labels/*.txt`: 0=mafsal, 1=hareketli mesnet, 2=tekil kuvvet için YOLO kutuları.
- `masks/*.png`: 0=arka plan, 1=mesnet A, 2=mesnet B, 3=yük1, 4=yük2 piksel maskeleri.
- `annotations/*.json`: metin kutuları/transkripsiyonları, birim ve SI değeri,
  hangi yüke/ölçüye ait oldukları, ölçü uç noktaları, çizim ve font parametreleri.
- `ground_truth.csv`: problem kimliği, grup, fizik girdileri, analitik RA/RB ve dosya yolları.
- `source_ground_truth.csv`: kaynaktaki CSV'nin değişmemiş kopyası; köken/grup doğrulaması için.
- `manifest.json`: sürüm, tohum, kaynak CSV/font/dosya SHA-256 özetleri ve sınırlılıklar.

CSV, metin transkripsiyonları ve maskeler eğitim/değerlendirme yer gerçekleridir;
görüntüden çıkarım sırasında hazır girdi olarak kullanılamaz. Özellikle RA/RB'yi
CSV'den alıp görüntüden tahminmiş gibi değerlendirmek geçersiz olur.

`style=D2` yeni sürümü belirtir. Eski `train_detector.py` yalnız style A'yı
seçtiğinden yeni veriyle doğrudan eğitim yapmaz. Yeni bir eğitim/değerlendirme
protokolü ayrıca sürümlenmelidir. Bu aşamada eski model yeniden eğitilmedi;
eski test eşikleri/sonuçları yeni veri için değiştirilmedi.

## Denetim kapsamı

Analitik tepkiler bağımsız Decimal denklemleriyle; birimler ve ölçü uçları fiziksel
konumlarla; YOLO kutuları gerçek sembol maskeleriyle karşılaştırılır. Kaydedilmiş
font bulunabiliyorsa her metin, transkripsiyonundan ayrı olarak rasterleştirilip
asıl görüntü pikselleriyle karşılaştırılır. Bu işlem OCR deneyi değildir.
Tam görüntülerin 256x160 gri girişleri ve sembollerin %22 paylı 48x48 RGB
kırpımları için de ayrımlar arası tam tekrar aranır. Kırpım tekrarları uyarı olarak
raporlanır; koşulsuz bağımsız kırpım sınıflandırma başarısı iddiasında bulunulmaz.

## Sınırlılıklar

Şemalar temiz, yatay ve ölçekli; yalnız iki aşağı yönlü tekil yük içerir.
Ölçekli çizimlerde piksel konum oranlarından yararlanma kısayolu hâlâ mümkündür.
Hazır parametre satırının kaldırılması, bütün görsel kısayolların giderildiğini
kanıtlamaz. Bağımsız gerçek çizimler, ölçek dışı şemalar, tarama/perspektif hataları,
el yazısı, başka mesnet/yük türleri ve belirsiz/eksik veriler bu sürümde yoktur.
Metin boyutlandırma ve sembol anlamı danışman/uzman incelemesi gerektirir;
herhangi bir çizim standardına tam uygunluk iddiası yoktur.

OCR ve görüntüden RA/RB çözümü henüz geliştirilmedi. Veri denetiminin geçmesi,
model tespit/okuma/hesap başarısının ölçüldüğü anlamına gelmez. Tam sonuçlar ve
örnekler `VERI_SETI_V2_RAPORU.md` dosyasındadır.
