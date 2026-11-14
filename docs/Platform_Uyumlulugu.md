# Platform uyumluluğu

## Gerçekte çalıştırılan

Windows 11 x86_64, Python 3.13.12, CPU. Kurulu sürümler ve font yolu
`audit_results/environment.json`; tam paket dökümü
`audit_results/environment-windows-py313.lock.txt` içindedir. Bu dosya sadece
ölçüm ortamının kaydıdır; diğer platformlarda zorunlu kilit dosyası değildir.

Linux ve macOS üzerinde bu oturumda çalıştırma yapılmadı. Aşağıdaki notlar kod
incelemesi ve bağımlılık belgelerine dayanır; test edilmiş uyumluluk iddiası değildir.

## Kod değişiklikleri

- Sabit `/usr/share/fonts/...` yolu kaldırıldı. Sistem fontları sırayla aranır;
  bulunamazsa Pillow'un gömülü fontu kullanılır. `STATIKAI_FONT` ile belirli
  bir font dosyası seçilebilir. Gerçek seçilen font veri manifestine yazılır.
- Dosya yollarında `pathlib`, metinlerde UTF-8, checkpoint yüklemede
  `map_location='cpu'` kullanılır. Modüller GPU zorunlu kılmaz.
- OpenCV headless kullanılır; pencere sistemi gerektirmez.
- Veri yükleme `num_workers=0` ile Windows multiprocessing farkından kaçınır.
- Kaynak görüntüler ve checkpointler ZIP içinde taşınabilir; `.venv` taşınmaz.
- Windows makinesinde pytest'in ortak temp dizinine erişim reddedildi. Bu
  ortamda ilk doğrulamalar `--basetemp` ile çalıştırıldı. Sonrasında
  `conftest.py` varsayılan test geçicilerini proje içinde yeni ve benzersiz
  bir dizine yönlendirecek şekilde eklendi; düz `python -m pytest -q` da sınanır.

## macOS ayrımı

Apple Silicon: uyumlu Python/PyTorch CPU paketleriyle denenmeli. MPS hızlandırma
bu prototipte uygulanmadı ve test edilmedi.

Intel macOS: resmi PyTorch x86_64 tekerlekleri 2.3 sürümünden itibaren
üretilmiyor. Bu nedenle Python 3.11 ve PyTorch 2.2.x için ayrı bir uyumluluk
yolu önerilir; NumPy <2 ve OpenCV <4.12 koşullu bağımlılıkları eklendi.
Bu kombinasyon burada kurulup çalıştırılmadı; eski PyTorch ile yeni ortamda
kaydedilmiş ağırlığın yüklenmesi de ayrıca sınanmalı. Python 3.13 ile Intel
Mac üzerinde standart kurulumun çalışacağı iddia edilmez.

Kaynaklar:
- https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690
- https://github.com/opencv/opencv-python/issues/1122
- https://pillow.readthedocs.io/en/stable/reference/ImageFont.html
- https://docs.pytorch.org/docs/2.15/generated/torch.load.html

## Doğrulama komutları

Windows:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q --basetemp=work/pytest_local
```

Linux / Apple Silicon macOS (uygun Python kurulumu sonrasında):
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q --basetemp=work/pytest_local
```

Intel macOS: aynı adımlar `python3.11` ile denenmeli. İlgili sürümler için
pip'in uyumlu wheel bulabilmesi koşuldur. Font farklılığı yeni üretilen
görüntülerin piksel özetlerini değiştirebilir; verilen veri seti korunursa
bu değişiklik test görüntülerini değiştirmez.

## Ayrı 3B masaüstü (0.3)

`requirements-desktop.txt` PyNite ve Matplotlib içindir, normal Windows Python
Tkinter'ını kullanır. Windows/Python 3.13.12 üzerinde çalıştırıldı; sürümler ve
kanıtlar `audit_results/desktop_versions.json` ve `desktop_*.log` dosyalarında.
macOS/Linux üzerinde Tk/grafik oturumu ve uygun paketler gerekir; denenmedi.
Intel Mac eski CNN NumPy<2 ortamına yeni PyNite kurulamaz; ayrı ortam gerekir.
`.cmd` Windows'a özgüdür; diğer sistemlerde `python statikai_desktop.py` kullanılır.
Kaynak kod sunulur; taşınabilir bağımsız .exe/.app üretildiği iddia edilmez.
