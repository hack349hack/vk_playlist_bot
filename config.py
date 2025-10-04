import os

# Токен бота Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')

# Данные VK API
VK_USER_ID = os.getenv('VK_USER_ID', '')
VK_ACCESS_TOKEN = os.getenv('VK_ACCESS_TOKEN', '')

# Настройки
MIN_LISTENS = 200
MAX_PLAYLISTS_TO_SHOW = 20
