# StatikAI — görüntüden mesnet tepkilerine gerçek entegrasyon raporu

Mevcut analitik çözücü değiştirilmeden dedektör, OCR ve ölçü grafıyla uçtan
uca bağlandı. Eksik veya inceleme işaretli girdiler çözücüye verilmez.
Ayrı 2B görüntü yükleme penceresi ve komut satırı eklendi; eski 3B modülü korunur.

## Ana sonuç: 30 farklı fiziksel problem

Önceden planlanan `variant=0` çizimiyle, 30 farklı problemde:

| Sonuç | Problem |
|---|---:|
| Otomatik doğru | 27 |
| İnceleme gerekli, hesap durdu | 3 |
| Yanlış otomatik sonuç | 0 |
| Toplam | 30 |

Aynı problemlerin dört farklı ölçülendirme düzeniyle toplam 120 görüntüde
**110 doğru otomatik çözüm (%91.67),
10 inceleme (%8.33), 0 yanlış otomatik sonuç**
gözlendi. Bu 120 görüntü 120 ayrı fiziksel problem değildir. 30 problemin
20 tanesi bütün dört çiziminde doğru çözüldü.
Yeni son testten kod, eşik veya parametre seçilmedi.

Başarı, yalnız dengeyi değil, beş girdinin ve iki tepkinin bağımsız referansla
1e-6 toleransında eşleşmesini gerektirir. Yanlış girdilerle dengeli sonuç da
başarısızlık sayılır. Yayınlanan 110 çözümde maksimum mutlak tepki hatası
3.55e-15 kN; bu, aynı doğru girdilerle
analitik aritmetik karşılaştırmasıdır, bütün görüntüler için hata iddiası değildir.
İncelemelerde RA/RB JSON'da null ve çözücü not_run kaldı.

Sıfır gözlenen yanlış kabul, gelecekte yanlış okuma veya kapsam dışı diyagramın
kabul edilmeyeceğini kanıtlamaz. Test aynı sentetik V2 üreticisindendir;
gerçek mühendislik çizimi veya yapı güvenliği başarısı değildir.

## Yeni akış ve uygulama

1. Kullanıcı görüntü dosyasını seçer.
2. Korunmuş TinyDetector tam görüntüde sembolleri bulur.
3. Yerel RapidOCR sayı ve açık birimleri okur.
4. Korunmuş ölçü grafı gerçek konumları ölçü zincirlerinden çıkarır.
5. Yeni kapsam ve kaynak/girdi kontrolleri geçerse physics.reactions çağrılır.
6. Physics.residuals ile kuvvet ve moment dengesi denetlenir.
7. Aşamalar, kaynaklar, birimler, uyarılar, RA/RB ve denge artıkları JSON'a yazılır.

Windows'ta `StatikAI_2B_Baslat.cmd` → **Görüntü yükle** →
**Algıla → Oku → Doğrula → Hesapla**. Her analiz work/beam_pipeline altında
benzersiz JSON'a kaydedilir; başka yere kaydetme düğmesi vardır.
Eski StatikAI_Baslat.cmd 3B uygulamayı açmaya devam eder.

Terminalde proje klasöründe:

```powershell
python -m pip install -r requirements.txt -r requirements-ocr.txt
python solve_beam_image.py --image dataset_dimensions_v2/images/beam_0000_v0.png --out work/ilk_cozum.json
python statikai_beam_app.py
```

Bu makinede kullanılan Python, önceki paylaşılan sanal ortamın Scripts/python.exe
uygulamasıdır; genel python komutu WindowsApps takma adına bağlı olabilir.
Başlatıcı mevcut .statikai-python.txt yolunu kullanır, taşınan kurulumda .venv arar.
Tam yönerge ve JSON şeması docs/Uctan_Uca_Kiris_Kullanimi.md içindedir.

## Çözücünün doğruluğu ve sayısal kapılar

Physics.py kaynağı değiştirilmedi; önce/sonra SHA-256:
`5dd8a9e9a512ebd8a3ee459b848cfd59a1d01dc5bc51cd4c53322ae5b90142be`.

```
RA + RB = P1 + P2
RB * L = P1*x1 + P2*x2
```

İç hesap mevcut kararlı P*(x/L) ve math.fsum yolunu korur. Yeni entegrasyon:

