import os
import time
import qrcode
import smtplib
import ssl
import gspread
import json
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask

app = Flask(__name__)

# ------------------------------
# Google Sheets API Setup
# ------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
if not SPREADSHEET_ID:
    raise ValueError("❌ Ошибка: SPREADSHEET_ID не найдено!")

CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not CREDENTIALS_JSON:
    raise ValueError("❌ Ошибка: GOOGLE_CREDENTIALS_JSON не найдено!")

try:
    creds_dict = json.loads(CREDENTIALS_JSON)
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
except Exception as e:
    raise ValueError(f"❌ Ошибка подключения к Google Sheets: {e}")

# ------------------------------
# SMTP Email Configuration
# ------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

if not SMTP_USER or not SMTP_PASSWORD:
    raise ValueError("❌ Ошибка: SMTP_USER или SMTP_PASSWORD не найдены!")

# Path to your logo
LOGO_PATH = "logo2.png"  # Make sure this file exists in the script directory

def send_email(email, name, qr_filename, language):
    try:
        # Generate Email Message
        msg = MIMEMultipart("related")
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg["Subject"] = "Ваш QR-код" if language == "ru" else "QR-код билеті"

        # Read the logo image
        with open(LOGO_PATH, "rb") as logo_file:
            logo_data = logo_file.read()

        # Read the QR Code image
        with open(qr_filename, "rb") as qr_file:
            qr_data = qr_file.read()

        # Set HTML Email Template
        html_template = f"""\
        <!DOCTYPE html>
        <html lang="ru">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ваш билет</title>
        <style>
            body {{
                background-color: #132f63;
                color: white;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                text-align: center;
            }}
            .container {{
                width: 100%;
                max-width: 600px;
                margin: auto;
                padding: 20px;
                border: 1px solid #EBEBEB;
                border-radius: 5px;
                background-color: #132f63;
            }}
            .logo {{
                text-align: left;
                padding: 20px;
            }}
            .qr-code {{
                text-align: center;
                margin: 20px;
            }}
        </style>
        </head>
        <body>
            <div class="logo">
                <img src="cid:logo" alt="Company Logo" width="150">
            </div>
            <div class="container">
                <h1>Спасибо за регистрацию!</h1>
                <p>Это ваш входной билет, пожалуйста, не удаляйте это письмо.</p>
                <p>QR code нужно предъявить на входе для участия в розыгрыше ценных призов!</p>
                <div class="qr-code">
                    <img src="cid:qrcode" alt="QR Code" width="150" height="150">
                </div>
                <p>Ждём вас 5 апреля в 9:30 по адресу:</p>
                <p><b>г. Алматы, проспект Аль-Фараби, 30, Almaty Teatre</b></p>
            </div>
        </body>
        </html>
        """

        # Attach HTML Content
        msg.attach(MIMEText(html_template, "html"))

        # Attach Logo as Inline Image
        logo_img = MIMEImage(logo_data, _subtype="png")
        logo_img.add_header("Content-ID", "<logo>")
        logo_img.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(logo_img)

        # Attach QR Code as Inline Image
        qr_img = MIMEImage(qr_data, _subtype="png")
        qr_img.add_header("Content-ID", "<qrcode>")
        qr_img.add_header("Content-Disposition", "inline", filename="qrcode.png")
        msg.attach(qr_img)

        # Send Email
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[OK] Письмо отправлено на {email}")
        return True
    except Exception as e:
        print(f"[Ошибка] Не удалось отправить письмо на {email}: {e}")
        traceback.print_exc()
        return False

def process_new_guests():
    try:
        all_values = sheet.get_all_values()

        for i in range(1, len(all_values)):
            row = all_values[i]
            if len(row) < 11:
                continue

            email, name, phone, status, language = row[0], row[1], row[2], row[7], row[10].strip().lower()

            if not name or not phone or not email or status.strip().lower() == "done":
                continue

            qr_data = f"Name: {name}\nPhone: {phone}\nEmail: {email}"
            os.makedirs("qrcodes", exist_ok=True)
            qr_filename = f"qrcodes/{email.replace('@', '_')}.png"

            qr = qrcode.make(qr_data)
            qr.save(qr_filename)

            if send_email(email, name, qr_filename, language):
                sheet.update_cell(i+1, 8, "Done")
    except Exception as e:
        print(f"[Ошибка] при обработке гостей: {e}")
        traceback.print_exc()

# Background Task (Google Sheets Processing)
def background_task():
    while True:
        try:
            process_new_guests()
        except Exception as e:
            print(f"[Ошибка] {e}")
            traceback.print_exc()
        time.sleep(30)

# Start Background Task
import threading
threading.Thread(target=background_task, daemon=True).start()

@app.route("/")
def home():
    return "QR Code Generator is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
