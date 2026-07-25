from email.message import EmailMessage
import os

msg = EmailMessage()
msg.set_content("text")
msg.add_alternative("<html><body><img src='cid:logo_image'></body></html>", subtype='html')

try:
    msg.get_payload()[1].add_related(b"fake_image_data", 'image', 'png', cid='<logo_image>')
    print("Success")
except Exception as e:
    print(f"Error: {e}")
