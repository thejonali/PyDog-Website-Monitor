from handlers.contact_handler import view_contacts
from db import connect_database
import re

def view_websites():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, website_url
    FROM websites
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No websites available.")
        return

    # Calculate column widths
    id_len = max(max(len(str(row[0])) for row in rows) + 5, len("Unique ID") + 1)
    website_url_len = max(max(len(row[1]) for row in rows) + 5, len("Website URL") + 1)

    # Print table header
    total_len = id_len + website_url_len
    print('-' * total_len)
    print(f"{'Unique ID'.ljust(id_len)} {'Website URL'.ljust(website_url_len)}")
    print('-' * total_len)

    # Print table rows
    for row in rows:
        print(f"{str(row[0]).ljust(id_len)} {row[1].ljust(website_url_len)}")

    print('-' * total_len)

def view_monitored_websites():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT w.id, w.website_url, c.contact_name, c.preferred_contact, c.email, c.phone_number
    FROM websites w
    JOIN website_monitor wm ON w.id = wm.website_id
    JOIN contacts c ON wm.contact_id = c.id
    WHERE w.monitor_status = 1
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No websites being monitored.")
        return

    # Calculate column widths
    id_len = max(max(len(str(row[0])) for row in rows) + 5, len("Unique ID") + 1)
    website_url_len = max(max(len(row[1]) for row in rows) + 5, len("Website URL") + 1)
    contact_name_len = max(max(len(row[2] or '') for row in rows) + 5, len("Primary Contact") + 1)
    contact_method_len = max(max(len(f"{'Email - ' + (row[4] or '') if row[3] == 'email' else 'Phone Number - ' + (row[5] or '')}") for row in rows) + 5, len("Contact Method") + 1)

    # Print table header
    total_len = id_len + website_url_len + contact_name_len + contact_method_len
    print('-' * total_len)
    print(f"{'Unique ID'.ljust(id_len)} {'Website URL'.ljust(website_url_len)} {'Primary Contact'.ljust(contact_name_len)} {'Contact Method'.ljust(contact_method_len)}")
    print('-' * total_len)

    # Print table rows
    for row in rows:
        contact_method = f"{'Email - ' + (row[4] or '') if row[3] == 'email' else 'Phone Number - ' + (row[5] or '')}"
        print(f"{str(row[0]).ljust(id_len)} {row[1].ljust(website_url_len)} {(row[2] or '').ljust(contact_name_len)} {contact_method.ljust(contact_method_len)}")

    print('-' * total_len)

def view_down_history():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT dt.id, w.website_url, dt.time_stamp, dt.error_code, c.contact_name
    FROM down_tracking dt
    JOIN websites w ON dt.website_id = w.id
    JOIN contacts c ON dt.sent_contact = c.id
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No down history available.")
        return

    # Calculate column widths
    id_len = max(max(len(str(row[0])) for row in rows) + 5, len("Unique ID") + 1)
    website_url_len = max(max(len(row[1]) for row in rows) + 5, len("Website URL") + 1)
    timestamp_len = max(max(len(str(row[2])) for row in rows) + 5, len("Timestamp") + 1)
    error_code_len = max(max(len(row[3]) for row in rows) + 5, len("Error Code") + 1)
    contact_name_len = max(max(len(row[4]) for row in rows) + 5, len("Contact Name") + 1)

    # Print table header
    total_len = id_len + website_url_len + timestamp_len + error_code_len + contact_name_len
    print('-' * total_len)
    print(f"{'Unique ID'.ljust(id_len)} {'Website URL'.ljust(website_url_len)} {'Timestamp'.ljust(timestamp_len)} {'Error Code'.ljust(error_code_len)} {'Contact Name'.ljust(contact_name_len)}")
    print('-' * total_len)

    # Print table rows
    for row in rows:
        print(f"{str(row[0]).ljust(id_len)} {row[1].ljust(website_url_len)} {str(row[2]).ljust(timestamp_len)} {row[3].ljust(error_code_len)} {row[4].ljust(contact_name_len)}")

    print('-' * total_len)

def add_website():
    website_url = input("Enter Website URL to monitor: ")

    if not website_url or len(website_url) > 150:
        print("Invalid entry - Website URL must be set and less than or equal to 150 characters.")
        return

    if not re.match(r'^https?://', website_url):
        print("Invalid entry - Website URL must start with http:// or https://")
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO websites (website_url, monitor_status)
    VALUES (?, 1)
    ''', (website_url,))
    conn.commit()
    conn.close()
    print("Website added successfully.")

def remove_website():
    view_monitored_websites()
    unique_id = input("Enter the Unique ID of the website you want to STOP monitoring (Enter 0 to go back to the main menu): ")

    if unique_id == '0':
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM websites WHERE id = ?', (unique_id,))
    website = cursor.fetchone()

    if not website:
        print("Invalid entry - Unique ID does not exist.")
        conn.close()
        return

    cursor.execute('UPDATE websites SET monitor_status = 0 WHERE id = ?', (unique_id,))
    conn.commit()
    conn.close()
    print("Website is no longer being monitored.")

def update_website():
    view_websites()
    unique_id = input("Enter the Unique ID of the website you want to edit (Enter 0 to go back to the main menu): ")

    if unique_id == '0':
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('SELECT website_url, monitor_status FROM websites WHERE id = ?', (unique_id,))
    website = cursor.fetchone()

    if not website:
        print("Invalid entry - Unique ID does not exist.")
        conn.close()
        return

    website_url, monitor_status = website

    new_website_url = input(f"Website URL [{website_url}] (enter nothing to not update this field): ")
    new_monitor_status = input(f"Monitor Status [{monitor_status}] (enter nothing to not update this field): ")

    if new_website_url:
        website_url = new_website_url
    if new_monitor_status:
        monitor_status = new_monitor_status

    cursor.execute('''
    UPDATE websites
    SET website_url = ?, monitor_status = ?
    WHERE id = ?
    ''', (website_url, monitor_status, unique_id))
    conn.commit()
    conn.close()
    print("Website updated successfully.")

def connect_contact_to_website():
    print("Connecting contact to website page...")
    view_websites()
    website_id = input("Enter the Unique ID of the website you want to connect a contact to (Enter 0 to go back to the main menu): ")

    if website_id == '0':
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM websites WHERE id = ?', (website_id,))
    website = cursor.fetchone()

    if not website:
        print("Invalid entry - Unique ID does not exist.")
        conn.close()
        return

    view_contacts()
    contact_id = input("Enter the Unique ID of the contact you want to connect to the website (Enter 0 to go back to the main menu): ")

    if contact_id == '0':
        return

    cursor.execute('SELECT id FROM contacts WHERE id = ?', (contact_id,))
    contact = cursor.fetchone()

    if not contact:
        print("Invalid entry - Unique ID does not exist.")
        conn.close()
        return

    cursor.execute('''
    INSERT INTO website_monitor (website_id, contact_id)
    VALUES (?, ?)
    ''', (website_id, contact_id))
    conn.commit()
    conn.close()
    print("Contact connected to website successfully.")

def website_functions():
    while True:
        print("1: Add website page to be monitored")
        print("2: Update website page")
        print("3: Remove website page from being monitored")
        print("4: Connect contacts to website pages")
        print("5: View all websites")
        print("6: View websites being monitored")
        print("0: Back to main menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            add_website()
        elif choice == '2':
            update_website()
        elif choice == '3':
            remove_website()
        elif choice == '4':
            connect_contact_to_website()
        elif choice == '5':
            view_websites()
        elif choice == '6':
            view_monitored_websites()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")
