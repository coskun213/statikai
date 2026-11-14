# OCR ve geometrik eşleştirme — deneysel V1.1

Bu modül yatay, solda mafsallı/sağda hareketli mesnetli ve iki düşey tekil
yüklü **2B sentetik kiriş diyagramlarından girdi çıkarır**. Statik hesaplama
motoru ve 3B masaüstü modülü değiştirilmedi. RA/RB hesabı çalıştırılmaz.
Masaüstü arayüzüne bağlanmadı; yeni giriş noktası komut satırıdır.

## Kurulum ve çalıştırma

Proje klasöründe, Python 3.11 veya üstü bir araştırma ortamında:

```powershell
python -m pip install -r requirements.txt -r requirements-ocr.txt
python read_beam_diagram.py --image dataset_dimensions_v2/images/beam_0000_v0.png --out work/ilk_ocr.json
python -m pytest -q
```

Windows'ta sanal ortam kullanılıyorsa `python` yerine
`.\.venv\Scripts\python.exe`; Linux/macOS'ta `.venv/bin/python` yazılır.
`--image` kendi PNG/JPEG dosyanız olabilir. `--out` mevcut dosyaların üzerine
yazmaz: her denemede yeni bir dosya adı verin. `--detector tiny` varsayılandır;
`--detector lite` diğer korunmuş V3 modelini kullanır. Raporlanan ana deney
yalnız Tiny ile yapıldı; Lite+OCR için aynı başarı iddia edilmez.

OCR ağırlıkları `experiments/ocr_v1_20261108_01/ocr_models/` içindedir.
`--ocr-models` ve `--detector-run` ile konumlar değiştirilebilir. Ağırlıklar
bulunmazsa RapidOCR ilk kullanımda internetten indirir; sonraki çıkarım yereldir.
Paketlenen iki ONNX dosyasıyla OCR çıkarımı için internet gerekmez.

Windows x64/Python 3.13 üzerinde gerçekten çalıştırıldı. Pathlib ve yerel CPU
ONNX kullanılır; mutlak Windows font yolları çıkarımın girdisi değildir.
macOS/Linux çalıştırmaları **ÇALIŞTIRILAMADI**; Python sürümü, ONNX wheel'i ve
mevcut Torch kurulumu ayrıca doğrulanmalıdır. Intel macOS için ana projenin
Torch/NumPy kısıtları korunur. OCR bağımlılıkları isteğe bağlı ayrı dosyadadır;
yalnız 3B masaüstü kurulumu için gerekli değildir.

## Ayrı bileşenler

- `statikai/ocr_engine.py`: RapidOCR 3.10.0 + ONNX Runtime 1.31.1 CPU;
  önceden eğitilmiş PP-OCRv6 small metin tespit/tanıma modelleri. Bizim
  diyagramlarımızla OCR eğitimi veya fine-tuning yapılmadı. Tanıma skoru
  kalibre edilmiş doğruluk olasılığı değildir.
- `statikai/ocr_quantities.py`: açıkça okunan pozitif sayı ve tam birim;
  `N`, `kN`, `mm`, `cm`, `m`. Bir tek virgül/nokta ondalık ayracıdır;
  binlik gruplama varsayılmaz. Harften rakam düzeltmesi, birimsiz sayı
  tamamlama veya varsayılan kuvvet/uzunluk yoktur.
- `statikai/symbol_reader.py`: korunmuş V3 Tiny ağırlıkları ve sabit 0.35 eşik.
  Model/veri protokolü SHA-256 doğrulanır. Bu OCR eğitimi değildir.
- `statikai/diagram_reading.py`: kiriş, yatay ölçü çizgisi ve düşey uzatma
  çizgilerini piksellerden bulur. Her kuvvet için tek bir geçerli metin/ok
  eşleştirmesi ister. Sayı ve birim ayrı OCR kutularındaysa yalnız karşılıklı
  tekil, komşu ve aynı satırdaki çift birleştirilir; ham kutular da korunur.
- `read_beam_diagram.py`: tek görüntüyü alır ve JSON kaydeder. Çıkarıma CSV,
  anotasyon veya maskeler verilmez. Statik motor import/çağrısı yoktur.
