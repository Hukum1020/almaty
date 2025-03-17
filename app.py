import os
import csv
import qrcode
import smtplib
import ssl
from flask import Flask, request, jsonify
from email.message import EmailMessage
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CSV_FILE = "event_guests.csv"

# SMTP-настройки (замени на свои)
SMTP_SERVER = "smtp.gmail.com"  # Или "smtp.yandex.ru" для Яндекса
SMTP_PORT = 587
SMTP_USER = "your_email@gmail.com"  # Замени на свою почту
SMTP_PASSWORD = "your_app_password"  # Вставь пароль приложения!

# Создание CSV-файла, если его нет
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Имя", "Фамилия", "Email", "Статус"])  # Заголовки

init_csv()

# Функция поиска гостя в CSV
def find_guest(email):
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row and row[2] == email:
                return row  # Возвращает [Имя, Фамилия, Email, Статус]
    return None

# Функция отправки email с QR-кодом
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

        # Отправка письма
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
        return False

# **1. Регистрация гостя и генерация QR-кода**
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    if request.content_type == "application/json":
        data = request.json
    else:  # Принимаем form-data от Tilda
        data = request.form.to_dict()
        
    data = request.json
    name = data.get("name")
    surname = data.get("surname")
    email = data.get("email")

    if not name or not surname or not email:
        return jsonify({"error": "Все поля обязательны"}), 400

    if find_guest(email):
        return jsonify({"error": "Этот email уже зарегистрирован"}), 400

    # Добавляем гостя в CSV
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([name, surname, email, "не пришел"])

    # Генерация QR-кода
    os.makedirs("qrcodes", exist_ok=True)
    qr_filename = f"qrcodes/{email.replace('@', '_')}.png"
    qr = qrcode.make(email)
    qr.save(qr_filename)

    # Отправка email
    if send_email(email, name, qr_filename):
        return jsonify({"message": "QR-код создан и отправлен на email!"}), 200
    else:
        return jsonify({"error": "Ошибка отправки email"}), 500

# **2. Сканирование QR-кода и отметка посещения**
@app.route('/scan_qr', methods=['POST'])
def scan_qr():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "QR-код некорректен"}), 400

    guest = find_guest(email)
    if not guest:
        return jsonify({"error": "Гость не найден"}), 404

    name, surname, _, status = guest

    # Обновление статуса в CSV
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

    return jsonify({
        "message": "Гость отмечен как посетивший" if updated else "Гость уже был отмечен ранее",
        "name": name,
        "surname": surname,
        "status": "посетил" if updated else "уже посещал"
    }), 200

# **3. Проверка Webhook (для Render)**
@app.route('/test', methods=['POST'])
def test_webhook():
    return jsonify({"message": "Webhook работает!"}), 200

# Запуск сервера на Render
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render передаёт порт через переменные окружения
    app.run(host="0.0.0.0", port=port, debug=True)
