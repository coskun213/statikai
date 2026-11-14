# StatikAI — Doğrulanabilir geliştirme aşamaları

## Faz 0 — Depoyu doğrula
- Giriş: mevcut 200 görüntü, `ground_truth.csv`, 4 test.
- Çıktı: bütün testler geçer; veri/etiket uyumu raporu, bağımlılık ve font yolu problemleri.

## Faz 1 — Veri ve genellenebilirlik
- 500 temel problem, her biri fiziksel eşdeğer varyantlar ve fiziksel değişim varyantı.
- Kiriş ve yazı konumlarını değiştir, ikinci bağımsız çizim stili kullan.
- Ayrımı `problem_id` bazında yap ve fiziksel konfigürasyonun tekrar etmemesini doğrula.
- Çıktı: yeni veri seti, QA raporu, unit testler.

## Faz 2 — Tam diyagramdaki sembolleri otomatik bul
- Önceden kesilmiş yamalara dayanma; tam görüntüden mesnet/kuvvet kutularını kendin tahmin et.
- Klasik OpenCV yaklaşımı ile hafif öğrenilmiş dedektörü kıyasla.
- Çıktı: sabit testte bbox precision/recall ve hatalı görüntü örnekleri.

## Faz 3 — OCR ve geometrik ilişkilendirme
- Kuvvet değerlerini, metre etiketlerini OCR ile oku.
- Hangi kuvvetin hangi oka ait olduğunu geometrik kurallarla eşleştir.
- Belirsiz/okunamayan girdilerde keyfi değer üretme, 'yeniden inceleme gerekli' işaretle.
- Çıktı: OCR field-level accuracy, tam veri çıkarma oranı.

## Faz 4 — Statik hesaplama + fizik denetimi
- Geçerli girdi şeması oluştur ve analitik RA/RB hesabını entegre et.
- Denge, birimler, hatalı sıralama ve eksik veri kontrolleri ekle.
- Çıktı: tam diyagramdan reaksiyon tahmini için hata/başarı tablosu.

## Faz 5 — Bilimsel deney
- Üç yaklaşımı kıyasla: klasik görüntü işleme+OCR; yapay zekâ+OCR; aynı modele fizik/belirsizlik denetimi.
- Eşdeğer çizimlerde kararlılık ve fiziksel değişimde duyarlılık testleri.
- Hatalı kabul, ret, yanlış alarm ve bağımsız çizim stili performansı.
- Çıktı: gerçek CSV/JSON sonuçları, güven aralıkları, hata analizi, yeniden üretim yönergesi.

## Faz 6 — Basit arayüz (öncelik düşük)
- Kullanıcı PNG yükler; algılanan bilgi, RA/RB, güvenilirlik uyarısı ve model sınırları gösterilir.
- UI yalnızca önceki deneysel modüller doğrulandıktan sonra geliştirilir.

Önce Faz 0 tamamlanmalı. Başvurudan önce büyük eğitimi bitirme zorunluluğu yoktur.

## 8 Kasım 2026 denetim ve prototip durumu

- Faz 0: dört orijinal test dahil toplam 26 otomatik test geçti. Font,
  kalıcı fiziksel girdi doğrulaması, NaN/sonsuzluk ve tahmin kapsaması düzeltildi.
- Faz 1: 500 aile/2500 görüntü/10000 kutu üretildi. İki sentetik gösterim stili
  ve problem bazlı ayrım QA'dan geçti. Dış kaynak gerçek çizim eklenmedi.
- Faz 2: küçük CPU dedektörü eğitildi; OpenCV ile aynı sabit 250 test
  görüntüsünde karşılaştırıldı. İkinci stilde özellikle hareketli mesnetler
  başarısız; genel diyagram okuma tamamlanmış değildir.
- Faz 3: OCR ve geometrik ilişkilendirme henüz uygulanmadı.
- Faz 4: analitik yardımcı sağlamlaştırıldı; görüntüden çözüm entegrasyonu yok.
- Faz 5 ve Faz 6: henüz uygulanmadı.

Sonraki çalışmalar test görüntülerine göre ayar yapmadan, yeni eğitim ve
validasyon örnekleriyle planlanmalı. Ayrıntı ve ham kanıtlar:
`docs/Denetim_ve_Prototip_Raporu.md`.

## Kullanıcının ek isteği — elle tanımlanan 3B masaüstü prototipi

Görüntü projesinden ayrı olarak masaüstü arayüz ve doğrusal elastik düzenli
3B çerçeve çözümü eklendi. 41 otomatik test ve gerçek GUI/entegrasyon kontrolleri
geçti. Bu, yukarıdaki OCR, görüntüden çözüm veya görüntü yükleyen Faz 6 arayüzünün
tamamlandığı anlamına gelmez. Alan yükleri düğümlere aktarılır; döşemeden kirişe
aktarılan yük eğilmesi, yönetmelik ve boyutlandırma yoktur. Ayrıntı ve sıradaki
doğrulama işleri `docs/3B_Masaustu_Raporu.md` içinde.


## Faz 1 ek veri sürümü — ölçülendirilmiş V2

Hazır parametre satırını kaldıran ölçü çizgileri ve metin/sembol ilişki etiketleri
ayrı V2 verisinde hazırlanır. Aynı kaynak fizik aileleri/splitleri korunur. Bu
çalışma OCR veya görüntüden çözümün tamamlandığı anlamına gelmez. Sürüm üretimi,
gerçek denetim ve kalan eksikler `VERI_SETI_V2_RAPORU.md` içinde raporlanır.

## Faz 3 — bağımsız OCR prototipi V1.1

Metin tanıma, açık birim dönüşümü, kuvvet/ok eşleştirme ve ölçü grafından
konum çıkarma eklendi. Eksik/çelişkili/belirsiz okuma inceleme ister. Gerçek
OCR testleri, ilk başarısız güvenlik örneği, sürüm düzeltmesi, yeni test grubu
ve bilimsel sınırlar `OCR_VE_GEOMETRI_RAPORU.md` içinde kaydedildi.
Dar sentetik alan dışındaki diyagram okuma tamamlanmış sayılmaz.
Faz 4 (OCR girdilerinden statik çözüm) ve görüntü arayüzü geliştirilmedi.
Mevcut statik motoru ve elle tanımlanan 3B masaüstü modülü korundu.

## Faz 4 — doğrulanmış OCR girdilerinden kiriş tepkileri

`statikai/beam_pipeline.py` korunmuş analitik motoru çağırır; yalnız bütün
okuma/kapsam/doğrulama kontrolleri geçtiğinde RA/RB ve denge artıkları üretilir.
Kısmi verilerden tamamlama yoktur. Gerçek deney ve eksikler `UCTAN_UCA_RAPORU.md`
içinde; yeni 2B pencere `statikai_beam_app.py` içindedir. Bu, genel diyagram
okuma, gerçek yapı hesabı veya tüm Faz 5 bilimsel karşılaştırmalarının tamamlanması değildir.
