# notification_service.py - SMS and Email Notification System
# Connects to Twilio API and logs all operations locally.

import os
from database import db

# Twilio Credentials (loaded from environment or set as defaults)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "ACmock_account_sid_placeholder")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "mock_auth_token_placeholder")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "+15005550006") # Default Twilio test number

# Primary target alert numbers (Patient, Admin, Appointment notifications)
ALERT_NUMBERS = ["7795273421", "7795273241", "7019113622"]

# Try to import Twilio
try:
    from twilio.rest import Client
    TWILIO_INSTALLED = True
except ImportError:
    TWILIO_INSTALLED = False

def send_sms_notification(message, trigger_reason, user_id=None):
    """Dispatches SMS to primary alert numbers and stores them in notifications audit log."""
    print(f"\n================= SMS NOTIFICATION TRIGGERED =================")
    print(f"Reason: {trigger_reason}")
    print(f"Content: {message}")
    print(f"Target Numbers: {', '.join(ALERT_NUMBERS)}")
    print(f"==============================================================\n")

    success_count = 0
    client = None

    if TWILIO_INSTALLED and "mock" not in TWILIO_ACCOUNT_SID:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception as e:
            print(f"[Notifications] Twilio initialization failed: {e}. Logging to console instead.")
            client = None

    for number in ALERT_NUMBERS:
        status = "sent"
        
        # Standardize format for international (assume +91 for Indian mobile numbers if they start with 7/8/9 and are 10 digits)
        formatted_number = number
        if len(number) == 10 and number[0] in '789':
            formatted_number = f"+91{number}"
        elif not number.startswith("+"):
            formatted_number = f"+1{number}" # Default to US or generic formatting

        if client:
            try:
                client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=formatted_number
                )
                print(f"[Notifications] Twilio SMS successfully sent to {formatted_number}")
                success_count += 1
            except Exception as e:
                print(f"[Notifications] Twilio SMS failed for {formatted_number}: {e}")
                status = "failed"
        else:
            # Console simulation counts as "sent" in testing mode
            print(f"[Notifications] Console-logged SMS (simulation mode) sent to {formatted_number}")
            success_count += 1

        # Save to database notifications table for audit trail
        try:
            query = """
            INSERT INTO notifications (user_id, mobile_number, type, message, status, trigger_reason)
            VALUES (%s, %s, 'sms', %s, %s, %s)
            """
            # If user_id is none, assign 1 (Default Patient/Admin) or general system user
            db_user_id = user_id if user_id else 1
            db.execute_query(query, (db_user_id, formatted_number, message, status, trigger_reason))
        except Exception as db_err:
            print(f"[Notifications] Database log failed: {db_err}")

    return success_count > 0


def send_sms_to_number(message, trigger_reason, target_number, user_id=None):
    """Sends SMS to a single specific number (e.g. for appointment/message alerts)."""
    print(f"\n[Notification] Targeted SMS to {target_number}: [{trigger_reason}] {message[:80]}...")
    formatted = target_number
    if len(target_number) == 10 and target_number[0] in '789':
        formatted = f"+91{target_number}"
    elif not target_number.startswith("+"):
        formatted = f"+1{target_number}"

    status = "sent"
    client = None
    if TWILIO_INSTALLED and "mock" not in TWILIO_ACCOUNT_SID:
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        except Exception:
            client = None

    if client:
        try:
            client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=formatted)
        except Exception as e:
            print(f"[Notifications] Targeted SMS failed: {e}")
            status = "failed"

    try:
        query = "INSERT INTO notifications (user_id, mobile_number, type, message, status, trigger_reason) VALUES (%s, %s, 'sms', %s, %s, %s)"
        db.execute_query(query, (user_id or 1, formatted, message, status, trigger_reason))
    except Exception as db_err:
        print(f"[Notifications] DB log failed: {db_err}")
    return status == "sent"

def send_email_notification(to_email, subject, message, trigger_reason, user_id=None):
    """Simulates email notification dispatch and saves it to the notification log."""
    print(f"\n================ EMAIL NOTIFICATION TRIGGERED ================")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Reason: {trigger_reason}")
    print(f"Content: {message}")
    print(f"==============================================================\n")

    # Log to DB
    try:
        query = """
        INSERT INTO notifications (user_id, mobile_number, type, message, status, trigger_reason)
        VALUES (%s, %s, 'email', %s, 'sent', %s)
        """
        db_user_id = user_id if user_id else 1
        db.execute_query(query, (db_user_id, to_email, f"Subject: {subject} | {message}", trigger_reason))
    except Exception as db_err:
        print(f"[Notifications] Database log failed: {db_err}")

    return True
