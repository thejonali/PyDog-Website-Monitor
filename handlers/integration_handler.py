from pydog_monitor.db import connect_database
from pydog_monitor.monitor import send_email_smtp, send_email, send_sms
from pydog_monitor.security import FERNET_KEY_ENV_VAR, encrypt_secret, encryption_enabled

SECRET_KEYS = {"sender_password", "auth_token"}


def _secret_display_value(key, value):
    if key in SECRET_KEYS:
        return "<stored secret>"
    return value


def _store_secret(value):
    return encrypt_secret(value)


def _print_encryption_status():
    if encryption_enabled():
        print(f"Secret encryption enabled using {FERNET_KEY_ENV_VAR}.")
    else:
        print(
            f"Secret encryption is not currently active because "
            f"{FERNET_KEY_ENV_VAR} is not set. Secrets will be stored as "
            "plaintext until you run `python generate_fernet_key.py` and add "
            "the key to `.env`."
        )

def setup_integrations():
    while True:
        print("\n1: Instructions")
        print("2: Add Integration")
        print("3: Test Integrations")
        print("4: Edit Integrations")
        print("0: Main Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            instructions_menu()
        elif choice == '2':
            add_integration_menu()
        elif choice == '3':
            test_integrations_menu()
        elif choice == '4':
            edit_integration_menu()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")

def instructions_menu():
    while True:
        print("\n1: Instructions for GMail API Integration")
        print("2: Instructions for standard SMTP Email Integration")
        print("3: Instructions for Twilio Integration")
        print("0: Back to Setup and Integrations Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            instructions_gmail_api()
        elif choice == '2':
            instructions_smtp_email()
        elif choice == '3':
            instructions_twilio()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")

def add_integration_menu():
    while True:
        print("\n1: Add GMail API Integration")
        print("2: Add standard SMTP Email Integration")
        print("3: Add Twilio Integration")
        print("0: Back to Setup and Integrations Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            add_gmail_integration()
        elif choice == '2':
            add_smtp_integration()
        elif choice == '3':
            add_twilio_integration()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")

def test_integrations_menu():
    while True:
        print("\n1: Test GMail API Connection")
        print("2: Test SMTP Email Integration")
        print("3: Test Twilio Integration")
        print("0: Back to Setup and Integrations Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            test_gmail_api()
        elif choice == '2':
            test_smtp_email()
        elif choice == '3':
            test_twilio()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")

def edit_integration_menu():
    while True:
        print("\n1: Edit GMail API Integration")
        print("2: Edit standard SMTP Email Integration")
        print("3: Edit Twilio Integration")
        print("4: Edit Monitor Header")
        print("0: Back to Setup and Integrations Menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            edit_gmail_integration()
        elif choice == '2':
            edit_smtp_integration()
        elif choice == '3':
            edit_twilio_integration()
        elif choice == '4':
            edit_monitor_header()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")

def instructions_gmail_api():
    print("\n------------------------")
    print("Instructions for GMail API Integration:")
    print("1. Go to the Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select an existing project.")
    print("3. Enable the Gmail API for your project.")
    print("4. Create OAuth 2.0 credentials and download the JSON file.")
    print("5. Save the JSON file as 'client_secret.json' in your project directory.")
    print("6. Run the application and follow the prompts to authorize access.")
    print("------------------------\n")

def instructions_smtp_email():
    print("\n------------------------")
    print("Instructions for standard SMTP Email Integration:")
    print("1. Obtain the SMTP server address and port for your email provider.")
    print("2. Obtain your email address and password.")
    print("3. Update the 'send_email' function with your SMTP server details, email address, and password.")
    print("4. Test the SMTP email integration using the provided test option.")
    print("------------------------\n")

def instructions_twilio():
    print("\n------------------------")
    print("Instructions for Twilio Integration:")
    print("1. Sign up for a Twilio account: https://www.twilio.com/")
    print("2. Obtain your Account SID, Auth Token, and Twilio phone number.")
    print("3. Update the 'send_sms' function with your Twilio credentials and phone number.")
    print("4. Test the Twilio integration using the provided test option.")
    print("------------------------\n")

def add_gmail_integration():
    instructions_gmail_api()
    print("Please add the 'client_secret.json' file to your project directory.")

def add_smtp_integration():
    _print_encryption_status()
    sender_email = input("Enter the sender email address: ")
    sender_password = input("Enter the sender email password: ")
    smtp_server = input("Enter the SMTP server address: ")
    smtp_port = input("Enter the SMTP server port: ")

    stored_password = _store_secret(sender_password)

    conn = connect_database()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("SMTP", "sender_email", sender_email, 1))
    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("SMTP", "sender_password", stored_password, 1))
    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("SMTP", "smtp_server", smtp_server, 1))
    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("SMTP", "smtp_port", smtp_port, 1))

    conn.commit()
    conn.close()

    print("SMTP Email Integration added successfully.")

def add_twilio_integration():
    _print_encryption_status()
    account_sid = input("Enter the Twilio Account SID: ")
    auth_token = input("Enter the Twilio Auth Token: ")
    from_phone = input("Enter the Twilio phone number: ")

    stored_auth_token = _store_secret(auth_token)

    conn = connect_database()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("Twilio", "account_sid", account_sid, 1))
    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("Twilio", "auth_token", stored_auth_token, 1))
    cursor.execute('''
    INSERT INTO settings (integration_name, key, value, status)
    VALUES (?, ?, ?, ?)
    ''', ("Twilio", "from_phone", from_phone, 1))

    conn.commit()
    conn.close()

    print("Twilio Integration added successfully.")

