# StatikAI 3B masaüstü prototipi — 8 Kasım 2026

Kullanıcı çok katlı betonarme ve ahşap çerçeve görsellerine benzer sistemleri
hesaplayan bir uygulama istedi; elinde yalnızca iki resim olduğunu belirtti.
Resimlerde ölçek, kesit, malzeme, yük ve birleşim bilgileri yok. Bu nedenle
fotoğrafların hesabı yapılmadı. Ayrı bir elle tanımlanan düzenli 3B çerçeve
prototipi geliştirildi. Önceki görüntü araştırmasının OCR ve görüntüden çözüm
fazları tamamlanmış sayılmadı. Pilot CNN ve sabit dedektör protokolü değiştirilmedi.

## Çalışan özellikler

- Tkinter masaüstü pencere; beton/ahşap örnekleri ve kat, açıklık, kesit, E,
  Poisson, birim hacim ağırlığı, alan yükü ve yatay yük girişleri.
- İki yönde düzenli aks, rijit birleşimler, ankastre/mafsallı taban, öz ağırlık.
- Döndürülebilir 3B çubuk görünümü; büyütülmüş düğüm deplasmanlarını birleştiren
  kesikli çizgiler (eleman boyunca gerçek eğri şekil değiştirme gösterimi değildir).
- Düğüm deplasmanları/dönmeleri, altı mesnet tepkisi, N, Vy, Vz, My, Mz, T
  maksimum mutlak değerleri ve eleman boyunca 31 noktalı diyagramlar.
- JSON model kaydet/aç ve sonuç dışa aktarma. Parametre değişince eski sonuçlar silinir.
- Windows başlatıcı ve masaüstü kısayolu; eski sembol demosuna ayrı düğme.

3B hesap motoru **PyNiteFEA 3.2.1** sonlu eleman analizidir. Bu sonuçlar bir
AI modelinin görüntüden tahmini değildir. Görüntüdeki yapılarla bağlantı kurulmadı.

## Varsayımlar, birimler ve kapsam

Global Y düşey; koordinatlar m, yükler kN, momentler kNm, E girişi GPa,
kesit girişi cm, sonuç deplasmanı mm, dönmeler rad. E dönüşümü 10^6 ile yapılır.
Kesit alanı ve iki atalet momenti dikdörtgen için analitiktir. Saint-Venant J,
Oasys GSA'daki dikdörtgen yaklaşımıyla hesaplanır; polar atalet momenti kullanılmaz.
Kolonların dikdörtgen kesit yönü motorun yerel eksenlerine göredir; dönük kesit
ve farklı elemanlara farklı malzeme/kesit tanımlama arayüzü yoktur.

Tek katsayısı 1.0 olan kullanıcı yük birleşimi, birinci mertebe küçük deplasman,
izotrop doğrusal elastik Euler-Bernoulli çubuklar, brüt kesitler ve rijit birleşimler
kullanılır. Kayma deformasyonu, beton çatlaması, malzeme/plastik doğrusal olmayanlığı,
P-Delta, döşeme/perde/kabuk/rijit diyafram ve temel-zemin etkileşimi modellenmez.
Ahşap örneği de izotroptur; ahşap anizotropisi ve bağlantı esnekliği modellenmez.

Alan yükü tesir alanıyla düğümlere düşey kuvvet olarak eşdeğerlenir. Toplam düşey
kuvvet ve moment korunur, ancak **döşeme yükünün kirişlerde oluşturduğu eğilme
yoktur**. Kirişlerde öz ağırlıktan ve çerçeve etkileşiminden iç kuvvetler oluşabilir.
Yatay yükler her kata elle girilir, kat düğümlerine eşit dağıtılır; kütle, spektrum,
TBDY deprem analizi veya otomatik rüzgâr hesabı yapılmaz. Yönetmelik yük birleşimleri,
donatı, kapasite, sehim sınırı veya güvenli/güvensiz kararı verilmez.

## Gerçek doğrulama

Windows, Python 3.13.12; PyniteFEA 3.2.1, NumPy 2.5.4, SciPy 1.18.1,
Matplotlib 3.11.2. `audit_results/desktop_versions.json` sürümleri kaydeder.

- Tam otomatik test: **41 passed**. 15 yeni test; iki yönde konsol eğilmesi
  PL³/(3EI), eksenel uzama PL/(EA), burulma TL/(GJ), kesit eksenleri, düğüm ve
  eleman sayıları, toplam yük, kuvvet/moment dengesi, sıfır yük, doğrusal ölçekleme,
  kare plan 90° simetrisi ve 8 geçersiz girdi durumu. Eski 26 test de geçti.
