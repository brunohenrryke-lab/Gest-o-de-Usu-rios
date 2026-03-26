import random
from flask import current_app
from flask_mail import Message
from extensions import mail

def generate_reset_code():
    """Generate a 6-digit numeric code."""
    return f"{random.randint(100000, 999999)}"

def send_reset_code(email, code):
    """Send the reset code via email."""
    subject = "Password Reset Code"
    body = f"Your verification code is: {code}\n\nThis code expires in 5 minutes."
    msg = Message(subject, recipients=[email], body=body)
    mail.send(msg)