- Tam beş sayısal, sonlu, pozitif ve doğru sıradaki girdiyi ister.
- Okunmuş N/kN, mm/cm/m birimlerini ham metinden yeniden kontrol eder.
- Her kuvvetin kaynak etiketini ve ölçü grafının konumlarla eşleşmesini sınar.
- Kısmi alanları, önceki sonuç dosyalarını veya referans CSV'yi hesap girdisi yapmaz.
- Bir mafsal, bir hareketli mesnet ve iki kuvvet dışında sembol sayısını reddeder.
- Ok başı yönü, iki yana açılan mesnet üçgeni, tekerlek halkaları ve yük
  bölgesindeki açıklanmayan çizgiler için ek piksel kontrolleri uygular.
- Kapsam/okuma belirsizse, yanlış birim veya ölçü çelişkisi varsa hesap durur.
- Kuvvet toleransı 1e-9 + 1e-10*ölçek kN; moment toleransı
  1e-8 + 1e-10*ölçek kN m. Artıklar JSON'da açıkça kaydedilir.
- Denge kontrolü başarısızsa hesaplanan tepkiler yayınlanmaz.

Mevcut kapsam yatay, solda mafsal/sağda hareketli mesnet ve iki aşağı yönlü tekil
yüktür. Yeni kontroller evrensel yük/mesnet sınıflandırıcısı değildir; bütün
ankastre, yayılı yük, küçük eğimli kuvvet veya alışılmadık sembollerin her
çizimde tanınacağı garanti edilmez. Böyle çizimlerde otomatik kullanım uygun değildir.

## Aşama bazında gerçek ölçümler

| Ölçüm | Gerçek sonuç |
|---|---:|
| Sembol tespiti TP / FP / FN (IoU≥0.50) | 480 / 1 / 0 |
| Sembol precision / recall / F1 | %99.79 / %100.00 / %99.90 |
| Doğru tespitlerde ortalama IoU | 0.8215 |
| OCR tam metin, yalnız boşluk normalizasyonu | 862/870 (%99.08) |
| OCR sayı + birim doğru SI değeri | 623/630 (%98.89) |
| Ham OCR metin tespit precision (IoU≥0.30) | %65.44 |
| Ham OCR metin tespit recall (IoU≥0.30 / ≥0.50) | %99.89 / %67.36 |
| Kuvvet–metin doğru eşleştirme | 238/240 (%99.17) |
| Kapsam kapısından önce tüm girdiler doğru ve eksiksiz | 113/120 (%94.17) |
| Bütün kapılardan sonra doğru statik çözüm | 110/120 (%91.67) |

OCR ham precision'ı düşüktür; taramalar/rakam benzeri semboller metin sanılır.
Metin referans kutuları sıkı, OCR kutuları geniş olduğundan IoU 0.30 yanında
0.50 sonucu da verilir. Girdi çıkarımı ile uçtan uca çözüm başarısı ayrıdır.
Bu model metrikleri önceki farklı test setleriyle doğrudan karşılaştırılmaz.

İç kapı durumları (bunlar referans doğruluk metrikleri değildir):

| Aşama | Geçti | İnceleme | Çalışmadı |
|---|---:|---:|---:|
| image | 120 | 0 | 0 |
| detection | 119 | 1 | 0 |
| ocr | 113 | 7 | 0 |
| geometry | 113 | 7 | 0 |
| scope | 115 | 5 | 0 |
| validation | 110 | 10 | 0 |
| statics | 110 | 0 | 10 |
| equilibrium | 110 | 0 | 10 |

Kapsam kapısı 5 görüntüyü reddetti.
Kapsam/okuma reddi çakışabilir. Doğru OCR/ölçü çıkarımı olan üç çizim de
tekerlek kanıtı yeterince doğrulanamadığı için hesaplanmadı; bu gereksiz
retler başarıya dahil edilmedi ve eşikler testte bunları gidermek için değiştirilmedi.

## Her farklı problemin sonucu (önceden tanımlı variant 0)

Birim kN. Tire, çözücü çağrılmadığını gösterir; referans değerler yalnız değerlendirme içindir.

