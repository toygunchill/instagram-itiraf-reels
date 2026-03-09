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

def _font_yukle(boyut: int, emoji: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Sistemde bulunan ilk uygun fontu yükler."""
    if emoji:
        adaylar = ["/System/Library/Fonts/Apple Color Emoji.ttc"]
    else:
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


def _metin_sar(metin: str, max_karakter: int = 32) -> list[str]:
    satirlar = []
    if not metin: return [""]
    for paragraf in metin.split("\n"):
        wrapped = textwrap.wrap(paragraf, width=max_karakter, break_long_words=False, replace_whitespace=False)
        if wrapped:
            satirlar.extend(wrapped)
        else:
            satirlar.append("")
    return satirlar


# ---- Ana frame uretici ----

class VideoGenerator:
    def __init__(self, sayfa_adi: str = "gizli_itiraf_edenler"):
        self.sayfa_adi = sayfa_adi
        self.f_baslik = _font_yukle(32)
        self.f_kucuk = _font_yukle(26)
        self.f_metin = _font_yukle(36)
        self.f_emoji = _font_yukle(36, emoji=True)
        self.f_gonderen = _font_yukle(24)
        self.f_saat = _font_yukle(22)
        self.f_input = _font_yukle(30)

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

        # Animasyon zamanlaması (FPS=30)
        # 0-150: İtiraf yazılıyor (5sn) - Daha yavaş
        # 150-180: Bekleme (1sn)
        # 180-225: Admin cevabı yazılıyor (1.5sn) - DAHA SERİ
        
        anim_itiraf = 150
        itiraf_uzunluk = len(metin)
        if frame_no < anim_itiraf:
            len_i = max(1, int(itiraf_uzunluk * frame_no / anim_itiraf))
            itiraf_gosterilen = metin[:len_i]
        else:
            itiraf_gosterilen = metin
            
        # İtiraf balonunu çiz
        y1_confession = self._ciz_balon(draw, itiraf_gosterilen, gonderen, 230, metin, is_admin=False)

        if admin_reply and frame_no >= 180:
            anim_admin = 45 # 1.5 saniyede bitsin (HIZLI)
            rel_frame = frame_no - 180
            admin_uzunluk = len(admin_reply)
            if rel_frame < anim_admin:
                len_a = max(1, int(admin_uzunluk * rel_frame / anim_admin))
                admin_gosterilen = admin_reply[:len_a]
            else:
                admin_gosterilen = admin_reply
            
            self._ciz_balon(draw, admin_gosterilen, self.sayfa_adi, y1_confession + 60, admin_reply, is_admin=True)

        self._ciz_input_bar(draw)
        return np.array(img)

    def _ciz_header(self, draw: ImageDraw.ImageDraw):
        draw.rectangle([0, 0, VIDEO_GENISLIK, 130], fill=RENKLER["header_bg"])
        draw.text((28, 50), "<", font=self.f_baslik, fill=RENKLER["beyaz"])
        cx, cy, r = 120, 65, 36
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RENKLER["profil_daire"])
        harf = self.sayfa_adi[0].upper() if self.sayfa_adi else "G"
        bbox = draw.textbbox((0, 0), harf, font=self.f_baslik)
        hw, hh = (bbox[2] - bbox[0]) // 2, (bbox[3] - bbox[1]) // 2
        draw.text((cx - hw, cy - hh - 2), harf, font=self.f_baslik, fill=RENKLER["beyaz"])
        draw.text((172, 35), self.sayfa_adi, font=self.f_baslik, fill=RENKLER["beyaz"])
        draw.text((172, 75), "Aktif", font=self.f_kucuk, fill=RENKLER["gri_acik"])
        draw.text((VIDEO_GENISLIK - 110, 45), "[]", font=self.f_baslik, fill=RENKLER["gri_acik"])
        draw.text((VIDEO_GENISLIK - 55, 45), "o", font=self.f_baslik, fill=RENKLER["gri_acik"])
        draw.line([0, 130, VIDEO_GENISLIK, 130], fill=RENKLER["gri_koyu"], width=1)

    def _ciz_ust_bilgi(self, draw: ImageDraw.ImageDraw):
        metin = "Bugün"
        bbox = draw.textbbox((0, 0), metin, font=self.f_saat)
        w = bbox[2] - bbox[0]
        draw.text(((VIDEO_GENISLIK - w) // 2, 155), metin, font=self.f_saat, fill=RENKLER["gri_orta"])

    def _ciz_balon(self, draw: ImageDraw.ImageDraw, gosterilen_metin: str, etiket: str, y0: int, tam_metin: str, is_admin: bool = False) -> int:
        margin = 40
        max_balon_genislik = int(VIDEO_GENISLIK * 0.75)
        satir_yukseklik = 46

        # BOYUT SABİTLEME: Sarma işlemini her zaman TAM METİN üzerinden yapıyoruz
        satirlar_iskelet = _metin_sar(tam_metin, max_karakter=30)
        
        # Balon boyutunu iskelete göre hesapla (Değişmez)
        en_uzun = max((draw.textbbox((0, 0), s, font=self.f_metin)[2] for s in satirlar_iskelet), default=100)
        balon_genislik = min(en_uzun + 60, max_balon_genislik)
        balon_yukseklik = len(satirlar_iskelet) * satir_yukseklik + 50

        if is_admin:
            balon_x1 = VIDEO_GENISLIK - margin
            balon_x0 = balon_x1 - balon_genislik
            fill_color = (0, 70, 150)
            outline_color = RENKLER["mavi"]
            label_color = RENKLER["mavi"]
        else:
            balon_x0 = margin
            balon_x1 = balon_x0 + balon_genislik
            fill_color = RENKLER["balon_bg"]
            outline_color = RENKLER["balon_kenarlik"]
            label_color = RENKLER["gri_acik"]

        balon_y1 = y0 + balon_yukseklik

        # Etiket
        draw.text((balon_x0 + 8, y0 - 30), etiket, font=self.f_gonderen, fill=label_color)
        
        # Balon Arka Plan
        _yuvarlatilmis_dikdortgen(draw, (balon_x0, y0, balon_x1, balon_y1), radius=22, fill=fill_color, outline=outline_color)

        # Yazı Çizimi (Karakter karakter dolma)
        current_len = 0
        target_len = len(gosterilen_metin)
        
        for i, satir in enumerate(satirlar_iskelet):
            if current_len >= target_len: break
            
            # Bu satırda kaç karakter göstereceğiz?
            kalan = target_len - current_len
            cizilecek_satir = satir[:kalan]
            current_len += len(satir) + 1 # +1 for the space/newline logic of wrap
            
            is_emoji = any(ord(c) > 0xFFFF for c in cizilecek_satir)
            draw.text(
                (balon_x0 + 24, y0 + 18 + i * satir_yukseklik),
                cizilecek_satir,
                font=self.f_emoji if is_emoji else self.f_metin,
                fill=RENKLER["beyaz"] if not is_emoji else None,
                embedded_color=True
            )

        if not is_admin:
            draw.text((balon_x0 + 8, balon_y1 + 8), "13:37", font=self.f_saat, fill=RENKLER["gri_koyu"])
        
        return balon_y1

    def _ciz_input_bar(self, draw: ImageDraw.ImageDraw):
        bar_y = VIDEO_YUKSEKLIK - 130
        draw.rectangle([0, bar_y - 10, VIDEO_GENISLIK, VIDEO_YUKSEKLIK], fill=RENKLER["header_bg"])
        _yuvarlatilmis_dikdortgen(draw, (24, bar_y, VIDEO_GENISLIK - 109, bar_y + 80), radius=40, fill=RENKLER["input_bg"], outline=RENKLER["input_kenarlik"])
        draw.text((52, bar_y + 20), "Bir mesaj yazin...", font=self.f_input, fill=RENKLER["gri_koyu"])
        btn_cx, btn_cy = VIDEO_GENISLIK - 59, bar_y + 40
        draw.ellipse([btn_cx - 36, btn_cy - 36, btn_cx + 36, btn_cy + 36], fill=RENKLER["mavi"])
        draw.text((btn_cx - 10, btn_cy - 16), ">", font=self.f_baslik, fill=RENKLER["beyaz"])

    def video_olustur(self, metin: str, gonderen: str, kategori: str, cikti_yolu: str, admin_reply: str = None) -> str:
        print(f"  Frameler olusturuluyor...")
        frameler = [self.frame_olustur(metin, gonderen, admin_reply, i, TOPLAM_FRAME) for i in range(TOPLAM_FRAME)]
        klip = ImageSequenceClip(frameler, fps=VIDEO_FPS)
        muzik_yolu = muzik_sec(kategori)
        if muzik_yolu:
            try:
                ses = AudioFileClip(muzik_yolu).subclipped(0, VIDEO_SURE).with_volume_scaled(0.20)
                klip = klip.with_audio(ses)
            except Exception: pass
        klip.write_videofile(cikti_yolu, fps=VIDEO_FPS, codec="libx264", audio_codec="aac", logger=None)
        return cikti_yolu
