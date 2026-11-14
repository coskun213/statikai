# StatikAI — Ölçülendirilmiş veri seti V2 raporu

Tarih: 8 Kasım 2026 (Türkiye). Sürüm şeması: `statikai.dimensions.v2`.
Yeni veri: `dataset_dimensions_v2/`. Kaynak: değiştirilmemiş `dataset_extended/`.

## Sonuç

**500 aile / 2.500 yeni görüntü üretildi; 54 otomatik test ve tam veri denetimi geçti.**
Eski 500 aile/2500 görüntü korunmuştur. Yeni sürüm eski fiziksel problemlerin
ayrı çizimleridir; 500 yeni bağımsız fizik problemi veya dış kaynaktan gerçek
mühendislik çizimi olarak sunulamaz. Eski test aileleri yeni eğitim grubuna taşınmadı.

Eski veri setleri, model/deney dosyaları, örnekler ve 3B kaynaklarını kapsayan
**5444 dosyanın SHA-256 özetleri değişmedi**. Ağırlıklar yeniden
eğitilmedi; eski sabit test/eşik/sonuç dosyaları yazılmadı. 3B modülü korunmuştur.

[Örnek görselleri aç](C:/Users/HP/Documents/Codex/2026-11-08/t/outputs/StatikAI_V2_Ornekler.png).
Örnekler model tahmini değil, veri setindeki çizimlerdir. Renkli etiket örneğindeki
kutular yer gerçekleridir. Seçim kuralı: aile 0 varyant 0–4 ve aile 9 varyant 1;
başarıya veya görsel puanına göre seçim yapılmadı. Altı örnek görsel olarak incelendi;
tüm 2500 görüntünün insan/uzman tarafından tek tek incelendiği iddia edilmez.

## Tasarım ve kaldırılan kısa yol

Görüntünün altında `L=... | x1=... | x2=...` biçiminde hazır bir parametre satırı
yok. Değerler ölçü çizgileriyle ilişkilendirilmiş, birim taşıyan sayılar olarak
çizilir. RA/RB görüntüye yazılmaz. Birim, sembol ve metin ilişkileri yer gerçeği
JSON'unda saklanır; bunlar görüntüden çıkarım girdisi olarak verilemez.

- `chain_total`: üç parça mesafesi ve ayrıca toplam açıklık.
- `chain_only`: yalnız üç parça mesafesi; L=d1+d2+d3, x1=d1, x2=d1+d2 gerekir.
- `datum`: A'dan iki yüke ve B'ye üç kademeli ölçü.
- `mixed`: A–yük1, yük1–yük2 ve toplam açıklık ayrı seviyelerde.

Mafsal üçgeni, iki makaralı hareketli mesnet, zemin taraması, aşağı yönlü kuvvet
okları, ölçü yardımcı çizgileri ve iç ok/tik uçları kullanılır. Semboller gerçek
çizimlerden alınmadı; mühendislik gösterimlerinden esinlenen kodla üretilmiş
şekillerdir. Bir çizim standardına tam uygunluk iddiası yoktur. Bütün nesnelerin
mürekkep rengi aynıdır; kuvvet/mesnet sınıfı renkle açıkça kodlanmaz.

Font, tuval boyutu, çizgi kalınlığı, sembol oranları, yerleşim, uç biçimi,
ondalık nokta/virgül ve N/kN ile m/cm/mm birimleri değişir. Sayısal fizik CSV'de
m ve kN cinsindedir. Çizgiler yerel çözünürlüğe göre ölçeklendiğinden CSV'deki
1/2/3 temel kalınlık her çözünürlükte aynı piksel sayısı değildir.

## Veri sayıları ve grup ayrımı

| Özellik | Sayı |
|---|---:|
| Temel aile | 500 |
| Görüntü | 2500 |
| Fiziksel eşdeğer varyant | 4 / aile |
| Yalnız x1 değişen müdahale varyantı | 1 / aile |
| Benzersiz fiziksel konfigürasyon | 1000 |
| Sembol kutusu / maske örneği | 10000 |
| Ölçü etiketi ve uç ilişkisi | 8500 |
| Toplam metin etiketi | 18500 |
| Fontla yeniden rasterleştirilerek doğrulanan metin | 18500 |
| Mafsal / hareketli mesnet / tekil yük | 2500 / 2500 / 5000 |

| Grup | Aile | Görüntü |
|---|---:|---:|
| Eğitim | 350 | 1750 |
| Doğrulama | 100 | 500 |
| Test | 50 | 250 |