| Problem | Sonuç | RA çıktı | RB çıktı | RA referans | RB referans |
|---|---|---:|---:|---:|---:|
| 20000 | Otomatik doğru | 28.345047 | 19.654953 | 28.345047 | 19.654953 |
| 20001 | Otomatik doğru | 15.181488 | 15.818512 | 15.181488 | 15.818512 |
| 20002 | Otomatik doğru | 10.839002 | 13.160998 | 10.839002 | 13.160998 |
| 20003 | Otomatik doğru | 8.101922 | 9.898078 | 8.101922 | 9.898078 |
| 20004 | Otomatik doğru | 27.783579 | 25.216421 | 27.783579 | 25.216421 |
| 20005 | Otomatik doğru | 22.635901 | 15.364099 | 22.635901 | 15.364099 |
| 20006 | Otomatik doğru | 13.998071 | 20.001929 | 13.998071 | 20.001929 |
| 20007 | Otomatik doğru | 17.908619 | 19.091381 | 17.908619 | 19.091381 |
| 20008 | Otomatik doğru | 25.682434 | 20.317566 | 25.682434 | 20.317566 |
| 20009 | İnceleme gerekli | — | — | 26.770017 | 27.229983 |
| 20010 | Otomatik doğru | 24.053204 | 25.946796 | 24.053204 | 25.946796 |
| 20011 | Otomatik doğru | 23.293426 | 23.706574 | 23.293426 | 23.706574 |
| 20012 | Otomatik doğru | 21.050425 | 18.949575 | 21.050425 | 18.949575 |
| 20013 | Otomatik doğru | 9.928531 | 20.071469 | 9.928531 | 20.071469 |
| 20014 | İnceleme gerekli | — | — | 17.988024 | 18.011976 |
| 20015 | İnceleme gerekli | — | — | 22.353696 | 18.646304 |
| 20016 | Otomatik doğru | 14.043415 | 8.956585 | 14.043415 | 8.956585 |
| 20017 | Otomatik doğru | 28.888133 | 26.111867 | 28.888133 | 26.111867 |
| 20018 | Otomatik doğru | 19.456067 | 25.543933 | 19.456067 | 25.543933 |
| 20019 | Otomatik doğru | 15.398424 | 19.601576 | 15.398424 | 19.601576 |
| 20020 | Otomatik doğru | 9.810312 | 13.189688 | 9.810312 | 13.189688 |
| 20021 | Otomatik doğru | 23.825014 | 22.174986 | 23.825014 | 22.174986 |
| 20022 | Otomatik doğru | 26.974391 | 28.025609 | 26.974391 | 28.025609 |
| 20023 | Otomatik doğru | 11.451379 | 8.548621 | 11.451379 | 8.548621 |
| 20024 | Otomatik doğru | 10.722968 | 19.277032 | 10.722968 | 19.277032 |
| 20025 | Otomatik doğru | 21.558413 | 18.441587 | 21.558413 | 18.441587 |
| 20026 | Otomatik doğru | 16.244436 | 22.755564 | 16.244436 | 22.755564 |
| 20027 | Otomatik doğru | 27.840536 | 28.159464 | 27.840536 | 28.159464 |
| 20028 | Otomatik doğru | 15.488276 | 26.511724 | 15.488276 | 26.511724 |
| 20029 | Otomatik doğru | 18.344370 | 19.655630 | 18.344370 | 19.655630 |

Bütün 120 görüntünün ayrıntısı test/case_results.csv ve case_scores.json içinde.

## Otomatik ve gerçek çıkarım testleri

