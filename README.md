# Instagram İtiraf Reels Otomasyonu 🚀

Bu proje, itirafları otomatik olarak görselleştirip Instagram Reels olarak paylaşan bir otomasyon sistemidir. Web paneli üzerinden JSON yükleyerek toplu üretim yapabilir veya botu çalıştırarak gelen DM'leri otomatik videoya dönüştürebilirsiniz.

## ✨ Özellikler
- **Web Panel:** Videoları yönetin, botu başlatın/durdurun ve canlı logları izleyin.
- **Hızlı Üretim (JSON):** Toplu itiraf verilerini yükleyin, videolar hemen üretilsin ve 30'ar dakika ara ile paylaşılsın.
- **DM Botu:** Gelen itiraf mesajlarını (`itiraf:` ile başlayan) otomatik olarak videoya dönüştürür.
- **Otomatik Silme:** Paylaşılan videolar depolama alanı kazanmak için hem yerelden hem de sistemden otomatik temizlenir.
- **Akıllı İşleme:** Claude API ile metin düzeltme, kategori belirleme ve etkileşimli caption üretimi.

## 🛠 Kurulum

1. **Depoyu Klonlayın:**
   ```bash
   git clone <repo-url>
   cd instagram-itiraf-reels
   ```

2. **Gerekli Kütüphaneleri Yükleyin:**
   *(Python 3.10+ önerilir)*
   ```bash
   pip install -r requirements.txt
   ```

3. **FFmpeg Kurulumu:**
   Video işlemleri için sisteminizde FFmpeg yüklü olmalıdır.
   - **macOS:** `brew install ffmpeg`
   - **Windows:** [ffmpeg.org](https://ffmpeg.org/download.html) üzerinden indirip PATH'e ekleyin.
   - **Linux:** `sudo apt install ffmpeg`

4. **Yapılandırma (.env):**
   Kök dizinde `.env` dosyası oluşturun ve bilgilerinizi girin:
   ```env
   IG_USERNAME=email@example.com
   IG_PASSWORD=sifreniz
   PAGE_NAME=itiraf.sayfasi
   ANTHROPIC_API_KEY=sk-ant-... (Opsiyonel: Claude kullanmak istemiyorsanız boş bırakın)
   ```

## 🚀 Çalıştırma

### Web Panelini Başlatın:
```bash
python api.py
```
Ardından tarayıcınızda `http://localhost:8000` adresine gidin.

### Botu Başlatın:
Panel üzerinden **"DM Botu"** sekmesine gelip **"Botu Başlat"** butonuna basmanız yeterlidir. Alternatif olarak terminalden:
```bash
python main.py --bot
```

## 📁 Dosya Yapısı
- `api.py`: FastAPI backend ve Web Panel sunucusu.
- `instagram_bot.py`: Instagram etkileşim ve paylaşım motoru.
- `video_generator.py`: Görsel ve video üretim mantığı.
- `production_manager.py`: Toplu üretim ve log yönetimi.
- `muzik/`: Kategori bazlı müziklerin bulunduğu klasör.
- `output/`: Üretilen videoların geçici olarak tutulduğu yer.

## ⚠️ Önemli Notlar
- Instagram hesabınızda **İki Faktörlü Doğrulama (2FA)** varsa, bot giriş yaparken sorun yaşayabilir. Uygulama şifresi kullanmanız veya 2FA'yı geçici olarak kapatmanız önerilir.
- Videolar paylaşıldıktan sonra otomatik olarak silinir.