Ayrım kaynak `problem_id` ve `split` değerlerini aynen taşır. Aynı ailenin dört
eşdeğer ve bir müdahale görüntüsü aynı gruptadır. V0/V4 çizim, font ve birim
parametreleri aynıdır; yalnız x1 değişimi ve onun neden olduğu ölçü/ok değişir.
Bu, görsel farkın fiziksel müdahaleyle kontrollü biçimde ilişkilendirilmesini sağlar.
Her grupta dört ölçü düzeni, dört font ve tüm birimler vardır.

| Çeşitlilik | Değer | Görüntü sayısı |
|---|---|---:|
| Font | cour.ttf | 639 |
| Font | times.ttf | 641 |
| Font | arial.ttf | 607 |
| Font | calibri.ttf | 613 |
| Çözünürlük | 900x660 | 840 |
| Çözünürlük | 1500x1100 | 835 |
| Çözünürlük | 1200x880 | 825 |
| Sembol stili | 2 | 567 |
| Sembol stili | 1 | 628 |
| Sembol stili | 0 | 631 |
| Sembol stili | 3 | 674 |
| Ölçü düzeni | chain_total | 1000 |
| Ölçü düzeni | datum | 500 |
| Ölçü düzeni | chain_only | 500 |
| Ölçü düzeni | mixed | 500 |
| Uzunluk birimi | mm | 862 |
| Uzunluk birimi | cm | 793 |
| Uzunluk birimi | m | 845 |
| Kuvvet birimi | N | 1219 |
| Kuvvet birimi | kN | 1281 |
| Temel çizgi kalınlığı | 1 | 829 |
| Temel çizgi kalınlığı | 2 | 870 |
| Temel çizgi kalınlığı | 3 | 801 |

Fizik aralıkları: L 7–15.95 m;
P1/P2 3–30 kN. Sınırlı, yatay, iki basit mesnetli ve iki düşey tekil yüklü problem
alanı korunmuştur. Dağılımlar bu alanın dışındaki mühendislik problemlerini temsil etmez.

## Analitik ve etiket denetimi

Her görüntüde 0<x1<x2<L, P1/P2>0 koşulları doğrulandı. Üretimde kullanılan
sayısal çözümden bağımsız olarak Decimal aritmetiğiyle:

```text
RB = (P1*x1 + P2*x2) / L
RA = P1 + P2 - RB
```

Tekrar hesaplandı. En büyük RA/RB referans farkı **5.000e-11 kN**;
en büyük kuvvet artığı **0.000e+00 kN**;
en büyük moment artığı **7.670e-10 kNm**. Küçük farklar
CSV'deki 10 ondalık kayıtla uyumludur; bunlar model tahmin hataları değildir.

Ek kontroller:

| Kontrol | Sonuç | Ölçülen |
|---|---|---:|
| Aynı problemin farklı gruplara düşmemesi | BAŞARILI | 0 aile sızıntısı |
| Aynı fiziğin farklı ailelerde tekrarı | BAŞARILI | 0 |
| Aynı fiziğin farklı gruplarda tekrarı | BAŞARILI | 0 |
| Tam PNG'nin gruplar arası tekrarı | BAŞARILI | 0 |
| 256x160 gri tam görüntü girdisi tekrarı | BAŞARILI | 0 |
| %22 paylı 48x48 RGB sembol kırpımı tekrarı | BAŞARILI | 0 ortak hash |
| Sembol sınıfı/kutusu ile gerçek piksel maskesi eşleşmesi | BAŞARILI | 10000 sembol |
| Fiziksel yük konumu/ölçü uç noktası ilişkileri | BAŞARILI | 2500 görüntü |
| Ölçü ve kuvvet birimi dönüşümleri | BAŞARILI | 18500 metin içinde ilgili değerler |
| Transkripsiyonun görüntüde gerçekten çizilmiş olması | BAŞARILI | 18500 metin |
| Dosya içeriği ve kaynak CSV bağları | BAŞARILI | manifest SHA-256 |
| Eski veri/ağırlık/sonuç ve 3B modülünün korunması | BAŞARILI | 5444 dosya |

Sembol maskesi kutuları doğrudan çizilmiş nesne piksellerinden bulunur. Denetleyici,
üreticinin çizim fonksiyonunu çağırmaz; maskeyi, kutuyu, sınıfı, referans konumu ve
metin miktarını ayrı kontrol eder. Kaydedilmiş fontla transkripsiyonu tekrar
çizip gerçek görüntüyle karşılaştırmak OCR değildir. Bu yöntem şu makinede
etiket/raster tutarlılığını sınar; insanın semantik çizim incelemesinin yerini tutmaz.

