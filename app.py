import os
import time
import qrcode
import smtplib
import ssl
import gspread
import json
import traceback
from email.message import EmailMessage
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
import threading

app = Flask(__name__)

# ------------------------------
# Настройка Google Sheets API
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
# Настройка SMTP (Gmail)
# ------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

if not SMTP_USER or not SMTP_PASSWORD:
    raise ValueError("❌ Ошибка: SMTP_USER или SMTP_PASSWORD не найдены!")

def send_email(email, qr_filename, language):
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg["Subject"] = "Ваш персональный QR-код" if language == "ru" else "Сіздің жеке QR-кодыңыз"

        msg.set_type("multipart/related")  

        # Загружаем HTML-шаблон
        template_filename = f"Ala{language}.html"
        if os.path.exists(template_filename):
            with open(template_filename, "r", encoding="utf-8") as template_file:
                html_content = template_file.read()
        else:
            print(f"❌ Файл шаблона {template_filename} не найден.")
            return False

        # ✅ Встраиваем логотип
        logo_path = "logo2.png"
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as logo_file:
                msg.add_related(logo_file.read(), maintype="image", subtype="png", filename="logo2.png", cid="logo")
            html_content = html_content.replace('src="logo2.png"', 'src="cid:logo"')
        else:
            print("⚠️ Логотип не найден, письмо отправляется без него.")

        # ✅ Встраиваем QR-код
        with open(qr_filename, "rb") as qr_file:
            msg.add_related(qr_file.read(), maintype="image", subtype="png", filename="qrcode.png", cid="qr")

        # Подставляем QR-код в HTML
        html_content = html_content.replace('src="qrcode.png"', 'src="cid:qr"')

        # Добавляем HTML-контент
        msg.add_alternative(html_content, subtype="html")

        # Отправка письма
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"✅ Письмо отправлено на {email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при отправке письма: {e}")
        traceback.print_exc()
        return False

def process_new_guests():
    try:
        all_values = sheet.get_all_values()
        headers = all_values[0]  # Заголовки колонок

        # Определяем индексы колонок
        name_idx = headers.index("Name")
        email_idx = headers.index("Email")
        phone_idx = headers.index("Phone")
        language_idx = headers.index("language")
        sent_idx = headers.index("sent")  # Колонка, в которую пишем отметку об отправке

        for i in range(1, len(all_values)):
            row = all_values[i]

            if len(row) <= sent_idx:  # Если строки пустые, пропускаем
                continue

            email = row[email_idx].strip()
            name = row[name_idx].strip()
            phone = row[phone_idx].strip()
            language = row[language_idx].strip().lower()
            sent_status = row[sent_idx].strip() if len(row) > sent_idx else ""

            # Проверяем, если письмо уже отправлено
            if not name or not phone or not email or sent_status:
                continue

            # Генерируем QR-код
            qr_data = f"Name: {name}\nPhone: {phone}\nEmail: {email}"
            os.makedirs("qrcodes", exist_ok=True)
            qr_filename = f"qrcodes/{email.replace('@', '_')}.png"

            qr = qrcode.make(qr_data)
            qr.save(qr_filename)

            # Отправляем письмо
            if send_email(email, qr_filename, language):
                # Записываем дату отправки в колонку "sent"
                sheet.update_cell(i + 1, sent_idx + 1, time.strftime("%Y-%m-%d %H:%M:%S"))

    except Exception as e:
        print(f"[Ошибка] при обработке гостей: {e}")
        traceback.print_exc()

# ------------------------------
# Фоновый процесс, который постоянно проверяет таблицу
# ------------------------------
def background_task():
    while True:
        try:
            process_new_guests()
        except Exception as e:
            print(f"[Ошибка] {e}")
            traceback.print_exc()
        time.sleep(30)  # Проверяем новых гостей каждые 30 секунд

# Запуск фонового процесса
threading.Thread(target=background_task, daemon=True).start()

@app.route("/")
def home():
    return "QR Code Generator is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
