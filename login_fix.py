from instagrapi import Client
import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv(Path(__file__).parent / ".env", override=True)

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
SESSION_FILE = Path("session.json")

def challenge_code_handler(username, choice):
    print(f"\n--- DOĞRULAMA GEREKLİ ---")
    print(f"Kullanıcı: {username}")
    print(f"Kod şuraya gönderildi: {choice}")
    code = input("Lütfen Instagram'dan gelen 6 haneli kodu buraya yazın: ")
    return code

def login_fix():
    cl = Client()
    cl.challenge_code_handler = challenge_code_handler
    
    print(f"Giriş deneniyor: {IG_USERNAME}...")
    
    if SESSION_FILE.exists():
        os.remove(SESSION_FILE)

    try:
        if cl.login(IG_USERNAME, IG_PASSWORD):
            cl.dump_settings(str(SESSION_FILE))
            print("\n✅ BAŞARILI: Giriş yapıldı ve session.json oluşturuldu.")
            print("Şimdi bu pencereyi kapatıp panelden botu başlatabilirsiniz.")
        else:
            print("\n❌ HATA: Giriş yapılamadı.")
    except Exception as e:
        print(f"\n❌ HATA OLUŞTU: {e}")

if __name__ == "__main__":
    login_fix()