Kırpım kontrolü yalnız dört ön plan sembolünü kapsar. Eski pilotun sabit arka plan
kırpımı seçicisi V2 için doğrulanmadı; çözünürlük/yerleşim değiştiği için doğrudan
kullanılmamalı. Eski verideki 140/140 test kırpımı tekrarı bulgusu tarihsel olarak
devam eder; eski veri değiştirilerek bu sonuç gizlenmedi.

## Test sonuçları

Başlangıç: eski 41 test **BAŞARILI**, 9.15 saniye.
Yeni 13 test ayrı çalıştırmada **BAŞARILI**, 29.39 saniye.
Son tam komut: **54 passed in 44.91s**, çıkış kodu 0.

```text
python -m pytest -q --junitxml audit_results/dataset_v2_20261108_01/final_tests.xml
```

Yeni testler veri üretimi/analitik ve grup sözleşmesi, yalnız segment etiketlerinden
L/x1/x2 türetme, kontrollü müdahale, üzerine yazmama ve aynı tohumla bütün
veri dosyalarını tekrar üretmeyi kapsar. Ayrıca yalnız denemeye ait kopyalarda
yanlış tepki, grup sızıntısı, fizik tekrarı, sınıf değişimi, yanlış ölçü yazısı,
eşdeğer birimle yanlış transkripsiyon, aynı görüntü, bozuk etiket ve eksik dosya
hataları eklendi. Hash manifesti de yeniden bağlandığında içerik denetleyicisinin
sınıf/metin/fizik hatalarını yakaladığı kontrol edildi. Orijinal veriler değiştirilmedi.

| Çalıştırma | Durum | Toplam süreç süresi (s) |
|---|---|---:|
| `dataset_v2_unit_01` | BAŞARILI | 29.878 |
| `dataset_v2_full_tests_01` | BAŞARILI | 46.596 |
| `dataset_v2_generate_01` | BAŞARILI | 303.552 |
| `dataset_v2_full_audit_01` | BAŞARILI | 93.390 |

