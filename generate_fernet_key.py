from cryptography.fernet import Fernet

from security import FERNET_KEY_ENV_VAR


def main():
    key = Fernet.generate_key().decode()
    print("Generated Fernet key:")
    print(key)
    print()
    print("Add this line to your .env file:")
    print(f"{FERNET_KEY_ENV_VAR}={key}")


if __name__ == "__main__":
    main()
