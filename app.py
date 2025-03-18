def send_email(email, name, qr_filename, language):
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg["Subject"] = "Ваш QR-код" if language == "ru" else "QR-код билеті"

        # Attach the logo image
        with open("logo2.png", "rb") as img:
            msg.add_attachment(img.read(), maintype="image", subtype="png", filename="logo2.png", cid="logo_image")

        css_styles = """
            <style>
                body { font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f4; }
                .email-container {
                    max-width: 600px;
                    margin: auto;
                    background: #ffffff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    text-align: center;
                }
                .email-container img {
                    max-width: 200px;
                    margin-bottom: 20px;
                }
                .email-container p {
                    font-size: 16px;
                    text-align: left;
                    color: #333;
                }
                .email-container .highlight {
                    font-weight: bold;
                    color: #132f63;
                }
            </style>
        """

        if language == "ru":
            body = f"""
            <html>
            <head>{css_styles}</head>
            <body>
                <div class="email-container">
                    <img src="cid:logo_image">
                    <p>Спасибо за регистрацию на <span class="highlight">BI Ecosystem!</span></p>
                    <p>Это ваш входной билет, пожалуйста, не удаляйте это письмо.</p>
                    <p>Ждём вас <span class="highlight">5 апреля в 9:30</span> по адресу:</p>
                    <p>г. Алматы, проспект Аль-Фараби, 30, Almaty Teatre</p>
                </div>
            </body>
            </html>
            """
        else:  # "kz"
            body = f"""
            <html>
            <head>{css_styles}</head>
            <body>
                <div class="email-container">
                    <img src="cid:logo_image">
                    <p><span class="highlight">BI Ecosystem</span> жүйесіне тіркелгеніңізге рахмет!</p>
                    <p>Бұл сіздің кіруге арналған билетіңіз, өтініш осы хатты өшірмеңіз.</p>
                    <p>Сізді <span class="highlight">5 сәуір күні сағат 09:30</span> Алматы қаласы, Әл-Фараби даңғылы, 30 мекен жайы бойынша күтеміз.</p>
                </div>
            </body>
            </html>
            """

        msg.add_alternative(body, subtype='html')

        with open(qr_filename, "rb") as qr_file:
            msg.add_attachment(qr_file.read(), maintype="image", subtype="png", filename="qrcode.png")

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
            if len(row) < 11:  # Теперь проверяем, что есть хотя бы 11 колонок (до language)
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

# Фоновый процесс (для обработки Google Sheets)
def background_task():
    while True:
        try:
            process_new_guests()
        except Exception as e:
            print(f"[Ошибка] {e}")
            traceback.print_exc()
        time.sleep(30)

# Запуск фонового процесса при старте
import threading
threading.Thread(target=background_task, daemon=True).start()

@app.route("/")
def home():
    return "QR Code Generator is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
