from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os
from dotenv import load_dotenv

load_dotenv()

VAULT_NAME = os.getenv("AZURE_KEYVAULT_NAME")
ENV = os.getenv("ENVIRONMENT", "local")


def load_keyvault_secrets():

    # Local → .env only
    if ENV.lower() == "local":
        print("🔹 Running in LOCAL mode – using .env")
        return

    # Production → Key Vault
    if not VAULT_NAME:
        raise RuntimeError("AZURE_KEYVAULT_NAME not set")

    vault_url = f"https://{VAULT_NAME}.vault.azure.net/"

    client = SecretClient(
        vault_url=vault_url,
        credential=DefaultAzureCredential()
    )

    for secret in client.list_properties_of_secrets():
        os.environ[secret.name] = client.get_secret(secret.name).value

    print("Key Vault secrets loaded")
