# Instagram Itiraf Reels Otomasyonu

Python tabanlı Instagram itiraf reels otomasyonu. DM tasarımlı video üretimi, Claude API entegrasyonu ve instagrapi ile tam otomasyon sunar.

## Kurulum

### 1. Bağımlılıkları yükle

```bash
pip install -r requirements.txt
```

### 2. Ortam değişkenlerini ayarla

```bash
cp .env.example .env
```

`.env` dosyasını düzenle:

```
IG_USERNAME=instagram_kullanici_adin
IG_PASSWORD=instagram_sifren
PAGE_NAME=itiraf.sayfasi
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Müzik ekle (opsiyonel)

`muzik/` klasörüne `.mp3` dosyaları ekle. Kategoriye göre alt klasörler oluşturabilirsin:

```
muzik/
├── iliski/     -> ilişki kategorisi müzikleri
├── aile/       -> aile kategorisi müzikleri
├── is/         -> iş kategorisi müzikleri
├── arkadaslik/ -> arkadaşlık kategorisi müzikleri
└── genel/      -> genel müzikler
```

Alt klasör yoksa `muzik/` kökündeki tüm `.mp3` dosyalarından rastgele seçilir.

---

## Kullanım

### JSON'dan toplu video üretimi

```bash
python main.py --json data.json --page itiraf.sayfasi
```

`data.json` formatı:

```json
[
  {
    "itiraf": "İtiraf metni buraya"
  },
  {
    "itiraf": "Başka bir itiraf",
    "kategori": "iliski"
  }
]
```

Kategoriler: `iliski`, `aile`, `is`, `arkadaslik`, `genel`

`kategori` alanı boş veya eksikse Claude otomatik belirler.

Çıktılar `output/` klasörüne kaydedilir:
- `itiraf_001.mp4` — video
- `itiraf_001_caption.txt` — Instagram caption

### DM otomasyon modu

```bash
python main.py --bot
```

Bot şunları yapar:
1. Instagram'a giriş yapar (session kaydeder, bir kez login gerekir)
2. DM'leri tarar, `itiraf: ...` formatındaki mesajları yakalar
3. Her itiraf için: Claude düzenleme → kategori → video üret → Reels paylaş → teşekkür DM
4. Paylaşımlar arası 120-300 saniye rastgele bekler

---

## Proje Yapısı

```
instagramproject/
├── config.py           # Ayarlar ve sabitler
├── claude_processor.py # Claude API entegrasyonu
├── video_generator.py  # Video üretici
├── instagram_bot.py    # DM okuma + Reels paylaşma
├── main.py             # CLI giriş noktası
├── requirements.txt
├── data.json           # Örnek JSON
├── .env.example        # Ortam değişkenleri şablonu
├── muzik/              # .mp3 dosyaları
└── output/             # Üretilen videolar ve caption'lar
```

---

## Gereksinimler

- Python 3.10+
- `Pillow` — frame oluşturma
- `moviepy` — video birleştirme
- `anthropic` — Claude API
- `instagrapi` — Instagram DM ve Reels
- `python-dotenv` — `.env` desteği

---

## Notlar

- İlk bot çalıştırmasında Instagram login gerekir, sonrası session ile devam eder.
- `session.json` ve `islenmis.json` dosyaları otomatik oluşturulur.
- Bot durumu `Ctrl+C` ile durdurulabilir.
- Instagram 2FA aktifse instagrapi bunu destekler, otomatik sorulur.