- `evaluate_ocr_pipeline.py`: çıkarımdan sonra referans anotasyonlarla ölçer.
  Referanslar yalnız bu değerlendirme katmanında kullanılır.

## Ölçü zinciri

Piksel konumları yalnız hangi ölçü ucunun hangi sembole ait olduğunu
belirlemek için kullanılır. Fiziksel mesafe `piksel * ölçek` ile hesaplanmaz.
Okunan ölçüler grafın kenarlarıdır; soldaki mesnet sıfır noktasıdır.
Örneğin A–F1=3 m, F1–F2=4 m, F2–B=3 m ise x1=3, x2=7, L=10 m elde edilir.
Doğrudan başlangıç ölçüleri ve karışık zincirler de aynı grafla çözülür.
Decimal aritmetiğiyle çevrim tutarlılığı kontrol edilir; eşik 0.001 m'dir.
Bağlantısız düğüm tamamlanmaz; çelişen ölçü varsa konumlar karantinaya alınır.

Yalnız piksel konumlarından çıkarılan büyüklük yoktur. Okunmuş diğer ölçülerle
bir konumun cebirsel türetilmesi mümkündür; kullanılan ölçü kimlikleri kaydedilir.
Fiziksel sıra `0 < x1 < x2 < L` ayrıca denetlenir. Kuvvet yönü bu ilk sürümde
tanınmaz; aşağı yönlü iki yük dar kapsamın ön koşuludur.

## JSON sözleşmesi

- `image`: yol, SHA-256 ve özgün piksel boyutu.
- `symbols`: sınıf, tahmin kutusu ve dedektör skoru.
- `ocr_readings`: `raw_text`, `bbox`, dört köşeli `quad`, tanıma `confidence`,
  ayrıştırma sonucu ve SI dönüşümü. Gruplanmış kutunun `component_text_ids`
  alanı özgün sayı/birim kutularına gider. Ham sonuçlar silinmez.
- `forces[].magnitude_kN`: okunan değer, kaynak kutusu, güven ve metin kimlikleri;
  okunamadığında `null`.
- `forces[].position_m`, `length_m`: ölçülerden türetilen değer ve
  `dimension_ids`/`source_text_ids`. Kaynak kutuları bu metin/ölçü kayıtlarındadır.
  Türetilmiş güven, kaynak skorlarının minimumudur; olasılık değildir.
- `geometry.dimensions`: metre cinsinden etiket değeri, kaynak kutusu/skoru,
  piksel uçları ve eşleştirilmiş sembol düğümleri.
- `issues`: kod, açıklama ve kaynak kimlikleri. Eksik birim, yanlış birim,
  düşük güven, ölçü çelişkisi, eksik uç veya belirsiz eşleştirme inceleme üretir.
- `review_required`: inceleme gerekiyorsa `true`.
- `extracted_inputs`: yalnız tüm kontroller geçtiğinde `L_m`, `P1_kN`,
  `x1_m`, `P2_kN`, `x2_m`; aksi halde `null`. Kısmi sonuçlar yukarıda korunur.
  `review_required=true` durumunda kısmi alanlar da yanlış olabilir; otomatik
  hesaba aktarılmamalıdır. Son testte bu şekilde işaretlenmiş bir yanlış kısmi
  x2 gözlendi; ayrıntısı sonuç raporundadır.
- `static_solution`: daima `status: "not_run"`, RA/RB `null`.

Bu şema ölçülmüş girdileri taşır; mühendis onayı veya güvenli yapı hesabı değildir.

## Deney ayrımı ve yeniden üretim

V1 geliştirmesi V2 train içinden 5 aile/25 görüntü; doğrulama V2 val içinden
10 aile/50 görüntüyle yapıldı. İlk sabit V1 testi V2 test 50 aile/250 görüntüdür.
İlk V1 güvenlik denetimindeki **başarısız** yanlış ölçü birimi örneği ve ilk
kod/sonuçlar silinmedi: `experiments/ocr_v1_20261108_01/frozen_source/`.

