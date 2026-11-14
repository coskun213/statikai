# Görüntüden kiriş tepkilerine — deneysel uçtan uca sürüm

`statikai/physics.py` değiştirilmeden görüntü tespiti, OCR ve ölçü grafına
bağlandı. Önceki `read_beam_diagram.py` hâlâ yalnız okuma komutudur.
Yeni hesaplama girişi `solve_beam_image.py`, ayrı 2B pencere
`statikai_beam_app.py` dosyasıdır. Eski 3B uygulama korunur.

## Pencereyi açma

Windows'ta proje klasöründeki **StatikAI_2B_Baslat.cmd** dosyasını açın.
`Görüntü yükle` ile PNG/JPEG seçin; ardından
`Algıla → Oku → Doğrula → Hesapla` düğmesine basın. Dedektör ve OCR ilk
çalışmada yüklenir; arayüz bunları ayrı iş parçacığında çalıştırır.
Okunan sembol/metin kutuları önizlemede, girdiler, tepkiler, denge ve uyarılar
alt alanda görünür. Durdurulan problem için RA/RB gösterilmez.

Her analiz otomatik olarak `work/beam_pipeline/` altında benzersiz JSON
dosyasına yazılır. `JSON farklı kaydet` ile başka yere de kaydedilebilir;
eski dosyanın üzerine yazılmaz. Alanlar otomatik okunur; eksik değeri
tamamlama veya uyarıyı atlayarak hesaplama düğmesi yoktur.

Başlatıcı önce önceki yerel Python yolunu ve `.venv` ortamını arar.
Gerekli paketler yoksa aşağıdaki iki requirements dosyasını kurar.
Python 3.11+ ve Tcl/Tk içeren normal Python kurulumu gerekir.

Terminalden, proje klasöründe:

```powershell
python -m pip install -r requirements.txt -r requirements-ocr.txt
python statikai_beam_app.py
```

Windows sanal ortamında `python` yerine `.\.venv\Scripts\python.exe`,
Linux/macOS'ta `.venv/bin/python` kullanılır. Linux'ta Tk ayrıca işletim
sistemi paketi olabilir; macOS/Linux üzerinde bu sürüm çalıştırılmadı.
Yeni üçüncü taraf bağımlılık eklenmedi. Yalnız 2B hat için Pynite gerekmez.

## Komut satırında tek görüntü

```powershell
python solve_beam_image.py --image dataset_dimensions_v2/images/beam_0000_v0.png --out work/ilk_cozum.json
```

`--image` kendi dosyanız olabilir. `--out` mevcutsa komut durur; başka ad seçin.
`--detector-run` ve `--ocr-models` ile taşınmış ağırlık konumları verilebilir.
Model ve eşikler önceki sabit Tiny/OCR sürümleridir; bu görevde yeniden
eğitim veya eşik ayarı yapılmadı. Paketlenen OCR ağırlıkları varsa çıkarım
yereldir; eksik olduklarında RapidOCR ilk kullanımda indirme yapabilir.

## İzin verilen alan

Yatay tek açıklıklı kiriş, **solda mafsallı, sağda hareketli mesnet**, açıklık
içinde iki aşağı yönlü düşey tekil kuvvet. Birimler N/kN ve mm/cm/m;
pozitif değerler ve `0 < x1 < x2 < L` zorunludur.

İki yükten farklı sayıda yük, ters mesnet yönü, ankastre, konsol, yayılı yük,
moment ve farklı yönlü kuvvetler için otomatik çözüm desteklenmez. OCR,
geometri veya kapsam kontrolü bunları belirlediğinde işlem durur. Kapsam
kontrolü bir evrensel nesne tanıyıcı değildir; her olası kapsam dışı sembolün
yakalanacağı iddia edilmez. Gerçek çizimler, el yazısı ve fotoğraf perspektifi
ile dış doğrulama henüz yoktur.

## İşlem sırası ve durdurma

1. PIL görüntüyü açar; bozuk/okunamayan dosya sonuç yerine inceleme kaydı üretir.
2. Korunmuş Tiny dedektörü bir mafsal, bir hareketli mesnet ve iki kuvvet kutusu
   bulmalıdır. En iyi iki kuvveti keyfî seçerek ek yükü atma yoktur.
3. RapidOCR ham metni, kaynak kutusunu ve skorunu üretir; açık birimler ayrıştırılır.
4. Korunmuş geometrik eşleştirme kuvvet/metin ve ölçü uçlarını bağlar. Konum
   ölçü zinciri grafından bulunur; pikselden metre değeri tahmin edilmez.
5. Yeni `beam_scope.py` ok başının aşağıda genişlemesini, mesnedin iki yana
   açılan üçgenini, hareketli mesnet tekerlek halkalarını ve yük bölgesindeki
   açıklanmayan mürekkebi kontrol eder. Kararsız bulguda hesap durur.
6. `beam_pipeline.validate_extraction` yalnız eksiksiz `extracted_inputs`
   kabul eder. `review_required=true`, herhangi bir okuma uyarısı veya
   eksik kaynak, yanlış birim, çelişkili ölçü, eksik/sonlu olmayan değer
   olduğunda çözücü **çağrılmaz**. Kısmi alanlardan tamamlama yapılmaz.