| Test / doğrulama | Durum | Kanıt |
|---|---|---|
| Değişiklik öncesi pytest | BAŞARILI | 92 passed in 57.52s; baseline_tests.log |
| İlk yeni test denemesi | BAŞARISIZ | 2 failed, 22 passed; pipeline_unit_v1.log; ankastre kapısı ve testte kütüphane metadata okuma engeli |
| İkinci yeni test denemesi | BAŞARISIZ | 1 failed, 23 passed; pipeline_unit_v2.log; tek taraflı tarama mesnetten ayırt edildi |
| Düzeltilmiş aşama/entegrasyon testleri | BAŞARILI | 24 passed in 2.59s; pipeline_unit_v3.log |
| Son python -m pytest -q | BAŞARILI | 116 passed in 51.76s; final_tests.log, final_tests.xml |
| Her testin ayrı sonucu | BAŞARILI | test_statuses.json; JUnit'ten çıkarılan 116 test kaydı |
| Analitik motor aşaması | BAŞARILI | 100 farklı girdide bağımsız Decimal referans ve denge; otomatik test içinde |
| Eksik/geçersiz girdide çözücü çağrılmaması | BAŞARILI | 13 farklı mutasyonda solver spy; otomatik test |
| Bozuk görsel, yön, ankastre, moment, yayılı/ek yük kapıları | BAŞARILI | Aşama testleri ve 14 gerçek model/OCR senaryosu |
| Ayrı doğrulama grubu | BAŞARILI | 50 görüntüde 41 doğru, 9 inceleme; validation/ |
| 30 yeni fiziksel problem / 120 görüntü ölçümü | BAŞARILI | 120/120 çalıştırıldı; test/metrics.json |
| Bütün test görüntülerinde otomatik çözüm hedefi | BAŞARISIZ | 110/120; 10 çizimde inceleme |
| Gerçek 2B pencere smoke testi | BAŞARILI | Tk penceresi gizli oluşturuldu, resim yükleme/worker/JSON hattı çalıştı; gui_smoke.log ve gui_smoke_result.json; insan görsel incelemesi değildir |
| Gerçek CLI örneği | BAŞARILI | cli_demo.log / cli_demo.json |
| JSON'da durdurulmuş tepkilerin null olması | BAŞARILI | 120 dosya kontrol edildi; output_checks.json |
| Eski veri/model/deney ve motorların korunması | BAŞARILI | 17.817 dosyada aynı SHA-256; preservation_after.json |
| macOS / Linux çalıştırma | ÇALIŞTIRILAMADI | Gerçek çalışma Windows x64/Python 3.13.12; kod taşınabilirlik incelemesi dışında test edilmedi |
| Gerçek dış kaynak çizim testi | ÇALIŞTIRILAMADI | Etiketli dış kaynak çizim grubu yok |

Yeni üçüncü taraf bağımlılık eklenmedi. Model ağırlıkları ve eski OCR/geometri
kaynakları değiştirilmedi. Öğrenilmiş dedektör, OCR ve her aşama ayrı ölçüldü;
nihai deneyde oracle kutu/metin kullanılmadı. Aşama izolasyon birim testlerinin
kontrollü/oracle girdileri model doğruluğu gibi raporlanmadı.

## 14 kontrollü güvenlik örneği

Bu görüntüler eğitim çiziminin değiştirilen kopyalarıdır; asılları korunur.
Gerçek dedektör/OCR hattı çalıştırıldı. Hepsinde çözüm başlamadan durdu.
Bunlar bağımsız kapsam dışı dağılımın eksiksiz tanınması kanıtı değildir.

| Senaryo | Durum | Gerçek durdurma nedenleri |
|---|---|---|
| erased_force | BAŞARILI | extraction_requires_review; missing_inputs; missing_force_text |
| wrong_force_unit | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; unsupported_unit; missing_force_text; unexplained_load_region_ink |
| contradictory_total | BAŞARILI | extraction_requires_review; missing_inputs; contradictory_dimensions |
| wrong_length_unit | BAŞARILI | extraction_requires_review; missing_inputs; unsupported_unit |
| erased_dimensions | BAŞARILI | extraction_requires_review; missing_inputs; incomplete_dimension_chain |
| extra_force_text | BAŞARILI | extraction_requires_review; missing_inputs; missing_force_text |
| upward_force | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; support_beam_mismatch; load_geometry; ambiguous_dimension_endpoint; ambiguous_dimension_endpoint; incomplete_dimension_chain; unsupported_load_direction; unsupported_support_shape; unexplained_load_region_ink |
| horizontal_force | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; symbol_inventory; unsupported_symbol_inventory |
| fixed_support | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; symbol_inventory; unsupported_symbol_inventory |
| moment | BAŞARILI | scope_requires_review; unexplained_load_region_ink |
| distributed | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; unsupported_unit; symbol_inventory; unsupported_symbol_inventory |
| third_arrow | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; symbol_inventory; unsupported_symbol_inventory |
| blank | BAŞARILI | extraction_requires_review; scope_requires_review; missing_inputs; symbol_inventory; unsupported_symbol_inventory |
| corrupt | BAŞARILI | image_or_inference_failure |

