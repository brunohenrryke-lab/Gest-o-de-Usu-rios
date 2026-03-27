import random
import requests
import os

def generate_reset_code():
    return f"{random.randint(100000, 999999)}"

def send_reset_code(email, code):
    api_key = os.environ.get('BREVO_API_KEY')
    if not api_key:
        print("ERRO: BREVO_API_KEY não configurada")
        return

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    sender = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    payload = {
        "sender": {"email": sender},
        "to": [{"email": email}],
        "subject": "Password Reset Code",
        "htmlContent": f"<p>Your code: <strong>{code}</strong></p><p>Expires in 5 minutes.</p>",
        "textContent": f"Your code: {code}\n\nExpires in 5 minutes."
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 201:
            print(f"E-mail enviado com sucesso para {email}")
        else:
            print(f"Falha: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro: {e}")