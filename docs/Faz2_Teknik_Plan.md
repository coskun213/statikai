# Faz 2 — Tam diyagramda sembol tespiti için teknik plan

## Kapsam ve bitiş ölçütü

Yatay, iki basit mesnetli, iki aşağı yönlü tekil yüklü sentetik kirişlerin tam
PNG görüntüsünden üç sembol sınıfı için kutu üretilecek: mafsallı mesnet,
hareketli mesnet, kuvvet oku. Çıkarım fonksiyonu yalnızca görüntü alacak;
etiket, problem parametresi veya gerçek nesne kutusu almayacak.

Bu aşamada OCR, sayısal alan çıkarma, sembol–metin eşleştirme ve görüntüden
RA/RB hesabı uygulanmayacak. Tanılama raporunda bu alanlar `null` ve
`not_implemented` olacak. Sonraki fazlar bu prototiple tamamlanmış sayılmaz.

## Ön koşullar ve veri

Faz 0 testleri ve veri denetimi geçmeden Faz 1; Faz 1 testleri ve genişletilmiş
veri QA raporu geçmeden Faz 2 deneyleri başlamaz.

500 problem, her problem için dört eşdeğer ve bir fiziksel müdahale görüntüsü:
2500 PNG. Müdahale yalnızca ilk yükün konumunu değiştirir; referanslar yeniden
hesaplanır. Problem ID modulo 10 ile 350/100/50 aile train/val/test ayrılır.
Tüm eşdeğer ve müdahale varyantları aynı ailede kalır. Fiziksel parametre ve
dosya özeti tekrarı, analitik referans ve kutu sınırları denetlenir.

A stili eğitim/validasyonda kullanılır: 1400/400 görüntü. B stilinin testteki
50 görüntüsü, eğitimde kullanılmayan gösterim koşuludur. B de bizim sentetik
çizim kodumuzdan gelir; bağımsız dış kaynak veya gerçek fotoğraf değildir.
Test A 200 görüntü, test B 50 görüntü; yöntemler aynı 250 görüntüde kıyaslanır.

## İki yöntem

1. **OpenCV temel yöntemi:** eşikleme, uzun yatay çizgiden kiriş adayını bulma,
   bağlı bileşenlerle düşey ok adayları ve mesnet şekillerini ayırma. Sabit
   piksel konumları yerine görüntüden bulunan kirişe göre bağıl ölçüler.
2. **Küçük öğrenilmiş dedektör:** PyTorch ile sıfırdan, CPU üzerinde eğitilen
   merkez ısı haritası ve kutu boyutu/ofseti tahmin eden küçük bir ağ.
   Tam görüntü girişi; önceden eğitilmiş ağırlık ve oracle kırpımı kullanılmaz.

`opencv-python-headless` yeni bağımlılığı birinci yöntemin eşikleme ve bağlı
bileşen işlemleri içindir; GUI bağımlılığı taşımaması için headless seçilir.

## Seçim ve ölçüm protokolü

Rastgelelik tohumu, paket sürümleri ve görüntü boyutu kaydedilir. Epok ve karar
eşikleri yalnızca A-validasyon grubunda seçilir. Seçilen checkpoint, eşikler
ve veri manifestinin SHA-256 özetleri nihai testten önce dondurulur.

IoU >= 0.50 ve doğru sınıf ile bire bir eşleştirme: precision, recall, F1,
sınıf bazında sayımlar; tüm nesneleri doğru bulunan görüntü oranı. A/B ayrı
raporlanır. Boş/sembolsüz görüntülerde yanlış pozitifler ayrıca ölçülür.
Aile bazında bootstrap belirsizlik aralığı verilir; görüntüler bağımsız
problemlermiş gibi sayılmaz. Yakalanamayan nesneler ve yanlış kutular saklanır.

İlk on test ailesi önceden tanımlı sırayla tanılama raporuna alınır;
başarılı örnekler seçilmez. Test sonuçlarına bakılarak aynı test için yeniden
ayar yapılmaz. Başarı düşükse olduğu gibi raporlanır ve yeni deney sürümü
farklı araştırma koşulu olarak planlanır.

## Sonraki aşamalar

Faz 3: OCR ve geometrik eşleştirme, sayısal alan bazında ayrı doğrulama.
Faz 4: yalnızca doğrulanmış girişlerden statik hesap ve belirsiz girişleri ret.
Faz 5: bu modüller hazır olduğunda tam çözüm kıyaslaması ve dış çizim testi.
Faz 6: önceki modüller doğrulandıktan sonra basit arayüz.

Mevcut analitik yardımcı fonksiyon, görsel çözümün uygulanmış olduğu anlamına
gelmez. Dengeyi yanlış okunmuş girdiler üzerinde sağlamak doğruluk kanıtı değildir.
