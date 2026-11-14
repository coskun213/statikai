# StatikAI — Gerçek pilot bilgisayar deneyi (08 Kasım 2026)

## Veri ve problem

- **40 benzersiz** temel, iki mesnetli ve iki düşey tekil yüklü kiriş problemi.
- Her problemden **5** görsel: 4 fiziksel olarak eşdeğer ve 1 yük konumu değiştirilmiş. Toplam **200** PNG.
- Tüm fiziksel konfigürasyonlarda tekrar kontrolü: 40 özgün temel + 40 farklı fiziksel müdahale; konfigürasyonlar eğitim/test arasında yinelenmez.
- Referans tepkiler `RA = P1 + P2 - RB`, `RB = (P1*x1 + P2*x2) / L` ile elde edilmiş ve otomatik testle doğrulanmıştır.
- Eğitim/validasyon/test bölmesi **temel problem kimliğine göre**: 28/8/4 problem; 140/40/20 diyagram.

## Sınırlı pilotin gerçek görevi

Önceden yerleri **gerçek anotasyon dosyasıyla** bilinen kuvvet oku, sabit mafsallı mesnet, hareketli mesnet ve arka plan parçaları 48x48 görüntülere çevrildi. Basit üç katmanlı CNN, bunları 4 sınıfta ayırmak üzere CPU'da **gerçekten** eğitildi. Bu bir nesne tespit modeli veya statik çözen model değildir. Sınıflandırıcı nesnenin diyagramdaki konumunu kendi başına bulamaz.

- Eğitim görüntü parçası: **980** (28 temel problem)
- Doğrulama görüntü parçası: **280** (8 temel problem)
- Test görüntü parçası: **140** (4 temel problem)
- Tohum: `2209`.
- Eğitim: 5 epok; en yüksek doğrulama macro-F1 değerindeki kontrol noktası seçildi.
- 4 otomatik test: **başarılı**.

## Gerçek test sonuçları

| Koşul | Doğruluk (accuracy) | Macro-F1 |
|---|---:|---:|
| Normal sentetik sembol kırpımı | 1,0000 | 1,0000 |
| Gri tonlamalı | 1,0000 | 1,0000 |
| Düşük ışık (parlaklık 0,38) | 0,1429 | 0,1000 |
| Bulanıklık (Gaussian sigma=2) | 0,4571 | 0,2364 |
| Düşük kontrast (çarpan 0,45) | 0,4286 | 0,1531 |

Bu koşullar test verisi üzerinde denenmiştir; testten sonra model yeniden eğitilmemiştir. Ayrıntılı JSON ve CSV: `kod/pilot_results/`.

## Bilimsel sınırlılıklar / yanlış yorumlar

1. **%100 yalnızca küçük, kolay ve aynı veri üreticisinden alınan kesilmiş görüntüler için geçerli.** Gerçek fotoğraf/teknik çizim başarısı kanıtlanmadı.
2. Yama konumu anotasyonla sağlandı; bu nedenle tam diyagramda nesne arama başarısı ölçülmedi.
3. OCR ile kuvvet ve mesafe okuma, sembol–metin eşleştirme, mesnet tepkisini görüntüden otomatik hesaplama **henüz yapılmadı**.
4. Test toplamda 4 temel problemden geldiğinden belirsizlik büyüktür; genişletilmiş ve farklı çizim üreten test şarttır.
5. Arka plan yamaları örnekleme tekniği nedeniyle diğerlerinden kolay ayırt edilebilir; sonraki deneyde zor negatif örnekler eklenmelidir.
6. Fiziksel denge denetleyicisini yer gerçekleriyle test etmek, kendi başına görsel modeli doğrulamak anlamına gelmez.

## Araştırmaya etkisi

Başvuru metninde 'görsel koşulların hesap güvenilirliğine etkisi' hipotezini gerekçelendirir; fakat yüksek doğruluk garantisi vermez. Daha sonra tam çözüm başarımı, OCR doğruluğu, eşdeğerlik ve fiziksel müdahale deneyleri planlıdır.
