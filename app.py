import os
import qrcode
import smtplib
import ssl
from flask import Flask, request, jsonify
from email.message import EmailMessage
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 🔹 Подключение к PostgreSQL через Render
DATABASE_URL = os.environ.get("DATABASE_URL")

# Проверяем, что переменная есть
if not DATABASE_URL:
    raise RuntimeError("❌ Ошибка: DATABASE_URL не найден! Проверь переменные окружения.")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# 🔹 Определяем таблицу гостей
class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default="не пришел")

# 🔹 Создаём таблицы (если их нет)
with app.app_context():
    db.create_all()

# 🔹 SMTP (отправка email с QR-кодом)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your_email@gmail.com"  # Замени на свою почту
SMTP_PASSWORD = "your_app_password"  # Используй пароль приложения!

def send_email(email, name, qr_filename):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Ваш QR-код"
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg.set_content(f"Здравствуйте, {name}!\n\nВаш персональный QR-код во вложении.")

        with open(qr_filename, "rb") as qr_file:
            msg.add_attachment(qr_file.read(), maintype="image", subtype="png", filename="qrcode.png")

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
        return False

# 🔹 Регистрация гостя (создание QR-кода и отправка на email)
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.json if request.is_json else request.form.to_dict()
    name, surname, email = data.get("name"), data.get("surname"), data.get("email")

    if not name or not surname or not email:
        return jsonify({"error": "Все поля обязательны"}), 400

    # Проверяем, есть ли email в базе
    existing_guest = Guest.query.filter_by(email=email).first()
    if existing_guest:
        return jsonify({"error": "Этот email уже зарегистрирован"}), 400

    # Генерация QR-кода
    qr_filename = f"qrcodes/{email.replace('@', '_')}.png"
    os.makedirs("qrcodes", exist_ok=True)
    qr = qrcode.make(email)
    qr.save(qr_filename)

    # Сохраняем гостя в базе
    new_guest = Guest(name=name, surname=surname, email=email)
    db.session.add(new_guest)
    db.session.commit()

    # Отправляем email
    if send_email(email, name, qr_filename):
        return jsonify({"message": "QR-код создан и отправлен на email!"}), 200
    else:
        return jsonify({"error": "Ошибка отправки email"}), 500

# 🔹 Сканирование QR-кода (отметка посещения)
@app.route('/scan_qr', methods=['POST'])
def scan_qr():
    data = request.json if request.is_json else request.form.to_dict()
    email = data.get("email")

    if not email:
        return jsonify({"error": "QR-код некорректен"}), 400

    guest = Guest.query.filter_by(email=email).first()
    if not guest:
        return jsonify({"error": "Гость не найден"}), 404

    if guest.status == "не пришел":
        guest.status = "посетил"
        db.session.commit()
        return jsonify({"message": "Гость отмечен как посетивший", "name": guest.name, "surname": guest.surname}), 200
    else:
        return jsonify({"message": "Гость уже был отмечен ранее", "name": guest.name, "surname": guest.surname}), 200

# Запуск сервера
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
