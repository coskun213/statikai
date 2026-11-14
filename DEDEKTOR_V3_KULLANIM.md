# StatikAI V3 modelini kullanma

Bu paket iki eğitilmiş aday, eski donmuş referans, gerçek sonuçlar ve yeni önceden kilitlenmiş
sentetik test verisini içerir. Yeni testte toplam F1: Tiny yeniden eğitim 0.9036,
LiteFPN 0.8667, eski donmuş Tiny 0.4403, OpenCV 0.3338. Yeni Lite mimarisi toplam
F1'de üstün çıkmadı; roller kaçırması daha az, yanlış roller tespiti daha fazla.
Ayrıntı: DEDEKTOR_V3_RAPORU.md. Model başarısı gerçek yapı güvenliği değildir.

## Tek görüntüden kutu çıkarma

Proje/paket kökünde, mevcut bağımlılıkları içeren Python ile:

```powershell
python detect_trained_symbols.py --model tiny --run experiments/detector_v3_20261108_01 --image "C:/tam/yol/kiris.png" --out work/benim_tespitim.json
python detect_trained_symbols.py --model lite --run experiments/detector_v3_20261108_01 --image "C:/tam/yol/kiris.png" --out work/benim_lite_tespitim.json
```

Sınıf 0=mafsal, 1=hareketli mesnet, 2=kuvvet oku. Kutu [x0,y0,x1,y1] orijinal
resimdeki piksel sınırlarıdır. CSV, sembol kutusu veya fizik değeri görüntünün
yanında gerekli değildir. Mevcut çıktı dosyasının üzerine yazılmaz.
OCR ve RA/RB çözümü yok; review_required=true insan incelemesi gerektirir.
Mevcut masaüstü sembol demosu otomatik değiştirilmedi.

Bu bilgisayardaki mevcut proje için ortam yolu `.statikai-python.txt` içindedir.
Powershell'de `$py = Get-Content .statikai-python.txt` sonrası `python` yerine
`& $py` kullanılabilir. Yerel ortam yolu dağıtım paketine eklenmez.

Bağımlılıklar mevcut requirements.txt içindedir; yeni paket gerekmedi. Ölçülen
ortam Python 3.13.12, torch 2.15.0+cpu, OpenCV 5.0.0.93. Fiziksel RTX 4060
bulunuyor fakat kurulu torch CPU sürümüdür; GPU eğitimi yapılmadı. Diğer platform
ve sürümler bu deneyde doğrulanmadı.

## Dosyalar ve sonuçlar

- experiments/detector_v3_20261108_01/lite/best.pt: LiteFPN, seçilen epok 13.
- experiments/detector_v3_20261108_01/tiny/best.pt: yeniden eğitilen Tiny, epok 18.
- evaluation/metrics.json ve per_image_metrics.json: P/R/F1, IoU, koşul/sınıf ölçümleri.
- evaluation/detections.csv ve predictions_original_pixels.json: tahmin koordinatları.
- evaluation/failures/: Lite modelinin gerçekten hata yaptığı 20 görüntü.
- evaluation/failure_contact_sheet.png: toplu hata görünümü.
- evaluation/roller_false_negatives*.json: iki adayın roller FN kayıtları.
- preregistered_plan.json, data_protocol.json, evaluation/frozen_thresholds.json: eğitimden/testten önce sabitlenen protokol.

Bağımsızlık yeni fizik aileleri ve ayrı çizim kodu düzeyindedir. Veriler aynı yazarın
sentetik çizimleridir; gerçek dış kaynak genellemesi olarak sunulmamalıdır.

## Tekrar eğitim

Paket eğitim görüntülerini tekrar içermez. Daha önce teslim edilen V2 paketinden
`dataset_dimensions_v2/` klasörünü buraya eklemek gerekir; dosya manifesti doğrulanır.
Yeni deney için boş ve yeni bir run klasörü oluşturup preregistered_plan.json dosyasını
oraya kopyalayın. Her aşamada `--run experiments/yeni_deney_01` verin:

```powershell
python train_detector_v3.py prepare --run experiments/yeni_deney_01
python train_detector_v3.py pilot --run experiments/yeni_deney_01
python train_detector_v3.py train-lite --run experiments/yeni_deney_01
python train_detector_v3.py train-tiny --run experiments/yeni_deney_01
python train_detector_v3.py evaluate --run experiments/yeni_deney_01
```

Mevcut run aşamaları üzerine yazmayı reddeder. Bu yeni test sonuçlarına bakarak
aynı testte model/eşik ayarı yapmayın; sonraki iyileştirmede yeni kilitli test gerekir.
