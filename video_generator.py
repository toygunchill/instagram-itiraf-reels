import os
import textwrap
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from config import (
    VIDEO_GENISLIK, VIDEO_YUKSEKLIK, VIDEO_FPS, VIDEO_SURE,
    TOPLAM_FRAME, RENKLER, OUTPUT_DIR, PAGE_NAME, muzik_sec,
)

try:
    from moviepy import ImageSequenceClip, AudioFileClip
except ImportError:
    from moviepy.editor import ImageSequenceClip, AudioFileClip


# ---- Font yardimcilari ----

def _font_yukle(boyut: int, emoji: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if emoji:
        adaylar = ["/System/Library/Fonts/Apple Color Emoji.ttc"]
    else:
        adaylar = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for yol in adaylar:
        if os.path.exists(yol):
            try:
                return ImageFont.truetype(yol, boyut)
            except Exception:
                continue
    return ImageFont.load_default()


def _yuvarlatilmis_dikdortgen(draw, xy, radius, fill, outline=None):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2)


def _metin_sar(metin: str, max_karakter: int = 32) -> list[str]:
    if not metin: return [""]
    satirlar = []
    for paragraf in metin.split("\n"):
        wrapped = textwrap.wrap(paragraf, width=max_karakter, break_long_words=False, replace_whitespace=False)
        satirlar.extend(wrapped if wrapped else [""])
    return satirlar


