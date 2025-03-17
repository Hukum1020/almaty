import os
import time
import qrcode
import smtplib
import ssl
import gspread
import json
from email.message import EmailMessage
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask

app = Flask(__name__)

# ------------------------------
# Настройка Google Sheets API
# ------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_JSON = os.getenv("CREDENTIALS_JSON")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

creds_dict = json.loads(CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# ------------------------------
# Настройка SMTP (Gmail)
# ------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(email, name, qr_filename):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Ваш QR-код"
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg.set_content(f"Здравствуйте, {name}!\n\nВаш персональный QR-код во вложении.")

        with open(qr_filename, "rb") as qr_file:
            msg.add_attachment(
                qr_file.read(),
                maintype="image",
                subtype="png",
                filename="qrcode.png"
            )

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[OK] Письмо отправлено на {email}")
        return True
    except Exception as e:
        print(f"[Ошибка] Не удалось отправить письмо на {email}: {e}")
        return False

def process_new_guests():
    all_values = sheet.get_all_values()

    for i in range(1, len(all_values)):
        row = all_values[i]
        if len(row) < 4:
            continue

        email, name, phone, status = row[0], row[1], row[2], row[7]

        if not name or not phone or not email or status.strip().lower() == "done":
            continue

        qr_data = f"Name: {name}\nPhone: {phone}\nEmail: {email}"
        os.makedirs("qrcodes", exist_ok=True)
        qr_filename = f"qrcodes/{email.replace('@', '_')}.png"

        qr = qrcode.make(qr_data)
        qr.save(qr_filename)

        if send_email(email, name, qr_filename):
            sheet.update_cell(i+1, 8, "Done")

# Фоновый процесс
def background_task():
    while True:
        try:
            process_new_guests()
        except Exception as e:
            print(f"[Ошибка] {e}")
        time.sleep(30)

# Запуск фонового процесса при старте
import threading
threading.Thread(target=background_task, daemon=True).start()

@app.route("/")
def home():
    return "QR Code Generator is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render использует переменную PORT
    app.run(host="0.0.0.0", port=port)