Eğitim çiziminden türetilmiş `5242 kg` kontrolünde doğru okunan yanlış birimin
etiket bölgesi filtresince atlandığı görüldü. V1.1 yalnız bu korumayı düzeltir:
sembol içinde olmayan, yüksek güvenle okunmuş desteklenmeyen birim inceleme ister.
Bu düzeltme eski test başarısına göre seçilmedi. Kısmi eski test ilerleme
skorlarının görülmesi ve karar `amendment.json` içinde açıkça kaydedildi.

V1.1 için seed=22091110 ile önceden tanımlanan **50 yeni fiziksel aile/250
görüntü** ayrı `fresh_test/` altında üretildi. Eski fizik kayıtlarıyla birebir
örtüşme sıfırdır. Aynı V2 çizim üreticisi kullanılır; yeni dış kaynak gerçek
çizim testi değildir. Eğitim/validasyon aileleriyle karışmaz. Etiket referansları
bağımsız Decimal kuvvet/moment denklemleriyle doğrulandı; çizimde hazır L/x1/x2
satırı yoktur. OCR veya dedektör bu görüntüler üretilirken çalıştırılmadı.

Plan ve hash'ler doğrulama sonrası, yeni test öncesi kilitlendi. Yeni testten
parametre seçilmedi. Mevcut sonuçlar üzerine tekrar yazılmaz; yeni deney için
yeni klasör ve açık sürüm gerekir. Başlıca komutlar:

```powershell
python tools/generate_ocr_holdout.py
python evaluate_ocr_pipeline.py prepare
python evaluate_ocr_pipeline.py validation
python evaluate_ocr_pipeline.py freeze
python evaluate_ocr_pipeline.py test
python tools/verify_ocr_safety.py --out work/yeni_guvenlik_deneyi
```

İlk dört komut paketlenmiş deneyde mevcut dosyalar nedeniyle tekrar yazmayı
reddeder. Salt denetim için `python -c "from evaluate_ocr_pipeline import
verify; verify()"` kullanılabilir. Yeni görsel okumak için yukarıdaki
`read_beam_diagram.py` komutu yeterlidir.

## Metriklerin anlamı

OCR metin kutuları referanslarla IoU≥0.30 ve bire bir eşleştirilir; referans
kutular sıkı yazı sınırları, OCR kutuları boşluklu olduğundan ayrıca IoU≥0.50
sonucu da verilir. Tam metin doğruluğunda yalnız boşluk farkı yok sayılır;
birim/rakam düzeltilmez. Sayı+birimin doğru SI değeri ayrı ölçülür. OCR'nin
mesnet taramalarını yazı sanması precision'ı düşürür; bu yanlış pozitifler sayılır.

Kuvvet/metin ilişkilendirmesi için ok IoU≥0.50, doğru etiket kutusu IoU≥0.30
gerekir. Tüm gerçek kuvvetlere göre oran ve okunmuş/tespit edilmiş girdilerdeki
koşullu oran ayrı verilir. Doğru sayı ve doğru ilişki ortak metriği de vardır.

Tam problem oranının paydası **tüm** test görüntüleridir; yalnız kabul edilenler
değildir. Kabul edilen fakat yanlış girdili problemler ayrıca sayılır. Kaynak
güveni yüksek ama tutarlı yanlış OCR okuması, özellikle gereksiz ölçü içermeyen
bir zincirde yakalanmayabilir. Sıfır gözlenen yanlış kabul bu riski yok etmez.

## Kaynaklar

- [RapidOCR resmi kaynak ve kullanım](https://github.com/RapidAI/RapidOCR)
- [RapidOCR kurulum notları](https://rapidai.github.io/RapidOCRDocs/main/en/install_usage/rapidocr/install/)
- [RapidOCR lisansı](https://github.com/RapidAI/RapidOCR/blob/main/LICENSE)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)

İndirilen model URL'leri, gerçek SHA-256 ve lisans atıfları
`docs/ocr_third_party/` içinde kaydedildi. Nicel sonuçlar ve başarısız
örnekler `OCR_VE_GEOMETRI_RAPORU.md` içindedir.