def edit_gmail_integration():
    print("Edit GMail API Integration:")
    print("Please add the 'client_secret.json' file to your project directory if it is not already present.")

def edit_smtp_integration():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT key, value FROM settings WHERE integration_name = 'SMTP' AND status = 1
    ''')
    settings = cursor.fetchall()

    if not settings:
        print("No record of SMTP integration exists, please add the integration first.")
        conn.close()
        return

    for key, value in settings:
        display_value = _secret_display_value(key, value)
        new_value = input(f"Enter new value for {key} [{display_value}]: ")
        if new_value:
            if key == "sender_password":
                new_value = _store_secret(new_value)
            cursor.execute('''
            UPDATE settings
            SET value = ?
            WHERE integration_name = 'SMTP' AND key = ?
            ''', (new_value, key))

    conn.commit()
    conn.close()
    print("SMTP Email Integration updated successfully.")

def edit_twilio_integration():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT key, value FROM settings WHERE integration_name = 'Twilio' AND status = 1
    ''')
    settings = cursor.fetchall()

    if not settings:
        print("No record of Twilio integration exists, please add the integration first.")
        conn.close()
        return

    for key, value in settings:
        display_value = _secret_display_value(key, value)
        new_value = input(f"Enter new value for {key} [{display_value}]: ")
        if new_value:
            if key == "auth_token":
                new_value = _store_secret(new_value)
            cursor.execute('''
            UPDATE settings
            SET value = ?
            WHERE integration_name = 'Twilio' AND key = ?
            ''', (new_value, key))

    conn.commit()
    conn.close()
    print("Twilio Integration updated successfully.")

def edit_monitor_header():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT key, value FROM settings WHERE integration_name = 'monitor_header' AND status = 1
    ''')
    settings = cursor.fetchall()

    for key, value in settings:
        new_value = input(f"Enter new value for {key} [{value}]: ")
        if new_value:
            cursor.execute('''
            UPDATE settings
            SET value = ?
            WHERE integration_name = 'monitor_header' AND key = ?
            ''', (new_value, key))

    conn.commit()
    conn.close()
    print("Monitor Header updated successfully.")

def test_gmail_api():
    email = input("Enter the email address to send the test email to: ")
    print("Testing GMail API Connection...")
    try:
        send_email(email, "Test Email", "<p>This is a test email.</p>", "https://www.example.com")
        print("GMail API Connection successful.")
    except Exception as e:
        print(f"GMail API Connection failed: {e}")

def test_smtp_email():
    email = input("Enter the email address to send the test email to: ")
    print("Testing SMTP Email Integration...")
    try:
        send_email_smtp(email, "Test Email", "<p>This is a test email.</p>")
        print("SMTP Email Integration successful.")
    except Exception as e:
        print(f"SMTP Email Integration failed: {e}")

def test_twilio():
    phone_number = input("Enter the phone number to send the test SMS to: ")
    print("Testing Twilio Integration...")
    try:
        send_sms(phone_number, "This is a test SMS.")
        print("Twilio Integration successful.")
    except Exception as e:
        print(f"Twilio Integration failed: {e}")
