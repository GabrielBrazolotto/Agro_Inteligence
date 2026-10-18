"""Execute da raiz: python -m scripts.init_data."""
from agro_ai.config import get_settings
from agro_ai.database import initialize_database

if __name__ == '__main__':
    settings = get_settings()
    initialize_database(settings.database)
    print(f'Banco comercial pronto: {settings.database}')