| No | Test | Sonuç |
|---:|---|---|
| 1 | `test_dataset_v2::test_v2_lineage_units_labels_and_split_contract` | BAŞARILI |
| 2 | `test_dataset_v2::test_segment_dimensions_reconstruct_physics_without_parameter_summary` | BAŞARILI |
| 3 | `test_dataset_v2::test_controlled_intervention_and_no_overwrite` | BAŞARILI |
| 4 | `test_dataset_v2::test_same_seed_reproduces_all_dataset_bytes` | BAŞARILI |
| 5 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[reaction-wrong reaction reference]` | BAŞARILI |
| 6 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[split-problem crosses splits]` | BAŞARILI |
| 7 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[duplicate_physics-repeat across families]` | BAŞARILI |
| 8 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[class_swap-YOLO class/bbox]` | BAŞARILI |
| 9 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[dimension_text-wrong dimension text/unit/value]` | BAŞARILI |
| 10 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[force_transcription-text transcription/raster mismatch]` | BAŞARILI |
| 11 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[image_duplicate-resized full-image inputs repeat]` | BAŞARILI |
| 12 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[malformed_label-Malformed or unreadable]` | BAŞARILI |
| 13 | `test_dataset_v2::test_corruptions_are_detected_beyond_file_checksums[missing_image-Malformed or unreadable]` | BAŞARILI |
| 14 | `test_detection::test_one_to_one_matching_counts_duplicate_as_false_positive` | BAŞARILI |
| 15 | `test_detection::test_box_geometry_round_trip_and_empty_image` | BAŞARILI |
| 16 | `test_detection::test_classical_finds_arrow_from_pixels_without_annotation_access` | BAŞARILI |
| 17 | `test_detection::test_full_image_model_loss_backprop_and_inference_have_no_oracle` | BAŞARILI |
| 18 | `test_experiments::test_patches_and_model_shapes` | BAŞARILI |
| 19 | `test_experiments::test_oracle_prediction_evaluation` | BAŞARILI |
| 20 | `test_extended_data::test_extended_qa_and_controlled_interventions` | BAŞARILI |
| 21 | `test_extended_data::test_qa_detects_cross_split_family_leakage` | BAŞARILI |
| 22 | `test_extended_data::test_qa_rejects_wrong_reference_and_invalid_box` | BAŞARILI |
| 23 | `test_frame3d::test_cantilever_matches_independent_hand_solution[FY-DY-Iz]` | BAŞARILI |
| 24 | `test_frame3d::test_cantilever_matches_independent_hand_solution[FZ-DZ-Iy]` | BAŞARILI |
| 25 | `test_frame3d::test_axial_and_torsion_hand_solutions` | BAŞARILI |
| 26 | `test_frame3d::test_rectangle_square_and_axis_swap` | BAŞARILI |
| 27 | `test_frame3d::test_grid_load_area_and_global_force_moment_balance` | BAŞARILI |
| 28 | `test_frame3d::test_zero_load_and_linear_load_scaling` | BAŞARILI |
| 29 | `test_frame3d::test_isotropic_square_plan_rotates_symmetrically` | BAŞARILI |
| 30 | `test_frame3d::test_invalid_input_rejected[changes0]` | BAŞARILI |
| 31 | `test_frame3d::test_invalid_input_rejected[changes1]` | BAŞARILI |
| 32 | `test_frame3d::test_invalid_input_rejected[changes2]` | BAŞARILI |
| 33 | `test_frame3d::test_invalid_input_rejected[changes3]` | BAŞARILI |
| 34 | `test_frame3d::test_invalid_input_rejected[changes4]` | BAŞARILI |
| 35 | `test_frame3d::test_invalid_input_rejected[changes5]` | BAŞARILI |
| 36 | `test_frame3d::test_invalid_input_rejected[changes6]` | BAŞARILI |
| 37 | `test_frame3d::test_invalid_input_rejected[changes7]` | BAŞARILI |
| 38 | `test_generator::test_reactions` | BAŞARILI |
| 39 | `test_generator::test_dataset` | BAŞARILI |
| 40 | `test_hardening::test_invalid_physics_is_rejected[values0]` | BAŞARILI |
| 41 | `test_hardening::test_invalid_physics_is_rejected[values1]` | BAŞARILI |
| 42 | `test_hardening::test_invalid_physics_is_rejected[values2]` | BAŞARILI |
| 43 | `test_hardening::test_invalid_physics_is_rejected[values3]` | BAŞARILI |
| 44 | `test_hardening::test_invalid_physics_is_rejected[values4]` | BAŞARILI |
| 45 | `test_hardening::test_invalid_physics_is_rejected[values5]` | BAŞARILI |
| 46 | `test_hardening::test_invalid_physics_is_rejected[values6]` | BAŞARILI |
| 47 | `test_hardening::test_validation_survives_python_optimized_mode` | BAŞARILI |
| 48 | `test_hardening::test_symmetric_and_mirror_properties` | BAŞARILI |
| 49 | `test_hardening::test_wrong_reading_can_be_self_consistent` | BAŞARILI |
| 50 | `test_hardening::test_nonfinite_predictions_rejected[values0]` | BAŞARILI |
| 51 | `test_hardening::test_nonfinite_predictions_rejected[values1]` | BAŞARILI |
| 52 | `test_hardening::test_duplicate_and_empty_predictions_rejected` | BAŞARILI |
| 53 | `test_hardening::test_missing_predictions_do_not_inflate_full_accuracy` | BAŞARILI |
| 54 | `test_hardening::test_font_is_available_without_linux_path` | BAŞARILI |

## Kaydedilen dosyalar ve kullanım

- `generate_extended_dataset.py`: eski v1 üretici korunur; `--version dimensions-v2` yeni yolu seçer.
- `statikai/dataset_v2.py`: kaynak ailelerini yeni ölçü çizgileriyle yeniden çizer.
- `audit_dataset.py` ve `statikai/dataset_v2_audit.py`: eski kontroller + yeni sürüm denetimi.
- `dataset_dimensions_v2/`: PNG, YOLO, piksel maskeleri, ayrıntılı JSON ve CSV'ler.
- `test_dataset_v2.py`: veri sözleşmesi ve kasıtlı bozulma testleri.
- `audit_results/dataset_v2_20261108_01/`: gerçek QA, dağılımlar, koruma ve JUnit çıktıları.
- `audit_results/logs/dataset_v2_*.log/.json`: komut, süre, çıkış ve kaynak kod özetleri.
- `docs/Veri_Seti_V2_Kullanimi.md`: alan ve dosya sözleşmesi, tekrar üretim yönergesi.

