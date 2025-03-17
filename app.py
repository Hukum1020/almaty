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

# Данные SMTP-сервера (замени на свои)
SMTP_SERVER = "smtp.gmail.com"  # Для Gmail (для Яндекса: smtp.yandex.ru)
SMTP_PORT = 587
SMTP_USER = "nikitasicily22@gmail.com"  # Замени на свою почту
SMTP_PASSWORD = "hufb ivmi rika trbs"  # Замени на пароль приложения

# Создание CSV-файла, если его нет
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Имя", "Фамилия", "Email", "Статус"])  # Заголовки

init_csv()

# Функция для проверки, зарегистрирован ли пользователь
def is_registered(email):
    with open(CSV_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row and row[2] == email:
                return True
    return False

# Функция для отправки email через smtplib
def send_email(email, name, qr_filename):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Ваш QR-код"
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg.set_content(f"Здравствуйте, {name}!\n\nВаш персональный QR-код во вложении.")

        # Добавляем вложение
        with open(qr_filename, "rb") as qr_file:
            msg.add_attachment(qr_file.read(), maintype="image", subtype="png", filename="qrcode.png")

        # Отправка письма
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # <---- Добавь этот уровень логирования
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")  # <---- Покажет точную ошибку
        return False


# Регистрация пользователя и генерация QR-кода
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json
    name = data.get("name")
    surname = data.get("surname")
    email = data.get("email")

    if not name or not surname or not email:
        return jsonify({"error": "Все поля обязательны"}), 400

    if is_registered(email):
        return jsonify({"error": "Этот email уже зарегистрирован"}), 400

    # Добавляем гостя в CSV
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([name, surname, email, "не пришел"])

    # Генерируем QR-код
    os.makedirs("qrcodes", exist_ok=True)
    qr_filename = f"qrcodes/{email.replace('@', '_')}.png"
    qr = qrcode.make(email)
    qr.save(qr_filename)

    # Отправляем email с QR-кодом
    if send_email(email, name, qr_filename):
        return jsonify({"message": "QR-код создан и отправлен на email!"}), 200
    else:
        return jsonify({"error": "Ошибка отправки email"}), 500

# Сканирование QR-кода и отметка посещения
@app.route('/scan_qr', methods=['POST'])
def scan_qr():
    data = request.json
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
    
    return jsonify({"message": "Гость отмечен как посетивший"} if updated else {"message": "Гость уже был отмечен ранее"}), 200

if __name__ == '__main__':
    app.run(debug=True)
