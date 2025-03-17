import os
import time
import qrcode
import smtplib
import ssl
import gspread
from email.message import EmailMessage
from oauth2client.service_account import ServiceAccountCredentials
import json

# ------------------------------
# Настройка Google Sheets API
# ------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")  # Загружаем JSON из переменной окружения
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # ID таблицы из переменной окружения

creds_dict = json.loads(CREDENTIALS_JSON)  # Декодируем JSON-ключ
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)

# Подключение к листу
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# ------------------------------
# Настройка SMTP (Gmail)
# ------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")  # Email
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Пароль приложения

def send_email(email, name, qr_filename):
    """Отправка письма с прикреплённым QR-кодом."""
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
    """Обработка данных из Google Sheets."""
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

def main_loop():
    while True:
        try:
            process_new_guests()
        except Exception as e:
            print("[Ошибка] при обработке гостей:", e)
        time.sleep(30)

if __name__ == '__main__':
    main_loop()
