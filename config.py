import os

# Токен бота Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')

# Service Token от ВКонтакте (получите из настроек приложения)
VK_SERVICE_TOKEN = os.getenv('VK_SERVICE_TOKEN', '')

# Настройки
MIN_LISTENS = 200
MAX_PLAYLISTS_TO_SHOW = 20

def check_config():
    missing_vars = []
    
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN':
        missing_vars.append('BOT_TOKEN')
    
    if not VK_SERVICE_TOKEN:
        missing_vars.append('VK_SERVICE_TOKEN')
    
    if missing_vars:
        raise Exception(f"Missing environment variables: {', '.join(missing_vars)}")

check_config()
