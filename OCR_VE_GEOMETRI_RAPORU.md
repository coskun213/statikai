# StatikAI — OCR ve geometrik eşleştirme V1.1

Yeni bağımsız OCR modülü ve ölçü grafı eklendi. **Statik motoru ve 3B masaüstü
modülü değiştirilmedi.** Görüntüden RA/RB çözümü veya masaüstü OCR arayüzü yoktur.

## Gerçek test sonuçları

Yeni 50 fizik ailesi / 250 sentetik çizim; 100 fiziksel konfigürasyon, dört
ölçülendirme düzeni, dört font, üç çözünürlük. Hazır L/x1/x2 parametre satırı
yoktur. Sayı etiketlerinin paydası 1350; kuvvetlerin paydası 500.
Çıkarım yalnız görüntü ve korunmuş modellerle çalışır, referanslar sonradan ölçüm içindir.

| Ölçüm | Doğru / toplam | Oran |
|---|---:|---:|
| Tam metin (yalnız boşluk normalizasyonu) | 1838/1850 | %99.35 |
| Sayısal etiket + doğru SI değer | 1343/1350 | %99.48 |
| Doğru birim | 1343/1350 | %99.48 |
| Kuvvet–metin doğru ilişki, tüm kuvvetler | 494/500 | %98.80 |
| Doğru kuvvet değeri ve doğru ilişki | 494/500 | %98.80 |
| Beş girdinin tamamı doğru, uyarısız | 242/250 | %96.80 |
| Eksiksiz çıktı kapsaması | 242/250 | %96.80 |
| İncelemeye ayrılan | 8/250 | %3.20 |
| Kabul edildiği halde yanlış | 0/250 | %0.00 |

Tam problem oranı için aile düzeyinde 5.000 tekrar bootstrap %95 aralığı:
%94.00–%99.20. Bu aralık gerçek dünyaya genelleme kanıtı değildir.
Kabul edilenler arasındaki doğruluk %100.00; sıfır gözlenen
hatalı kabul gelecekte hata olmayacağı anlamına gelmez.

Ham metin tespit precision (IoU≥0.30): %66.27;
recall: %99.73. IoU≥0.50 recall:
%66.16. OCR kutuları sıkı referans yazı kutularından
büyüktür; bu nedenle her iki eşik de açıkça raporlandı. Mesnet tarama çizgilerinin
rakam sanılması çok sayıda OCR yanlış pozitifine yol açtı; bu sonuçlar gizlenmedi.

Kuvvet/metin koşullu eşleştirme: 494/500
(%98.80). Koşullu payda yalnız hem okunabilir
etiketi hem IoU≥0.50 ile tespit edilmiş oku bulunan kuvvetlerdir. Ana tabloda
payda bütün 500 kuvvettir. Geometri/ilişki başarısı, karakter OCR başarısıyla aynı metrik değildir.

| Alan | Kullanılabilir kısmi çıktı | Doğru çıktı / tüm görüntüler |
|---|---:|---:|
| L_m | 244/250 | 244/250 |
| P1_kN | 247/250 | 247/250 |
| x1_m | 247/250 | 247/250 |
| P2_kN | 247/250 | 247/250 |
| x2_m | 244/250 | 243/250 |

| Ölçülendirme | Görüntü | Tam doğru | Oran |
|---|---:|---:|---:|
| chain_total | 100 | 96 | %96.00 |
| datum | 50 | 50 | %100.00 |
| chain_only | 50 | 47 | %94.00 |
| mixed | 50 | 49 | %98.00 |

| Font | Görüntü | Tam doğru | Oran |
|---|---:|---:|---:|
| times.ttf | 60 | 58 | %96.67 |
| calibri.ttf | 64 | 63 | %98.44 |
| arial.ttf | 65 | 65 | %100.00 |
| cour.ttf | 61 | 56 | %91.80 |

## Testlerin durumu ve kanıtları

