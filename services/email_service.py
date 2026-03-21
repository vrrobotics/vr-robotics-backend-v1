import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings


def send_email(to: str, subject: str, html_body: str):
    """Send an HTML email via Brevo SMTP"""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"VR Robotics Academy <{settings.FROM_EMAIL}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.FROM_EMAIL, to, msg.as_string())


def send_booking_confirmation(booking: dict):
    """Send confirmation email to parent after successful payment"""
    html = f"""
    <div style="font-family:Arial;max-width:600px;margin:0 auto;padding:20px">
      <h2 style="color:#FF6A00">🎉 Demo Class Booked!</h2>
      <p>Dear {booking['parent_name']},</p>
      <p>Your demo class for <b>{booking['child_name']}</b> is confirmed!</p>
      <table style="width:100%;border-collapse:collapse;margin:20px 0">
        <tr>
          <td style="padding:10px;border:1px solid #ddd;font-weight:bold">Date</td>
          <td style="padding:10px;border:1px solid #ddd">{booking.get('preferred_date', 'TBD')}</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #ddd;font-weight:bold">Time</td>
          <td style="padding:10px;border:1px solid #ddd">{booking.get('preferred_time', 'TBD')}</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #ddd;font-weight:bold">Amount</td>
          <td style="padding:10px;border:1px solid #ddd">₹{booking['amount']} ✅ Paid</td>
        </tr>
        <tr>
          <td style="padding:10px;border:1px solid #ddd;font-weight:bold">Payment ID</td>
          <td style="padding:10px;border:1px solid #ddd">{booking.get('razorpay_payment_id', '—')}</td>
        </tr>
      </table>
      <p>We'll send the class link 24 hours before your session.</p>
      <p style="color:#888;margin-top:30px">— VR Robotics Academy, Hyderabad</p>
    </div>
    """
    send_email(booking["email"], "✅ Demo Booked — VR Robotics Academy", html)


def notify_admin(booking: dict):
    """Notify VR Robotics admin about new booking"""
    html = f"""
    <h3>📋 New Demo Booking Received</h3>
    <p><b>Parent:</b> {booking['parent_name']} | {booking['email']} | {booking['phone']}</p>
    <p><b>Child:</b> {booking['child_name']}, Age {booking.get('child_age', 'N/A')}</p>
    <p><b>Date:</b> {booking.get('preferred_date', 'TBD')} at {booking.get('preferred_time', 'TBD')}</p>
    <p><b>Amount:</b> ₹{booking['amount']} | Payment ID: {booking.get('razorpay_payment_id', '—')}</p>
    <p><b>Interests:</b> {booking.get('interests', '—')}</p>
    <p><b>Message:</b> {booking.get('message', '—')}</p>
    """
    send_email(settings.VR_ADMIN_EMAIL, f"🆕 Demo: {booking['child_name']}", html)
