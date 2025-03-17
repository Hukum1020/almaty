import os
import time
import qrcode
import smtplib
import ssl
import gspread
from email.message import EmailMessage
from oauth2client.service_account import ServiceAccountCredentials

# ------------------------------
# Настройка Google Sheets API
# ------------------------------
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
CREDENTIALS_FILE = r"C:\Users\Hukum\Desktop\test\bigroup-454020-ee270aaea23e.json"  # Путь к JSON-файлу ключа
SPREADSHEET_ID = "1PlDRt50qcTUUxVglsLfT76fiTYj9Hb2IMyKPDNNHoHQ"  # ID Google Таблицы

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
client = gspread.authorize(creds)

# Предположим, что у вас основной лист - sheet1
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

# ------------------------------
# Настройка SMTP (Gmail)
# ------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "nikfedorov65@gmail.com"    # Ваш Gmail-адрес
SMTP_PASSWORD = "isqz pccv rigl sxek"   # Пароль приложения (или обычный, если 2FA отключена)

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
    """
    Считывает все строки из Google Sheets,
    ищет гостей без статуса 'Done',
    генерирует QR и отправляет письмо,
    а затем обновляет столбец 'Status'.
    """
    all_values = sheet.get_all_values()
    # Предположим, структура таблицы:
    #   A: Name
    #   B: Phone
    #   C: Email
    #   D: Status
    # Первая строка — заголовки, значит данные начинаются со второй строки.

    for i in range(1, len(all_values)):
        row = all_values[i]
        # Проверяем, что в строке есть нужное кол-во столбцов
        if len(row) < 4:
            continue
 
        email, name, phone, status = row[0], row[1], row[2], row[7]
        
        # Пропускаем пустые
        if not name or not phone or not email:
            continue

        # Если статус уже "Done", значит ранее отправляли
        if status.strip().lower() == "done":
            continue

        # Генерируем QR-код
        qr_data = f"Name: {name}\nPhone: {phone}\nEmail: {email}"
        os.makedirs("qrcodes", exist_ok=True)
        qr_filename = f"qrcodes/{email.replace('@', '_')}.png"

        qr = qrcode.make(qr_data)
        qr.save(qr_filename)

        # Отправляем email
        if send_email(email, name, qr_filename):
            # Если успешно отправлено, обновляем статус
            # В gspread нумерация строк и столбцов с 1
            # i — индекс в Python, поэтому i+1 — реальный номер строки
            # В нашем случае статус = 4-й столбец
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