| Kontrol | Durum | Gerçek sonuç / kanıt |
|---|---|---|
| Değişiklik öncesi python -m pytest -q | BAŞARILI | 62 passed in 61.04s; OCR V1 baseline_tests.log |
| İlk yeni birim/geometri testleri | BAŞARILI | 29 passed in 0.38s; OCR V1 ocr_unit_v1.log |
| İlk entegrasyon denemesi | BAŞARISIZ | RapidOCR enum parametresi TypeError; development_train_v1.log; kurulu API'ye göre düzeltildi |
| V1 bütün otomatik testler | BAŞARILI | 91 passed in 75.23s; V1 final_tests.log |
| V1 gerçek OCR güvenlik kontrolü | BAŞARISIZ | 5/6 geçti, yanlış ölçü birimi uyarısı eksik; eski summary.json korundu |
| V1.1 python -m pytest -q | BAŞARILI | 92 passed in 56.92s; final_tests.log |
| Her otomatik testin ayrı durumu | BAŞARILI | test_statuses.json: 92 test kimliği ve BAŞARILI |
| V1.1 gerçek OCR güvenlik kontrolü | BAŞARILI | 6/6; safety_diagnostics/summary.json |
| Doğrulama veri grubu | BAŞARILI | 50/50 çalıştırıldı, 44 tam doğru, 6 inceleme; validation/metrics.json |
| Yeni sabit son test ölçümü | BAŞARILI | 250/250 çalıştırıldı; test/metrics.json; bu testlerin tümünün doğru çıktığı anlamına gelmez |
| Her problemde tam çıkarım hedefi | BAŞARISIZ | 242/250; kalan 8 problem başarısız çıkarım/inceleme |
| JSON ve kaynak izlenebilirliği | BAŞARILI | 250 JSON; json_output_checks.json |
| pip check | BAŞARILI | No broken requirements found; pip_check.log |
| Korunan veri/ağırlık/sonuç ve motorlar | BAŞARILI | 16.551 dosya SHA-256 aynı; preservation_after.json |
| Windows x64 gerçek çalıştırma | BAŞARILI | Python 3.13.12; ONNX CPU ve PyTorch CPU |
| macOS ve Linux gerçek çalıştırma | ÇALIŞTIRILAMADI | Bu makinede bu işletim sistemleri yok; taşınabilirlik yalnız kod/bağımlılık incelemesi |
| Gerçek dış kaynak mühendislik çizimleri | ÇALIŞTIRILAMADI | Etiketli dış kaynak çizim testi hazırlanmadı |

V1.1 güvenlik senaryoları: silinmiş kuvvet metni, yanlış kuvvet birimi, çelişkili
toplam boy, silinmiş ölçüler, yanlış ölçü birimi ve fazladan kuvvet metni.
Her birinin gerçek PNG'si, tam OCR/dedektör JSON'u ve ayrı durumu kaydedildi.
Belirsiz bire bir eşleştirme ayrıca otomatik testte uyarı üretir.

## İlk sürüm ve güvenlik düzeltmesi

V1, V2'nin eski test grubunda 235/250 tam doğru sonuç
verdi. Ancak eğitim çizimi kopyasındaki `5242 kg` hatası ölçü etiketi bölgesi
filtresine takılıp göz ardı edildi. V1 sonuçları, başarısız güvenlik örneği,
kilitli protokol ve ilk kaynakların kopyası silinmedi.

V1.1 düzeltmesi yalnız bu eğitim kaynaklı güvenlik bulgusuna dayanır. Yüksek
güvenle okunan desteklenmeyen birim, sembolün içinde değilse ölçü bölgesi
sezgisel filtresinden bağımsız olarak inceleme ister. Ek regresyon testi eklendi.
Eski test ilerleme toplamlarının görülmesi ve karar amendment.json içinde
kaydedildi. Parametreler eski testte başarı artırmak için seçilmedi.

Güncel sürüm için seed=22091110 ile 50 yeni aile oluşturuldu. Eski V2 aileleri
ve V3 bağımsız testindeki fizik kayıtlarıyla birebir fiziksel örtüşme sıfır;
100 benzersiz fiziksel konfigürasyon var. Aile varyantları birlikte tutulur.
Bu veriyle eğitim yapılmadı. Önceki testler korunurken yeni son test verisi
üretiminden sonra kod/hash/eşikler kilitlendi; yeni test sonuçlarından ayar yapılmadı.

Ölçü/etiket referansları Decimal kuvvet ve moment denklemleriyle 250/250 doğrulandı.
Çizim üreticisi V2 ile aynıdır: bağımsız dış çizim veya yeni çizim stili diye sunulmaz.
Yeni test üretim kodu tools/generate_ocr_holdout.py, manifest ve plan ayrı kaydedildi.

## Uygulama ve kaynak gösterimi

