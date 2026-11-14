"""Build the Turkish audit report from actual JSON/CSV/log artifacts."""
import csv
import json
from pathlib import Path


def build(root):
    read=lambda name:json.loads((root/name).read_text(encoding='utf8'))
    metrics=read('detector_results/evaluation/metrics.json')
    protocol=read('detector_results/evaluation/frozen_protocol.json')
    train=read('detector_results/training_metadata.json')
    env=read('audit_results/environment.json')
    original=read('audit_results/original_dataset_audit_final.json')
    extended=read('audit_results/extended_dataset_audit_final.json')
    percent=lambda value:f'{100*value:.2f}'
    learned=metrics['methods']['learned'];classical=metrics['methods']['classical']
    table=[]
    for style,label in [('A','A: eğitimde görülen gösterim'),('B','B: eğitimde kullanılmayan gösterim')]:
        a,b=classical['by_style'][style],learned['by_style'][style]
        table.append(f"| {label} | {b['images']} | %{percent(a['f1'])} | %{percent(b['f1'])} | %{percent(b['exact_image_rate'])} |")
    table.append(f"| Birlikte | {metrics['test_images']} | %{percent(classical['f1'])} | %{percent(learned['f1'])} | %{percent(learned['exact_image_rate'])} |")
    logs=[]
    for path in sorted((root/'audit_results/logs').glob('*.json')):
        item=json.loads(path.read_text(encoding='utf8'))
        logs.append(f"| `{path.stem}` | {item['exit_code']} | {item['elapsed_seconds']:.3f} | `{path.with_suffix('.log').relative_to(root).as_posix()}` |")
    with (root/'audit_results/pilot_shift_reproduced.csv').open(encoding='utf8',newline='') as handle:
        pilot=list(csv.DictReader(handle))
    pilot_table='\n'.join(f"| {r['condition']} | {r['n']} | %{percent(float(r['accuracy']))} | {float(r['macro_f1']):.4f} |" for r in pilot)
    ci=learned['family_bootstrap_95_ci']['f1']
    return f'''# StatikAI — Sistem denetimi ve ilk tam görüntü tespit prototipi

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
{pilot_table}

Bu test yalnızca **4 temel problemden 140 oracle kırpımı** içerir. Diyagram
tespiti, OCR veya statik çözüm başarısı değildir. Arka plan örnekleri çoğunlukla
boş bir banttan alınmıştır; zor negatifleri temsil etmez. Eğitim/test aynı
çizim üreticisinden gelir; sabit sembol konumları kolaylaştırıcıdır.

## Veri sızıntısı ve veri/etiket denetimi

| Özellik | Sağlanan veri | Yeni veri |
|---|---:|---:|
| Temel problem | {original['problems']} | {extended['problems']} |
| Görüntü | {original['images']} | {extended['images']} |
| Sembol kutusu | {original['boxes']} | {extended['boxes']} |
| Benzersiz fiziksel konfigürasyon | {original['unique_physical_configurations']} | {extended['unique_physical_configurations']} |
| Ayrımlar arası aynı fiziksel konfigürasyon | {original['cross_split_physical_leaks']} | {extended['cross_split_physical_leaks']} |
| Ayrımlar arası aynı görüntü özeti | {original['cross_split_image_hash_leaks']} | {extended['cross_split_image_hash_leaks']} |
| Farklı ailelerde tekrarlayan aynı fizik | {original['physical_configurations_shared_across_families']} | {extended['physical_configurations_shared_across_families']} |

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
{original['max_moment_residual_kNm']:.9g} kNm; yeni CSV'de
{extended['max_moment_residual_kNm']:.9g} kNm. Bunlar kaydedilen sayıların
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

CPU, tohum {train['seed']}, {train['epochs']} epok, {train['parameters']} parametre,
eğitim döngüsü yaklaşık {train['elapsed_seconds']:.1f} saniye. A stilinden
{train['train_images']} eğitim görüntüsü ve 30 boş negatif kullanıldı.
Model sıfırdan eğitildi; ön-eğitimli ağırlık kullanılmadı. Merkez ısı haritası
ve kutu regresyonu yaklaşımı küçük bir özel mimariyle uygulandı; resmi
CenterNet modelinin birebir uygulaması olduğu iddia edilmez.

Model epoku ve eşikler yalnızca 100 validasyon ailesinden 400 A görüntüsünde
seçildi. Seçilen epok: {protocol['selected_epoch']}; öğrenilmiş eşik:
{protocol['learned']['score_threshold']}; klasik doluluk eşiği:
{protocol['classical']['fill_cutoff']}. Parametreler testten önce
`frozen_protocol.json` içine yazıldı. Test sonucuna göre yeniden eğitim veya
eşik ayarı yapılmadı. Aynı 50 test ailesinin aynı 250 görüntüsü kullanıldı.

## Gerçek tam görüntü tespit sonuçları

Doğru sınıf + IoU >= 0.50 ile bire bir eşleştirme. Aşağıdaki F1 değerleri
**sembol tespitine** aittir; OCR veya mesnet tepkisi çözüm doğruluğu değildir.

| Test koşulu | Görüntü | OpenCV F1 | Öğrenilmiş F1 | Öğrenilmiş: 4 nesne doğru, fazladan kutu yok |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

Birleşik testte öğrenilmiş yöntem: TP={learned['tp']}, FP={learned['fp']},
FN={learned['fn']}; precision %{percent(learned['precision'])}, recall
%{percent(learned['recall'])}. Aile bazında 1000 bootstrap tekrarından F1 için
%95 aralık: %{percent(ci[0])}–%{percent(ci[1])}. Bu aralık yalnızca bu sentetik
aile örneklemesini kapsar; eğitim tohumu ve gerçek kaynak değişkenliğini kapsamaz.

**Önemli başarısızlık:** B stilinde hareketli mesnet recall değeri öğrenilmiş
yöntemde %{percent(learned['by_style']['B']['per_class']['roller_support']['recall'])};
klasik yöntemde %{percent(classical['by_style']['B']['per_class']['roller_support']['recall'])}.
Öğrenilmiş yöntemin B stilinde tüm dört nesneyi doğru bulduğu görüntü oranı
yalnızca %{percent(learned['by_style']['B']['exact_image_rate'])}.
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

Önceden tanımlı ilk on test ailesi: {metrics['diagnostic_families']}.
Her ailenin beş varyantı için toplam 50 görüntüde iki yöntemin sonuçları
`diagnostic_10_families.json` içindedir. Her satırda OCR/çözümün eksik olduğu
açıkça belirtilir. Bu, tam otomatik statik çözüm deneyinin tamamlandığı anlamına gelmez.
En düşük F1'li on görüntü/yöntem ve on kanonik aile örneği için kutulu PNG'ler kaydedildi.

## Windows, macOS, Linux

Gerçekte ölçülen ortam: {env['platform']}, Python 3.13.12,
PyTorch {env['torch']}, OpenCV {env['opencv']}; GPU kullanılmadı.
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
{chr(10).join(logs)}

## Teknik kaynaklar

- Merkez tabanlı tespit fikri: https://arxiv.org/abs/1904.07850
- OpenCV bağlı bileşenler: https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html
- Font yükleme: https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
- Checkpoint yükleme: https://docs.pytorch.org/docs/2.15/generated/torch.load.html
- Intel macOS desteği: https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690
- NumPy/OpenCV sürüm ilişkisi: https://github.com/opencv/opencv-python/issues/1122
'''


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    report=build(root)
    (root/'docs/Denetim_ve_Prototip_Raporu.md').write_text(report,encoding='utf8')
    print('Saved docs/Denetim_ve_Prototip_Raporu.md')
