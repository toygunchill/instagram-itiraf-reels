import os
import textwrap
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config import (
    VIDEO_GENISLIK, VIDEO_YUKSEKLIK, VIDEO_FPS, VIDEO_SURE,
    TOPLAM_FRAME, RENKLER, OUTPUT_DIR, PAGE_NAME, muzik_sec,
)

# moviepy import (eski ve yeni API uyumu)
try:
    from moviepy import ImageSequenceClip, AudioFileClip, CompositeAudioClip
except ImportError:
    from moviepy.editor import ImageSequenceClip, AudioFileClip, CompositeAudioClip


# ---- Font yardimcilari ----

def _font_yukle(boyut: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Sistemde bulunan ilk uygun fontu yükler."""
    adaylar = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for yol in adaylar:
        if os.path.exists(yol):
            try:
                return ImageFont.truetype(yol, boyut)
            except Exception:
                continue
    return ImageFont.load_default()


# ---- Cizim yardimcilari ----

def _yuvarlatilmis_dikdortgen(
    draw: ImageDraw.ImageDraw,
    xy: tuple,
    radius: int,
    fill: tuple,
    outline: tuple | None = None,
    outline_width: int = 1,
):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                            outline=outline, width=outline_width)


def _metin_sar(metin: str, max_karakter: int = 35) -> list[str]:
    satirlar = []
    for paragraf in metin.split("\n"):
        satirlar.extend(textwrap.wrap(paragraf, width=max_karakter) or [""])
    return satirlar


# ---- Ana frame uretici ----

class VideoGenerator:
    def __init__(self, sayfa_adi: str = PAGE_NAME):
        self.sayfa_adi = sayfa_adi
        self.f_baslik = _font_yukle(32)
        self.f_kucuk = _font_yukle(26)
        self.f_metin = _font_yukle(36)
        self.f_gonderen = _font_yukle(24)
        self.f_saat = _font_yukle(22)
        self.f_input = _font_yukle(30)

    # -------------------------------------------------------
    def frame_olustur(
        self,
        metin: str,
        gonderen: str,
        admin_reply: str,
        frame_no: int,
        toplam_frame: int,
    ) -> np.ndarray:
        img = Image.new("RGB", (VIDEO_GENISLIK, VIDEO_YUKSEKLIK), RENKLER["arka_plan"])
        draw = ImageDraw.Draw(img)

        self._ciz_header(draw)
        self._ciz_ust_bilgi(draw)

        # Animasyon zamanlaması
        # 0-60: İtiraf yazılıyor
        # 60-120: İtiraf duruyor
        # 120-180: Admin cevabı yazılıyor (varsa)
        
        anim_itiraf = 60
        itiraf_metni = metin
        if frame_no < anim_itiraf:
            len_i = max(1, int(len(metin) * frame_no / anim_itiraf))
            itiraf_metni = metin[:len_i]
            
        # İtiraf balonunu her zaman çiz (en azından ilk kısmı)
        self._ciz_mesaj_balonu(draw, itiraf_metni, gonderen)

        # Admin cevabı varsa ve zamanı geldiyse çiz
        if admin_reply and frame_no >= 120:
            anim_admin = 60 # 120'den 180'e kadar
            rel_frame = frame_no - 120
            admin_metni = admin_reply
            if rel_frame < anim_admin:
                len_a = max(1, int(len(admin_reply) * rel_frame / anim_admin))
                admin_metni = admin_reply[:len_a]
            
            # İtiraf balonunun altına admin balonunu çiz
            # Mesaj balonunun yüksekliğini hesaplamamız lazım (veya sabit bir offset kullanabiliriz)
            # Şimdilik _ciz_mesaj_balonu içinde y koordinatını döndürelim veya parametre yapalım.
            itiraf_y1 = 230 + (len(_metin_sar(metin, 32)) * 46 + 50)
            self._ciz_admin_balonu(draw, admin_metni, itiraf_y1 + 60)

        self._ciz_input_bar(draw)

        return np.array(img)

    # -------------------------------------------------------
    def _ciz_admin_balonu(self, draw: ImageDraw.ImageDraw, metin: str, y_offset: int):
        margin = 40
        max_balon_genislik = int(VIDEO_GENISLIK * 0.75)
        satir_yukseklik = 46

        satirlar = _metin_sar(metin, max_karakter=32)

        # Balon boyutunu hesapla
        en_uzun = max((draw.textbbox((0, 0), s, font=self.f_metin)[2] for s in satirlar), default=100)
        balon_genislik = min(en_uzun + 60, max_balon_genislik)
        balon_yukseklik = len(satirlar) * satir_yukseklik + 50

        # Sağ tarafa yasla (Mavi balon tarzı)
        balon_x1 = VIDEO_GENISLIK - margin
        balon_x0 = balon_x1 - balon_genislik
        balon_y0 = y_offset
        balon_y1 = balon_y0 + balon_yukseklik

        # Admin etiketi (sağ üst)
        draw.text(
            (balon_x0 + 8, balon_y0 - 30),
            self.sayfa_adi,
            font=self.f_gonderen,
            fill=RENKLER["mavi"],
        )

        # Balon (Mavi/Accent rengi arka plan)
        _yuvarlatilmis_dikdortgen(
            draw,
            (balon_x0, balon_y0, balon_x1, balon_y1),
            radius=22,
            fill=(0, 70, 150), # Koyu mavi
            outline=RENKLER["mavi"],
            outline_width=1,
        )

        # Metin satirlari
        for i, satir in enumerate(satirlar):
            draw.text(
                (balon_x0 + 24, balon_y0 + 18 + i * satir_yukseklik),
                satir,
                font=self.f_metin,
                fill=RENKLER["beyaz"],
            )

    # -------------------------------------------------------
    def _ciz_header(self, draw: ImageDraw.ImageDraw):
        # Header arka plani
        draw.rectangle([0, 0, VIDEO_GENISLIK, 130], fill=RENKLER["header_bg"])

        # Geri oku (<)
        draw.text((28, 50), "<", font=self.f_baslik, fill=RENKLER["beyaz"])

        # Profil dairesi
        cx, cy, r = 120, 65, 36
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RENKLER["profil_daire"])
        # Daire icinde harf
        harf = self.sayfa_adi[0].upper() if self.sayfa_adi else "I"
        bbox = draw.textbbox((0, 0), harf, font=self.f_baslik)
        hw = (bbox[2] - bbox[0]) // 2
        hh = (bbox[3] - bbox[1]) // 2
        draw.text((cx - hw, cy - hh - 2), harf, font=self.f_baslik, fill=RENKLER["beyaz"])

        # Sayfa adi
        draw.text((172, 35), self.sayfa_adi, font=self.f_baslik, fill=RENKLER["beyaz"])
        draw.text((172, 75), "Aktif", font=self.f_kucuk, fill=RENKLER["gri_acik"])

        # Sag ikonlar (video + telefon)
        draw.text((VIDEO_GENISLIK - 110, 45), "[]", font=self.f_baslik, fill=RENKLER["gri_acik"])
        draw.text((VIDEO_GENISLIK - 55, 45), "o", font=self.f_baslik, fill=RENKLER["gri_acik"])

        # Alt cizgi
        draw.line([0, 130, VIDEO_GENISLIK, 130], fill=RENKLER["gri_koyu"], width=1)

    # -------------------------------------------------------
    def _ciz_ust_bilgi(self, draw: ImageDraw.ImageDraw):
        # Tarih/zaman bilgisi
        metin = "Bugün"
        bbox = draw.textbbox((0, 0), metin, font=self.f_saat)
        w = bbox[2] - bbox[0]
        draw.text(((VIDEO_GENISLIK - w) // 2, 155), metin, font=self.f_saat, fill=RENKLER["gri_orta"])

    # -------------------------------------------------------
    def _ciz_mesaj_balonu(self, draw: ImageDraw.ImageDraw, metin: str, gonderen: str):
        margin = 40
        max_balon_genislik = int(VIDEO_GENISLIK * 0.75)
        satir_yukseklik = 46

        satirlar = _metin_sar(metin, max_karakter=32)

        # Balon boyutunu hesapla
        en_uzun = max((draw.textbbox((0, 0), s, font=self.f_metin)[2] for s in satirlar), default=100)
        balon_genislik = min(en_uzun + 60, max_balon_genislik)
        balon_yukseklik = len(satirlar) * satir_yukseklik + 50

        # Sol tarafa yasla
        balon_x0 = margin
        balon_x1 = balon_x0 + balon_genislik
        balon_y0 = 230
        balon_y1 = balon_y0 + balon_yukseklik

        # Gonderici adi
        draw.text(
            (balon_x0 + 8, balon_y0 - 30),
            gonderen,
            font=self.f_gonderen,
            fill=RENKLER["gri_acik"],
        )

        # Balon
        _yuvarlatilmis_dikdortgen(
            draw,
            (balon_x0, balon_y0, balon_x1, balon_y1),
            radius=22,
            fill=RENKLER["balon_bg"],
            outline=RENKLER["balon_kenarlik"],
            outline_width=1,
        )

        # Metin satirlari
        for i, satir in enumerate(satirlar):
            draw.text(
                (balon_x0 + 24, balon_y0 + 18 + i * satir_yukseklik),
                satir,
                font=self.f_metin,
                fill=RENKLER["beyaz"],
            )

        # Saat etiketi
        draw.text(
            (balon_x0 + 8, balon_y1 + 8),
            "13:37",
            font=self.f_saat,
            fill=RENKLER["gri_koyu"],
        )

    # -------------------------------------------------------
    def _ciz_input_bar(self, draw: ImageDraw.ImageDraw):
        bar_y = VIDEO_YUKSEKLIK - 130
        bar_yukseklik = 80
        margin = 24

        # Arka plan
        draw.rectangle([0, bar_y - 10, VIDEO_GENISLIK, VIDEO_YUKSEKLIK], fill=RENKLER["header_bg"])

        # Input kutusu
        _yuvarlatilmis_dikdortgen(
            draw,
            (margin, bar_y, VIDEO_GENISLIK - margin - 85, bar_y + bar_yukseklik),
            radius=40,
            fill=RENKLER["input_bg"],
            outline=RENKLER["input_kenarlik"],
            outline_width=1,
        )
        draw.text(
            (margin + 28, bar_y + 20),
            "Bir mesaj yazin...",
            font=self.f_input,
            fill=RENKLER["gri_koyu"],
        )

        # Gonderi dugmesi (daire)
        btn_cx = VIDEO_GENISLIK - margin - 35
        btn_cy = bar_y + bar_yukseklik // 2
        btn_r = 36
        draw.ellipse(
            [btn_cx - btn_r, btn_cy - btn_r, btn_cx + btn_r, btn_cy + btn_r],
            fill=RENKLER["mavi"],
        )
        # Ok isareti
        draw.text((btn_cx - 10, btn_cy - 16), ">", font=self.f_baslik, fill=RENKLER["beyaz"])

    # -------------------------------------------------------
    def video_olustur(
        self,
        metin: str,
        gonderen: str,
        kategori: str,
        cikti_yolu: str,
        admin_reply: str = None,
    ) -> str:
        print(f"  Frameler olusturuluyor ({TOPLAM_FRAME} adet)...")
        frameler = [
            self.frame_olustur(metin, gonderen, admin_reply, i, TOPLAM_FRAME)
            for i in range(TOPLAM_FRAME)
        ]

        print("  Video birlestiriliyor...")
        klip = ImageSequenceClip(frameler, fps=VIDEO_FPS)

        muzik_yolu = muzik_sec(kategori)
        if muzik_yolu:
            print(f"  Muzik ekleniyor: {muzik_yolu}")
            try:
                # Prompt Madde 6: Konuşma yoksa volume = 0.20
                ses = AudioFileClip(muzik_yolu).subclipped(0, VIDEO_SURE).with_volume_scaled(0.20)
                klip = klip.with_audio(ses)
            except Exception as e:
                print(f"  Muzik eklenemedi: {e}")

        print(f"  Video kaydediliyor: {cikti_yolu}")
        klip.write_videofile(
            cikti_yolu,
            fps=VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        return cikti_yolu