RapidOCR 3.10.0 / ONNX Runtime 1.31.1, PP-OCRv6 small det+rec, CPU kullanıldı.
OCR önceden eğitilmiş üçüncü taraf modellerdir; kendi verilerimizle OCR eğitimi
yapılmadı. Modeller indirildikten sonra görüntüler yerelde okunur.
[Resmî RapidOCR kaynak/kullanım](https://github.com/RapidAI/RapidOCR),
[kurulum belgesi](https://rapidai.github.io/RapidOCRDocs/main/en/install_usage/rapidocr/install/).
Model URL, SHA-256, lisans ve atıflar docs/ocr_third_party/ içinde.

Dedektör korunmuş V3 yeniden eğitilmiş TinyDetector-v1, eşik 0.35'tir.
Küçük model ya da diğer ağırlıklar bu görevde yeniden eğitilmedi veya değiştirilmedi.
Test çıkarım süresi 144.39 s / 250 görüntü
(ortalama 0.578 s/görüntü; dosya/JSON/ölçüm ve görselleştirme dahil,
başlangıç model kurulum süresi hariç). Bu bir saf model FPS ölçümü değildir.

Sayı, açık birim, ham metin, kaynak kutusu ve OCR skoru korunur. `N→kN`,
`cm/mm→m` dönüşümleri uygulanır. Sayı/birim ayrı OCR kutularındaysa yalnız
tekil komşu çift birleştirilir. Rakam veya birim düzeltmesi yapılmaz.
Kuvvet/metin ataması birden çok şekilde mümkünse en yakın olanı keyfî seçmez.

Ölçü çizgileri ve uzatma çizgileri sembol düğümlerine bağlanır. Uzunluk ve yük
konumları okunan ölçülerden graf toplamıyla bulunur; piksel/metre ölçeği kullanılmaz.
Bağlantısız, çelişkili veya belirsiz girdiler incelemeye ayrılır. Tam çıktı yoksa
extracted_inputs null; kaynaklı kısmi okumalar kaynaklarıyla ayrıca görünür.

Yeni kullanım ve JSON alanları: docs/OCR_ve_Geometrik_Eslestirme.md.
Örnek giriş: dataset_dimensions_v2/images/beam_0000_v0.png;
çıktı: experiments/ocr_v1_1_20261108_01/demo_train_0000_v0.json.
Gerçek okuma L=15.88 m, P1=17 kN, x1=5.242 m, P2=10 kN, x2=11.193 m.
Bu örnek eğitim görüntüsüdür; son test başarısı yerine kullanılmaz.

## Başarısız örnekler

8 gerçek başarısız çıkarımın tamamı case_scores.json'da; ilk
8 tanesinin görseli test/failures/ altında. Olmayan hata örneği
üretilmedi. Özet kolaj outputs/StatikAI_OCR_Hatalar.png. Kutular: mavi sembol,
yeşil kabul edilen sayı/birim, turuncu kullanılamayan OCR; mor ölçü bağlantıları.

| Görüntü | Düzen | İnceleme / başarısızlık nedeni |
|---|---|---|
| ocr_fresh_10013_v2.png | chain_only | missing_unit, incomplete_dimension_chain |
| ocr_fresh_10013_v3.png | mixed | missing_unit |
| ocr_fresh_10018_v2.png | chain_only | symbol_inventory |
| ocr_fresh_10028_v0.png | chain_total | symbol_inventory |
| ocr_fresh_10028_v4.png | chain_total | symbol_inventory |
| ocr_fresh_10038_v0.png | chain_total | missing_unit, missing_unit, incomplete_dimension_chain |
| ocr_fresh_10038_v4.png | chain_total | missing_unit |
| ocr_fresh_10045_v2.png | chain_only | missing_unit, missing_unit, incomplete_dimension_chain |


Kısmi sonuçlarda bir yanlış x2 gözlendi: `ocr_fresh_10013_v3.png` içinde gerçek
`5063 mm` etiketi OCR'de `5063` ve `3 mm` diye bölündü. Birimsiz `5063`
inceleme uyarısı üretti; kısmi graf 0.003 m yanlış kenarını kullanıp x2=3.496 m
verdi (doğru x2=8.556 m). `review_required=true` ve `extracted_inputs=null`
olduğu için bu problem tam kabul edilmedi. **İnceleme durumundaki kısmi alanlar
hesaba otomatik aktarılmamalıdır.** Testte görülen bu hata için parametre/kod
ayarı yapılmadı; sonraki bağımsız çalışmada ele alınmalıdır.

## Bilimsel sınırlılıklar ve kalan işler

- Testler aynı sentetik çizim üreticisindendir. Gerçek taramalar, el yazısı,
  fotoğraf perspektifi, eğik/çapraz etiketler ve dış mühendislik çizimleriyle doğrulanmadı.
- Yatay, solda mafsal/sağda hareketli mesnet ve iki aşağı yönlü tekil yük dar kapsamıdır.
  Ters mesnet, konsol, yayılı yük, moment, çok açıklık ve 3B görüntü okuma yoktur.
- Skorlar kalibre değildir. Yanlış OCR rakamı/birimi yüksek güvenle ve tutarlı
  okunursa, özellikle yedek ölçüsüz zincirde hata fark edilmeyebilir.
- Tamamen tespit edilemeyen ek etiket/yanlış birim her durumda bulunamaz. Uyarı
  kontrollerinin örneklerde geçmesi bütün yanlış birimlerin yakalanmasını garanti etmez.
- IoU≥0.30 metin lokalizasyon eşiği sıkı kutu değerlendirmesi değildir; daha sıkı
  IoU≥0.50 sonuç da açıkça raporlanır. Ham OCR precision'ı yüksek değildir.
- Test setindeki incelemeler, girdilerin çoğu doğru olsa bile tam çıkarım başarısı
  sayılmadı. İnceleme uyarısı çıktının mühendislik açısından güvenli olduğunu kanıtlamaz.
- statikai/physics.py, frame3d.py, masaüstü ve eski veri/model/deneyler değişmedi.
  RA/RB üretilmez; sonraki aşamada doğrulanmış girdilerle ayrı entegrasyon gerekir.
