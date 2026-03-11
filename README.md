# Instagram İtiraf Reels Otomasyonu 🚀

Bu proje, itirafları otomatik olarak profesyonel görünümlü Instagram Reels ve Story videolarına dönüştüren, otomatik paylaşım ve etkileşim özelliklerine sahip gelişmiş bir otomasyon sistemidir.

## ✨ Öne Çıkan Özellikler

### 📱 Modern Yönetim Paneli
- **Dashboard Altyapısı:** 4 kartlı modern ana ekran üzerinden tüm modüllere erişim.
- **Çoklu Hesap Desteği:** Birden fazla Instagram hesabını tek panelden yönetme ve bilgilerini UI üzerinden anlık güncelleme.
- **Video Yönetimi:** Üretilen videoları filtreleme (Bekleyen/Paylaşılan), silme ve açıklama metinlerini (caption) tek tıkla kopyalama.

### 🎬 Profesyonel Video Üretimi
- **Düşük Bellek (Low-RAM) Modu:** Kareleri diske yazarak RAM tüketmeden üretim yapabilen, uzun süreli kullanımlarda donma yapmayan altyapı.
- **Canlı İlerleme Takibi:** Üretim sırasında `%25`, `%50` gibi ilerleme çubukları (ASCII Bar) ve adım adım log raporlama.
- **Emoji Desteği:** Apple Color Emoji entegrasyonu ile renkli ve sorunsuz emoji gösterimi.
- **Hibrit Ses Birleştirme:** FFmpeg ile doğrudan ses bindirme sayesinde %100 müzikli ve stabil videolar.

### 🎵 Akıllı Müzik Sistemi
- **Otomatik YouTube İndirici:** İtirafın temasına (Vibe) göre YouTube'dan telifsiz, kısa ve en uygun müzikleri otomatik bulur ve indirir.
- **Vibe Eşleşmesi:** 20+ kategori (İlişki, Aldatma, Eski Sevgili, İhanet vb.) için önceden tanımlanmış müzik duyguları.

### 🤖 Gelişmiş Bot ve Paylaşım Mantığı
- **Tekli Üret & Paylaş:** Anlık itirafları üretip hiç beklemeden paylaşma özelliği.
- **Toplu Üretim & Zamanlama:** Yüklenen JSON verilerini sıraya alır, videoları üretir ve her paylaşım arasına 25-45 dakika arası rastgele süre koyarak "insansı" davranış sergiler.
- **Story CTA (Eylem Çağrısı):** Takipçilerden itiraf istemek için Premium gradyan ve Glassmorphism efektli Story jeneratörü.
- **Akıllı Retry:** Instagram 500 hatalarına ve hız sınırlarına karşı exponential backoff (artan bekleme süresi) mekanizması.

## 🛠 Kurulum

1. **Depoyu Klonlayın:**
   ```bash
   git clone <repo-url>
   cd instagram-itiraf-reels
   ```

2. **Bağımlılıkları Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Sistem Gereksinimleri (FFmpeg):**
   Müzik ve video birleştirme işlemleri için sisteminizde **FFmpeg** yüklü olmalıdır.
   - **macOS:** `brew install ffmpeg`
   - **Windows:** [ffmpeg.org](https://ffmpeg.org/download.html) üzerinden indirin.

4. **Yapılandırma (.env):**
   Panelin **Ayarlar** sekmesinden veya manuel olarak `.env` dosyasından bilgilerinizi girin:
   ```env
   IG_USERNAME=email@example.com
   IG_PASSWORD=sifreniz
   PAGE_NAME=gizli_itiraf_edenler
   ANTHROPIC_API_KEY=sk-ant-... (Claude Düzenleme için)
   ```

## 🚀 Başlatma

### Yerel Sunucuyu Çalıştırın:
```bash
python api.py
```
Tarayıcınızda `http://localhost:8000` adresine giderek Dashboard üzerinden yönetime başlayabilirsiniz.

## 📁 Dosya Yapısı
- `api.py`: FastAPI backend ve modüler yönetim sistemi.
- `video_generator.py`: Gelişmiş Low-RAM video ve story motoru.
- `music_downloader.py`: YouTube üzerinden dinamik müzik indirici.
- `instagram_bot.py`: Paylaşım, takip ve DM otomasyon motoru.
- `production_manager.py`: Üretim kuyruğu ve canlı log yöneticisi.
- `muzik/`: Vibe bazlı otomatik oluşturulan müzik kütüphanesi.

## ⚠️ Güvenlik ve Notlar
- Hesabınızın sağlığı için bot işlemler arası bekleme sürelerini otomatik ayarlar.
- **Giriş Sorunu:** `challenge_required` hatası alırsanız `python login_fix.py` aracını kullanarak etkileşimli giriş yapabilirsiniz.
- Videolar paylaşıldıktan sonra disk alanı kazanmak için otomatik temizlenir.