Yeni veri sürümü, tohum **20261109**, Python 3.13.12, Pillow 13.0.0.
Manifest **10003 veri dosyasının** özetini içerir; manifest ayrıca
kaydedilir. Font dosyaları dağıtılmaz; dosya adları ve SHA-256 özetleri kaydedilir.
Üretim sırasında 0 çakışan/sınır dışı metin yerleşimi
adayında yeniden örnekleme yapıldı. Bu karar model skoruna göre verilmedi; okunabilir
etiket yerleşimi kuralıdır. Kırpım hash sonuçlarına göre örnek seçilmedi/silinmedi.

Proje kökünde, bağımlılıkları kurulu Python ile:

```powershell
python generate_extended_dataset.py --version dimensions-v2 --source dataset_extended --out dataset_dimensions_v2_yeniden --seed 20261109
python audit_dataset.py --dataset dataset_dimensions_v2_yeniden --out work/v2_yeniden_qa.json
```

V2 üretici var olan çıktı klasörünü reddeder. Kaynak veri de denetlenir; son
manifest tamamlanmadan sürüm bitmiş sayılmaz. Aynı font, sürüm, kaynak ve tohumla
50 görüntülük test sürümü byte düzeyinde yeniden üretildi. Başka platform/font
sürümünde aynı piksellerin çıkacağı iddia edilmez.

## Eksikler ve bilimsel sınırlar

1. **Şemalar ölçekli.** Hazır parametre satırı kaldırıldı, ancak piksel oranlarından
   yararlanma kısayolu hâlâ mümkün. Gerçekten ölçek dışı şemalar ve yanıltıcı ölçek
   deneyleri bu sürümde yok. Bütün kısayolların giderildiği iddia edilemez.
2. Aynı eski fizik aileleri yeniden çizildi. Yeni bir bağımsız fiziksel test örneklemi
   veya dış kaynaktan toplanmış gerçek mühendislik çizim seti yok. Yalnız font/stil
   çeşitliliği gerçek dünya genellemesini kanıtlamaz; yakın şablon benzerliği sürebilir.
3. Bütün örneklerde iki mesnet ve iki aşağı yönlü tekil yük var. Sembolsüz/zor negatif,
   kısmi çizim, okunamayan sayılar, el yazısı, perspektif, eğik kiriş, yayılı yük,
   moment yükü, ankastre ve hiperstatik örnekler yok. Hata reddetme bu veriyle tek
   başına doğrulanamaz. Yanlış/eksik giriş örnekleri model eğitimi için hazırlanmadı.
4. Görseller temiz; tarama gürültüsü, JPEG, aydınlatma, silinmiş çizgi ve çizgi-metin
   çakışmaları veri koşulları olarak modellenmedi. Çakışan etiketler bilerek reddedildi.
5. OCR, metin–sembol eşleştirme modeli, görüntüden RA/RB çözüm zinciri ve uçtan uca
   başarı deneyi bu aşamada **ÇALIŞTIRILAMADI**; bu modüller henüz yok. Metin-raster
   doğrulaması bir OCR başarı yüzdesi değildir. Mevcut ağırlıkların V2'deki başarısı
   ölçülmedi; bu görev veri aşamasıdır.
6. Yeni `style=D2`, eski eğitim kodunun yalnız A seçen filtresinden ayrıdır. Yeni
   eğitim/değerlendirme adaptörü ve kilitli protokol gerekir; otomatik olarak eski
   test protokolüne eklemek ya da testten eşik ayarlamak uygun değildir.
7. Bu makinede kayıtlı dört fontun tamamıyla metin doğrulandı. Diğer sistemlerde
   font bulunamazsa metin-raster denetimi uyarı verebilir; görüntü/maskeler ve diğer
   anlamsal kontroller taşınabilir. Linux/macOS çalıştırmaları **ÇALIŞTIRILAMADI**.
8. Üretilmiş etiketlerin tutarlılığı denetlendi, fakat mühendislik gösterimlerinin
   ve ölçü okunabilirliğinin bütün veri için bağımsız uzman onayı alınmadı.

Bir sonraki araştırma adımı yeni eğitim/validasyon kaynaklarında ölçek dışı ve gerçek
çizimleri eklemek, yeni kilitli dış test hazırlamak ve faz sırasıyla OCR/eşleştirme
modüllerini geliştirmektir. Mevcut sürüm ve eski sonuçlar korunarak yeni sürüm açılmalıdır.
