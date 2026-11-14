# Codex'e yapıştırılacak talimat

StatikAI adlı TÜBİTAK 2209-A araştırma projesinin kod paketini incele ve mevcut testleri çalıştır. Kodun bilimsel doğruluk ve veri sızıntısı yönünden denetimini yap. Mevcut `train_pilot.py` yalnızca gerçek anotasyon kutuları verilmiş görüntü parçalarını sınıflandırıyor; bunu uçtan uca nesne tespiti veya çözüm olarak gösterme.

**Bir sonraki geliştirme hedefi:** Statikçe belirli, iki basit mesnetli ve iki düşey tekil yüklü kiriş çizimleri için deneysel bir görsel yorumlayıcı geliştirmek. Bunu aşağıdaki basamaklarla yap:

1. Veri üreticisini kiriş başlangıç/bitiş noktalarının görüntü üzerindeki konumunu, boyutu ve stili değiştirecek şekilde genişlet. Fiziksel olarak eşdeğer varyantlarda yük ve mesnet değerlerini değiştirme. Fiziksel müdahale varyantlarında yalnızca belirlenen yük konumunu değiştir. Her değişiklikte analitik referansları yeniden hesapla.
2. Problemin tüm varyasyonlarını **problem ID düzeyinde** aynı train, val veya test grubunda tut. Etiketleri gerçek çözümlerle birim test üzerinden doğrula.
3. Hafif nesne tespiti yaklaşımıyla iki mesnet ve kuvvet oklarının diyagramdaki konumunu kendiliğinden bulan bir model eğit. PyTorch veya uygun açık kaynak araçlar kullan; ön-eğitilmiş ağırlık kullanırsan açıkça belgele. İlk pilotu CPU'da küçük ölçekte çalıştır.
4. Ayrı OCR modülüyle sayısal etiketleri ve birimleri oku; hangi etiketin hangi yüke/mesafeye ait olduğunu geometrik olarak eşleştir. OCR ile tespit başarılarını **ayrı** ölç. Modelin okuyamadığı verilerde keyfi değer üretme.
5. Geçerli şekilde ayrıştırılmış kiriş bilgisinden RA/RB hesaplayan mevcut analitik statik çözümü entegre et. Girdilerin geçerliliğini kontrol et (0<x1<x2<L, P>0). Gözlenen fiziksel yük bilgileri hatalıysa denge artık değerinin tek başına hatayı yakalayamayacağını belgele.
6. Klasik görüntü işleme+OCR temel yöntemi, öğrenilmiş model+OCR yöntemi ve önerilen belirsizlik/fizik denetimi içeren yöntemle **aynı sabit testte** karşılaştırma yap.
7. Ölçümler: nesne tespit precision/recall/F1, OCR tam okuma, tam mesnet tepkisi çözüm oranı, RA/RB mutlak hata, aynı problemin eşdeğer çizim tutarlılığı, fiziksel değişime duyarlılık, hata reddetme oranı ve yanlış alarm. Testten eşik/parametre ayarlama yapma.
8. Tüm sonuçları CSV/JSON olarak kaydet. Test verisi yalnızca nihai değerlendirme için olsun. Hatalı veya yapılamamış deneyleri başarılmış gibi raporlama.
9. README ve otomatik testleri güncelle. İlk çıktı olarak veri üretici iyileştirmesi ve 10 problem üzerinden çalışan uçtan uca tanılama raporu üret. GPU zorunluysa CPU/alternatif yöntem planını yaz.

**Sınırlamalar:** Bu proje gerçek yapı tasarımı, güvenlik kararı veya statik mühendis kontrolü için kullanılmayacak. Uygulamanın araştırma amaçlı ve dar kapsamlı olduğunu vurgula.
