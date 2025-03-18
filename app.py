def send_email(email, name, qr_filename, language):
    try:
        msg = EmailMessage()
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg["Subject"] = "Ваш QR-код" if language == "ru" else "QR-код билеті"

        if language == "ru":
            body = f"""Спасибо за регистрацию на BI Ecosystem!  

Это ваш входной билет, пожалуйста, не удаляйте это письмо. QR-код нужно предъявить на входе для участия в розыгрыше ценных призов!  

Ждём вас 5 апреля в 9:30 по адресу:  
г. Алматы, проспект Аль-Фараби, 30, Almaty Teatre"""
        else:  # "kz"
            body = """BI Ecosystem жүйесіне тіркелгеніңізге рахмет! 

Бұл сіздің кіруге арналған билетіңіз, өтініш осы хатты өшірмеңіз. Ұтыс ойындарында қатысу үшін осы QR кодты кіру есігі алдында көрсету қажет.

Сізді 5 сәуір күні сағат 09:30 Алматы қаласы, Әл-Фараби даңғылы, 30 мекен жайы бойынша күтеміз."""

        email_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    width: 100%;
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background-color: #132f63;
                    padding: 20px;
                    text-align: center;
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 20px;
                    color: #333;
                    font-size: 16px;
                    line-height: 1.5;
                }}
                .button {{
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    padding: 12px 20px;
                    border-radius: 5px;
                    font-size: 16px;
                    text-align: center;
                    margin-top: 20px;
                }}
                .footer {{
                    padding: 15px;
                    text-align: center;
                    font-size: 14px;
                    color: #888;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    BI Ecosystem
                </div>
                <div class="content">
                    <p>{body}</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.set_content(body)  # Plain text fallback
        msg.add_alternative(email_html, subtype="html")

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
