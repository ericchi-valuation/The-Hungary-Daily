import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def send_newsletter(subject, html_content, subscriber_list=None):
    """
    Sends the daily newsletter via Gmail SMTP.
    """
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_password:
        print("⚠️ Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD. Skipping newsletter send.")
        return False
        
    if not subscriber_list: # Fallback to subscribers.txt if no list provided
        subscriber_file = "subscribers.txt"
        if os.path.exists(subscriber_file):
            with open(subscriber_file, "r", encoding="utf-8") as f:
                subscriber_list = [line.strip() for line in f if line.strip() and "@" in line]
        else:
            print("⚠️ subscribers.txt not found. Skipping newsletter send.")
            return False

    if not subscriber_list:
        print("⚠️ Subscriber list is empty. Skipping.")
        return False

    print(f"📧 Preparing to send newsletter to {len(subscriber_list)} subscribers...")

    try:
        # Connect to Gmail SMTP Server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)

        for recipient in subscriber_list:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"The Hungarian Daily <{gmail_user}>"
            msg['To'] = recipient

            # Attach HTML content
            part = MIMEText(html_content, 'html')
            msg.attach(part)

            server.send_message(msg)
            print(f"  ✔️ Sent to {recipient}")

        server.quit()
        print("✅ Newsletter sent successfully!")
        return True

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_html = "<h1>Szia!</h1><p>This is a test email for Hungary Daily Insider.</p>"
    send_newsletter("The Hungarian Daily Test Email", test_html)
