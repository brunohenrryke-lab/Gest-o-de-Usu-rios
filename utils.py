import random
from flask_mail import Message
from extensions import mail

def generate_reset_code():
    return f"{random.randint(100000, 999999)}"

def send_reset_code(email, code):
    msg = Message(
        subject="Password Reset Code",
        recipients=[email],
        body=f"Your verification code is: {code}\n\nThis code expires in 5 minutes."
    )
    mail.send(msg)