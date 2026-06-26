from pydog_monitor.db import connect_database

def view_contacts():
    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, contact_name, email, phone_number, preferred_contact
    FROM contacts
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No contacts available.")
        return

    # Calculate column widths
    id_len = max(max(len(str(row[0])) for row in rows) + 5, len("Unique ID") + 1)
    contact_name_len = max(max(len(row[1]) for row in rows) + 5, len("Contact Name") + 1)
    email_len = max(max(len(row[2]) for row in rows) + 5, len("Email") + 1)
    phone_number_len = max(max(len(str(row[3])) for row in rows) + 5, len("Phone Number") + 1)
    preferred_contact_len = max(max(len(row[4]) for row in rows) + 5, len("Preferred Contact") + 1)

    # Print table header
    total_len = id_len + contact_name_len + email_len + phone_number_len + preferred_contact_len
    print('-' * total_len)
    print(f"{'Unique ID'.ljust(id_len)} {'Contact Name'.ljust(contact_name_len)} {'Email'.ljust(email_len)} {'Phone Number'.ljust(phone_number_len)} {'Preferred Contact'.ljust(preferred_contact_len)}")
    print('-' * total_len)

    # Print table rows
    for row in rows:
        print(f"{str(row[0]).ljust(id_len)} {row[1].ljust(contact_name_len)} {row[2].ljust(email_len)} {str(row[3]).ljust(phone_number_len)} {row[4].ljust(preferred_contact_len)}")

    print('-' * total_len)

def add_contact():
    contact_name = input("Enter Contact Name: ")
    email = input("Enter Email: ")
    phone_number = input("Enter Phone Number: ")
    preferred_contact = input("Enter Preferred Contact (Email or Phone): ").lower()

    if not contact_name or len(contact_name) > 50:
        print("Invalid entry - Contact Name must be set and less than 50 characters.")
        return
    if not email or len(email) > 50:
        print("Invalid entry - Email must be set and less than 50 characters.")
        return
    if preferred_contact not in ['email', 'phone']:
        print("Invalid entry - Preferred Contact must be either 'Email' or 'Phone'.")
        return
    if preferred_contact == 'phone' and not phone_number:
        print("Invalid entry - Phone Number must be set if Preferred Contact is 'Phone'.")
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO contacts (contact_name, email, phone_number, preferred_contact)
    VALUES (?, ?, ?, ?)
    ''', (contact_name, email, phone_number, preferred_contact))
    conn.commit()
    conn.close()
    print("Contact added successfully.")

def remove_contact():
    view_contacts()
    unique_id = input("Enter the Unique ID of the contact you want to remove (Enter 0 to go back to the main menu): ")

    if unique_id == '0':
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM contacts WHERE id = ?', (unique_id,))
    contact = cursor.fetchone()

    if not contact:
        print("Invalid entry - Unique ID does not exist.")
        conn.close()
        return

    cursor.execute('DELETE FROM contacts WHERE id = ?', (unique_id,))
    conn.commit()
    conn.close()
    print("Contact removed successfully.")

def update_contact():
    view_contacts()
    unique_id = input("Enter the Unique ID of the contact you want to edit (Enter 0 to go back to the main menu): ")

    if unique_id == '0':
        return

    conn = connect_database()
    cursor = conn.cursor()
    cursor.execute('SELECT contact_name, email, phone_number, preferred_contact FROM contacts WHERE id = ?', (unique_id,))
    contact = cursor.fetchone()

    if not contact:
        print("Invalid entry - Unique ID does not exist.")
        conn.close()
        return

    contact_name, email, phone_number, preferred_contact = contact

    new_contact_name = input(f"Contact Name [{contact_name}] (enter nothing to not update this field): ")
    new_email = input(f"Email [{email}] (enter nothing to not update this field): ")
    new_phone_number = input(f"Phone Number [{phone_number}] (enter nothing to not update this field): ")
    new_preferred_contact = input(f"Preferred Contact [{preferred_contact}] (enter nothing to not update this field): ")

    if new_contact_name:
        contact_name = new_contact_name
    if new_email:
        email = new_email
    if new_phone_number:
        phone_number = new_phone_number
    if new_preferred_contact:
        preferred_contact = new_preferred_contact

    cursor.execute('''
    UPDATE contacts
    SET contact_name = ?, email = ?, phone_number = ?, preferred_contact = ?
    WHERE id = ?
    ''', (contact_name, email, phone_number, preferred_contact, unique_id))
    conn.commit()
    conn.close()
    print("Contact updated successfully.")

def contact_functions():
    while True:
        print("1: Add contact for monitoring")
        print("2: Update contact")
        print("3: Remove contact from monitoring")
        print("0: Back to main menu")
        choice = input("Enter your choice: ")

        if choice == '1':
            add_contact()
        elif choice == '2':
            update_contact()
        elif choice == '3':
            remove_contact()
        elif choice == '0':
            break
        else:
            print("Invalid choice. Please try again.")