class VideoGenerator:
    def __init__(self, sayfa_adi: str = "gizli_itiraf_edenler"):
        self.sayfa_adi = sayfa_adi
        self.f_baslik = _font_yukle(34)
        self.f_kucuk = _font_yukle(26)
        self.f_metin = _font_yukle(38)
        self.f_emoji = _font_yukle(38, emoji=True)
        self.f_gonderen = _font_yukle(26)
        self.f_saat = _font_yukle(22)
        self.f_input = _font_yukle(30)

    def _get_text_width(self, draw, text):
        """Karakter bazlı genişlik ölçümü (Emoji + Latin karma)."""
        w = 0
        for char in text:
            f = self.f_emoji if ord(char) > 0xFFFF else self.f_metin
            bbox = draw.textbbox((0, 0), char, font=f, embedded_color=True)
            w += (bbox[2] - bbox[0])
        return w

    def _draw_mixed_text(self, draw, xy, text, is_admin=False):
        """Harf harf font seçerek çizim yapar (Kutucuk sorununu çözer)."""
        x, y = xy
        for char in text:
            is_e = ord(char) > 0xFFFF
            f = self.f_emoji if is_e else self.f_metin
            color = None if is_e else RENKLER["beyaz"]
            draw.text((x, y), char, font=f, fill=color, embedded_color=True)
            bbox = draw.textbbox((0, 0), char, font=f, embedded_color=True)
            x += (bbox[2] - bbox[0])

    def frame_olustur(self, metin, gonderen, admin_reply, frame_no, toplam_frame):
        img = Image.new("RGB", (VIDEO_GENISLIK, VIDEO_YUKSEKLIK), RENKLER["arka_plan"])
        draw = ImageDraw.Draw(img)

        self._ciz_header(draw)
        self._ciz_ust_bilgi(draw)

        # HIZ AYARLARI
        anim_itiraf = 150 # 5sn
        it_gost = metin[:max(1, int(len(metin) * frame_no / anim_itiraf))] if frame_no < anim_itiraf else metin
        y1_conf = self._ciz_balon(draw, it_gost, gonderen, 230, metin, is_admin=False)

        if admin_reply and frame_no >= 180:
            anim_admin = 45 # 1.5sn (HIZLI)
            rel_f = frame_no - 180
            ad_gost = admin_reply[:max(1, int(len(admin_reply) * rel_f / anim_admin))] if rel_f < anim_admin else admin_reply
            self._ciz_balon(draw, ad_gost, self.sayfa_adi, y1_conf + 70, admin_reply, is_admin=True)

        self._ciz_input_bar(draw)
        return np.array(img)

    def _ciz_balon(self, draw, gosterilen_metin, etiket, y0, tam_metin, is_admin=False):
        margin = 45
        max_w = int(VIDEO_GENISLIK * 0.75)
        line_h = 50

        # Boyutu en baştan TAM METNE göre sabitliyoruz
        satirlar_iskelet = _metin_sar(tam_metin, max_karakter=28)
        balon_w = min(max((self._get_text_width(draw, s) for s in satirlar_iskelet), default=100) + 60, max_w)
        balon_h = len(satirlar_iskelet) * line_h + 55

        if is_admin:
            x1 = VIDEO_GENISLIK - margin
            x0 = x1 - balon_w
            fill, outline = (10, 80, 180), (30, 120, 255)
            # Etiketi sağa yasla
            label_w = draw.textbbox((0,0), etiket, font=self.f_gonderen)[2]
            draw.text((x1 - label_w - 5, y0 - 35), etiket, font=self.f_gonderen, fill=RENKLER["mavi"])
        else:
            x0, x1 = margin, margin + balon_w
            fill, outline = RENKLER["balon_bg"], RENKLER["balon_kenarlik"]
            draw.text((x0 + 5, y0 - 35), etiket, font=self.f_gonderen, fill=RENKLER["gri_acik"])

        y1 = y0 + balon_h
        _yuvarlatilmis_dikdortgen(draw, (x0, y0, x1, y1), 25, fill, outline)

        # Yazıyı satır satır ve karakter karakter çiz
        curr_idx = 0
        target_idx = len(gosterilen_metin)
        for i, satir in enumerate(satirlar_iskelet):
            if curr_idx >= target_idx: break
            line_to_draw = satir[:target_idx - curr_idx]
            self._draw_mixed_text(draw, (x0 + 28, y0 + 22 + i * line_h), line_to_draw, is_admin)
            curr_idx += len(satir) + 1

        if not is_admin:
            draw.text((x0 + 5, y1 + 8), "13:37", font=self.f_saat, fill=RENKLER["gri_koyu"])
        return y1

    def _ciz_header(self, draw):
        draw.rectangle([0, 0, VIDEO_GENISLIK, 135], fill=RENKLER["header_bg"])
        draw.text((30, 50), "<", font=self.f_baslik, fill=RENKLER["beyaz"])
        cx, cy, r = 125, 68, 38
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=RENKLER["profil_daire"])
        harf = self.sayfa_adi[0].upper()
        bbox = draw.textbbox((0,0), harf, font=self.f_baslik)
        draw.text((cx-(bbox[2]-bbox[0])//2, cy-(bbox[3]-bbox[1])//2-2), harf, font=self.f_baslik, fill=RENKLER["beyaz"])
        draw.text((185, 38), self.sayfa_adi, font=self.f_baslik, fill=RENKLER["beyaz"])
        draw.text((185, 80), "Aktif", font=self.f_kucuk, fill=RENKLER["gri_acik"])
        draw.line([0, 135, VIDEO_GENISLIK, 135], fill=RENKLER["gri_koyu"], width=1)

    def _ciz_ust_bilgi(self, draw):
        bbox = draw.textbbox((0,0), "Bugün", font=self.f_saat)
        draw.text(((VIDEO_GENISLIK-(bbox[2]-bbox[0]))//2, 165), "Bugün", font=self.f_saat, fill=RENKLER["gri_orta"])

    def _ciz_input_bar(self, draw):
        y = VIDEO_YUKSEKLIK - 130
        draw.rectangle([0, y - 10, VIDEO_GENISLIK, VIDEO_YUKSEKLIK], fill=RENKLER["header_bg"])
        _yuvarlatilmis_dikdortgen(draw, (25, y, VIDEO_GENISLIK - 115, y + 85), 42, RENKLER["input_bg"], RENKLER["input_kenarlik"])
        draw.text((55, y + 22), "Bir mesaj yazin...", font=self.f_input, fill=RENKLER["gri_koyu"])
        btn_cx, btn_cy = VIDEO_GENISLIK - 65, y + 42
        draw.ellipse([btn_cx-38, btn_cy-38, btn_cx+38, btn_cy+38], fill=RENKLER["mavi"])
        draw.text((btn_cx-12, btn_cy-18), ">", font=self.f_baslik, fill=RENKLER["beyaz"])

    def video_olustur(self, metin, gonderen, tema, cikti_yolu, admin_reply=None):
        print(f"  [Video] Üretim başlatıldı. Tema: {tema}")
        frameler = [self.frame_olustur(metin, gonderen, admin_reply, i, TOPLAM_FRAME) for i in range(TOPLAM_FRAME)]
        klip = ImageSequenceClip(frameler, fps=VIDEO_FPS)
        
        muzik_yolu = muzik_sec(tema)
        if muzik_yolu:
            print(f"  [Video] Müzik bulundu: {os.path.basename(muzik_yolu)}")
            try:
                audio = AudioFileClip(muzik_yolu)
                # Müzik videodan kısaysa döngüye sok, uzunsa kes
                if audio.duration < VIDEO_SURE:
                    from moviepy import afx
                    audio = audio.with_effects([afx.AudioLoop(duration=VIDEO_SURE)])
                else:
                    audio = audio.subclipped(0, VIDEO_SURE)
                
                audio = audio.with_volume_scaled(0.25) # Sesi biraz daha artırdım (0.20 -> 0.25)
                klip = klip.with_audio(audio)
                print("  [Video] Müzik başarıyla eklendi.")
            except Exception as e:
                print(f"  [Video] Müzik ekleme hatası: {str(e)}")
        else:
            print("  [Video] UYARI: Bu tema için müzik dosyası bulunamadı!")

        print(f"  [Video] Dosya kaydediliyor: {os.path.basename(cikti_yolu)}")
        klip.write_videofile(
            cikti_yolu, 
            fps=VIDEO_FPS, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile="temp-audio.m4a", # Ses için geçici dosya kullan
            remove_temp=True,                # İşlem bitince temizle
            logger=None
        )
        return cikti_yolu