7. Ham OCR yeniden ayrıştırılır; birim/güven/kaynak ve graf değerleriyle
   sayısal girdi tutarlılığı yeniden denetlenir. Semboller ve mesnet türleri
   yeniden kontrol edilir. Geçerli veri mevcut `physics.reactions` fonksiyonuna girer.
8. `physics.residuals` ile kuvvet ve moment dengesi sınanır. Sayısal hata veya
   tolerans aşımı varsa tepkiler yayınlanmaz; RA/RB `null` kalır.
9. Uyarılar, aşama durumları, süreler, kaynaklar ve sonuç JSON'a kaydedilir.

## Denklemler ve denge toleransları

```
RB = (P1*x1 + P2*x2) / L
RA = P1 + P2 - RB
F_artik = RA + RB - P1 - P2          [kN]
M_artik = RB*L - P1*x1 - P2*x2     [kN m]
```

Analitik motor sayısal kararlılık için eşdeğer `P*(x/L)` ve `math.fsum`
hesabını kullanır. Kuvvet toleransı `1e-9 + 1e-10 * kuvvet_ölçeği` kN,
moment toleransı `1e-8 + 1e-10 * moment_ölçeği` kN m'dir. Ölçekler mutlak
terimlerin toplamı ve en az 1'dir. Gerçek artıklar, toleranslar ve boyutsuz
normalize artıklar JSON'da bulunur.

**Denge bir görüntü doğruluk testi değildir.** Örneğin 8 kN yanlışlıkla
18 kN okunursa, çözücü 18 kN için tamamen dengeli ama gerçek probleme göre
yanlış tepkiler üretebilir. Birim testinde bu durum özellikle gösterilir.
Çıktı bunu `interpretation_truth_status: not_independently_verified` olarak
belirtir. İnceleme gerekmemesi mühendislik güvenliği veya doğru okuma garantisi değildir.

## JSON alanları

- `status`: `computed` veya `review_required`.
- `extraction`: tam ham dedektör/OCR, kaynak kutuları, skorlar, ölçü grafı ve
  önceki okuma uyarıları. Bu alt nesnenin `static_solution=not_run` alanı
  yalnız **okuma aşamasının** statik motoru çağırmadığını gösterir.
- `scope_check`: ok yönü/mesnet/ek mürekkep kanıtları ve sınırlılık.
- `validated_inputs`: çözücüye giden beş SI değer; durdurulursa `null`.
- Üst düzey `static_solution`: gerçek analitik tepkiler (`RA_kN`, `RB_kN`),
  yukarı yön pozitif işaret sözleşmesi ve birimler. Durdurulursa ikisi de `null`.
- `equilibrium`: kuvvet ve moment artıkları, toleranslar, kontrol sonucu ve
  `interpretation_verified=false`. İşlem durdurulduysa `not_run`.
- `stages`, `stage_timings_seconds`: aşama durumları ve ölçülen süreler.
  Aşama durumu bir iç kontrol kararıdır; referans etiketlere göre başarım
  ölçümü ayrı deney raporundadır.
- `issues`: entegrasyon durdurma gerekçeleri. Ayrıntılı okuma/kapsam nedenleri
  ilgili alt nesnelerde de korunur.
- `physics_source_sha256`: değiştirilmeyen analitik kaynak dosyasının özeti.
- `interpretation_warning`: dengeli yanlış okuma olasılığı açıklaması.

## Deneyler ve yeniden üretim

`experiments/end_to_end_v1_20261108_01/plan.json` ve `frozen_protocol.json`
ayrı deney kaydıdır. Geliştirme yalnız ilk beş V2 eğitim ailesi ve kontrollü
birim fikstürlerinde yapıldı; doğrulama ilk on V2 val ailesi/50 çizimdir.

Yeni test 30 farklı fiziksel problem, her birinin önceden tanımlı dört
ölçülendirme düzeniyle 120 görüntüdür. Seed=22091115. Birincil problem
tablosunda önceden seçilen `variant=0` kullanılır; 120 görüntü 120 bağımsız
fiziksel problem gibi sayılmaz. Eski fizik kayıtlarıyla birebir örtüşme yoktur.
Çizimler aynı sentetik V2 üreticisindendir; dış kaynak gerçek çizim değildir.
Referans tepkiler mevcut çözücüden bağımsız Decimal denklemleriyle hazırlanır.

14 bozulmuş eğitim kopyası ayrıca güvenlik senaryolarıdır; bunların geçmesi
evrensel kapsam dışı tanıma başarısı değildir. Uçtan uca doğrulukta otomatik
kabul, beş girdinin ve iki tepkinin referansla eşleşmesini gerektirir.
Yanlış girdilerle tesadüfen doğru/dengeli tepki oluşması başarı sayılmaz.

```powershell
python -m pytest -q
python evaluate_beam_pipeline.py verify
python statikai_beam_app.py --smoke-test --image dataset_dimensions_v2/images/beam_0000_v0.png
```

Kayıtlı deney dosyaları tekrar yazılmaz. Yeni deney için ayrı sürüm/klasör
gerekir. Gerçek sayılar ve her problemde sonuç: `UCTAN_UCA_RAPORU.md`.
Bu modül araştırma prototipidir; gerçek yapı tasarımı veya güvenlik kararı için kullanılmaz.
