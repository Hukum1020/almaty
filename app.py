from flask import Flask, request, jsonify
import qrcode
import csv
import os
import smtplib
import ssl
from email.message import EmailMessage
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CSV_FILE = "event_guests.csv"

# В идеале пароли и логины брать из переменных окружения:
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "your_email@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "ваш_пароль_приложения")

# Создаём CSV, если ещё не существует
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Имя", "Фамилия", "Email", "Статус"])  # Заголовки

init_csv()

# Проверяем, зарегистрирован ли email
def is_registered(email):
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row and row[2] == email:
                return True
    return False

# Отправка email
def send_email(email, name, qr_filename):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Ваш QR-код"
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg.set_content(f"Здравствуйте, {name}!\n\nВаш персональный QR-код во вложении.")

        # Прикрепляем QR-код
        with open(qr_filename, "rb") as qr_file:
            msg.add_attachment(qr_file.read(), maintype="image", subtype="png", filename="qrcode.png")

        # Отправляем
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # Логгирование для отладки (можно отключить)
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
        return False

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    # Tilda обычно шлёт form-data, поэтому считываем через request.form:
    data = request.form.to_dict()

    name = data.get("name")
    surname = data.get("surname")
    email = data.get("email")

    if not name or not surname or not email:
        return jsonify({"error": "Все поля обязательны"}), 400

    if is_registered(email):
        return jsonify({"error": "Этот email уже зарегистрирован"}), 400

    # Записываем в CSV
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([name, surname, email, "не пришел"])

    # Генерируем папку под QR-коды (если нужно)
    os.makedirs("qrcodes", exist_ok=True)
    qr_filename = f"qrcodes/{email.replace('@', '_')}.png"
    qr = qrcode.make(email)
    qr.save(qr_filename)

    # Отправляем письмо с QR
    if send_email(email, name, qr_filename):
        return jsonify({"message": "QR-код создан и отправлен на email!"}), 200
    else:
        return jsonify({"error": "Ошибка отправки email"}), 500

@app.route('/scan_qr', methods=['POST'])
def scan_qr():
    data = request.json  # Допустим, сканер шлёт JSON
    email = data.get("email")

    if not email:
        return jsonify({"error": "QR-код некорректен"}), 400

    if not is_registered(email):
        return jsonify({"error": "Гость не найден"}), 404

    # Обновляем статус в CSV
    rows = []
    updated = False
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row and row[2] == email and row[3] == "не пришел":
                row[3] = "посетил"
                updated = True
            rows.append(row)

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

    if updated:
        return jsonify({"message": "Гость отмечен как посетивший"}), 200
    else:
        return jsonify({"message": "Гость уже был отмечен ранее"}), 200

if __name__ == '__main__':
    # Локальный запуск
    app.run(debug=True)