## Denge ile doğru okuma arasındaki fark

Kontrollü testte gerçek L=10, P1=8, x1=3, P2=6, x2=7 için
RA=7.4, RB=6.6 kN. P1 yanlışlıkla 18 kabul edilince
RA=14.4, RB=9.6 kN elde edilir ve **yanlış okunan girdilere göre
her iki denge denklemi de sağlanır**. Referans problem için doğru tepki değildir.
Bu, gerçek OCR başarısızlığı gibi uydurulmuş bir deney değil; özellikle yanlış
girdi verilen ve gerçekten çalıştırılan solver testidir. Kanıt
coherent_wrong_reading_demo.json ve ilgili otomatik testtir.

Bu yüzden üst seviye status=computed, yalnız doğrulanan okuma girdilerinden
hesap üretildiğini anlatır. interpretation_truth_status=not_independently_verified
ve equilibrium.interpretation_verified=false her çıktıda korunur.

## İnceleme gerektiren gerçek test çizimleri

Bütün 10 görüntünün tam JSON'u kaydedildi ve her birinin görseli
 test/failures/ altındadır. Özet kolaj StatikAI_Uctan_Uca_Hatalar.png dosyasında.

| Görüntü | Ret / inceleme nedenleri |
|---|---|
| e2e_20004_v3.png | extraction_requires_review; scope_requires_review; missing_inputs; missing_unit; incomplete_dimension_chain; support_type_unverified |
| e2e_20005_v1.png | extraction_requires_review; missing_inputs; missing_unit; incomplete_dimension_chain |
| e2e_20007_v2.png | extraction_requires_review; missing_inputs; missing_unit; incomplete_dimension_chain |
| e2e_20009_v0.png | extraction_requires_review; scope_requires_review; missing_inputs; symbol_inventory; unsupported_symbol_inventory |
| e2e_20014_v0.png | scope_requires_review; support_type_unverified |
| e2e_20015_v0.png | scope_requires_review; support_type_unverified |
| e2e_20020_v3.png | scope_requires_review; support_type_unverified |
| e2e_20025_v3.png | extraction_requires_review; missing_inputs; missing_unit; incomplete_dimension_chain |
| e2e_20028_v2.png | extraction_requires_review; missing_inputs; missing_unit; incomplete_dimension_chain |
| e2e_20029_v1.png | extraction_requires_review; missing_inputs; missing_unit; missing_unit; incomplete_dimension_chain |

## Deney ayrımı, süre ve kalan sınırlar

Seed=22091115 ile yeni 30 fizik ailesi ve dört çizim düzeni testten önce
oluşturuldu. Eski V2, V3 ve OCR test fizik kayıtlarıyla tam örtüşme sıfır.
Yeni görüntüler eğitimde kullanılmadı; CSV/anotasyonlar yalnız sonradan puanlamada
okundu. Referanslar mevcut çözücüden bağımsız Decimal kuvvet/moment denklemleriyle
üretildi. Kod, ağırlık, eşik ve plan hash'leri test öncesi frozen_protocol.json
ile kilitlendi ve sonrasında doğrulandı. Testten ayar yapılmadı.

Çıkarım+referans puanlama+JSON/görselleştirme süresi 70.89 s / 120 çizim;
model ilk yükleme hariç ortalama 0.591 s/görüntü.
Sistem CPU üzerinde çalıştırıldı. Bu saf model FPS veya eğitim süresi değildir.

Testler aynı V2 çizim üreticisinden gelir: font ve sembol dağılımı eğitimle
benzerdir. Gerçek el çizimi, tarama, perspektif, küçük açılı kuvvet, farklı
mesnet standardı ve görünmeyen/okunamayan ek yükler için genelleme kanıtı yoktur.
Yalnız açıklanmayan çizgiler ve tanınan kapsam uyuşmazlıklarında ret uygulanır;
kapsam dışı nesnenin her durumda fark edileceği garantisi yoktur.

OCR yanlış değeri yüksek güvenle ve tutarlı okuyabilir; denge bunu düzeltemez.
Sıfır yanlış otomatik sonuç yalnız bu son testte gözlendi. İncelemeli/kısmi
veriler hesaba aktarılmaz. Gerçek yapı tasarımı veya güvenlik kararı bu
araştırma prototipiyle verilmemelidir.