- `pip check`: **No broken requirements found.**
- Gerçek Tkinter arayüz testi: dört sekme açıldı; 63 düğüm, 126 eleman, 9 mesnet
  satırı oluştu; seçili son elemanın 31 noktalı diyagramı ve büyütülmüş düğüm
  deplasmanı çizimi kontrol edildi. Çıkış kodu 0. Son testte pencere zoomed
  durumundaydı. PNG yalnızca model grafiği kaydıdır, tam pencere ekran görüntüsü değildir.
- Üç entegrasyon modeli çözüldü. Düşey tepki toplamı, modelin yük listesinden
  bağımsız uzunluk/alan/ağırlık formülleriyle kontrol edildi. Sonuçlar aşağıda.

| Örnek (fotoğraflar değildir) | Düğüm / eleman | En büyük düğüm deplasmanı (mm) | Düşey tepki toplamı (kN) |
|---|---:|---:|---:|
| 6 kat, 2x2 açıklık, beton için örnek E | 63 / 126 | 6.505394 | 4263.000 |
| 2 kat, 2x1 açıklık, ahşap için örnek E | 18 / 26 | 2.213774 | 225.650 |
| 2 kat, 1x1 açıklık, mafsallı taban, iki yatay yön | 12 / 16 | 1.844430 | 431.000 |

İlk örnekte 2400 kN kat yükü + 1863 kN çubuk öz ağırlığı = 4263 kN.
Tüm üç örnekte maksimum kuvvet denge artığı 1.33e-11 kN'den, maksimum moment
artığı 1.61e-10 kNm'den küçüktür. Denge tek başına gerçek yapı doğruluğunu
kanıtlamaz. Çok katlı sonuçlar başka bir ticari yazılımla karşılaştırılmadı.
Tüm geometriler/yükler örnektir; bu deplasmanlar gerçek binalara atfedilemez.

Ham kanıt: `audit_results/logs/desktop_final_tests.*`, `desktop_gui_final.*`,
`desktop_dependencies.*`, `desktop_integration.*`, `audit_results/desktop_smoke.json`,
`audit_results/desktop/integration_summary.json` ve aynı klasördeki tam sonuç JSON'ları.
Tekrarlama: README'deki kurulumdan sonra `python -m pytest -q`,
`python tools/verify_desktop.py`, `python statikai_desktop.py --smoke-test`.

## Platform ve kurulum

Windows çalıştırıldı. macOS/Linux için kaynak Python/Tk/Matplotlib tabanlıdır;
`.cmd` ve `.lnk` yalnız Windows içindir, diğerlerinde Python komutu kullanılır.
Tk ve grafik oturumu gerekir; Linux'ta sistemin python3-tk paketi gerekebilir.
Bu iki platformda çalıştırılmışlık veya paketlenmiş .exe/.app iddiası yoktur.
PyNite'nin yeni NumPy gereksinimi eski Intel macOS CNN ortamındaki NumPy<2 ile
uyuşmaz; ayrı 3B ortam gerekir ve uygun wheel/çalışabilirlik doğrulanmadı.

Masaüstü başlatıcı masaüstü bağımlılıklarını kurabilir; ilk kurulum internet ister.
Bu bilgisayardaki `.statikai-python.txt` yerel sanal ortamı seçer; dağıtılan ZIP'e
makineye özgü bu dosya ve sanal ortam eklenmez. Başka bilgisayarda Python kurulumu
ve bağımlılıklar gerekir. Eski sembol demosu ayrıca `requirements.txt` ister.

## Sonraki geliştirme sırası

Önce danışmanla doğrulanmış yük yolu (döşemeden kirişe dağıtılmış yük), yerel
kesit yönleri, birden çok yük durumu/birleşimi ve bağımsız çözücü karşılaştırması.
Ardından eğitim amaçlı kat deplasmanı/ötelenme kontrolleri. Görüntü araştırması
ayrı olarak Faz 3 OCR, konum–değer eşleştirme ve insan onaylı geometri çıkarma
sırasını izlemeli. Tek resimden eksik parametreler tahmin edilip gerçek hesap
verisi olarak kullanılamaz. Bu prototip tüm bina tasarım yazılımı değildir.

## Birincil teknik kaynaklar

- [PyNite FEModel3D](https://pynite.readthedocs.io/en/latest/FEModel3D.html)
- [PyNite üye modeli](https://pynite.readthedocs.io/en/latest/member.html)
- [Oasys GSA dikdörtgen kesit teorisi](https://docs.oasys-software.com/structural/gsa/version/10.3.1/references-theory/rectangular-sections/)
