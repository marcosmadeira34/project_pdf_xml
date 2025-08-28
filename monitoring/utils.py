import os
from twilio.rest import Client

def send_whatsapp_alert(message: str):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")  # exemplo: 'whatsapp:+14155238886'
    to_whatsapp = os.getenv("MY_WHATSAPP_NUMBER")      # exemplo: 'whatsapp:+55SEUNUMERO'

    client = Client(account_sid, auth_token)

    menu = (
        "\n\nEscolha uma ação:\n"
        "1️⃣ - Status do worker\n"
        "2️⃣ - Logs do worker\n"
        "3️⃣ - Logs do beat\n"
        "4️⃣ - Logs do gunicorn\n"
        "5️⃣ - Logs do nginx\n"
        "6️⃣ - Criar usuário\n"
        "7️⃣ - Reiniciar worker\n"
        # "8️⃣ - Logs do nginx\n"
        # "9️⃣ - Reiniciar worker\n"
    )

    client.messages.create(
        body=f"{message}{menu}",
        from_=from_whatsapp,
        to=to_whatsapp
    )