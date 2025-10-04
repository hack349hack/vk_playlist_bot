import requests
import re
import time
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class VKParser:
    def __init__(self, user_token: str = None):
        self.token = user_token
        self.base_url = "https://api.vk.com/method"
        self.session = requests.Session()
        
        if user_token:
            self.check_token(user_token)
    
    def set_token(self, token: str) -> Tuple[bool, str]:
        """Установка токена пользователя"""
        try:
            self.token = token
            return self.check_token(token)
        except Exception as e:
            return False, str(e)
    
    def check_token(self, token: str) -> Tuple[bool, str]:
        """Проверка валидности токена"""
        try:
            data = self.make_request('users.get', {}, token)
            if not data:
                return False, "❌ Токен невалиден"
            
            user_info = data['response'][0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
            
            # Проверяем права на audio
            audio_test = self.make_request('audio.search', {
                'q': 'test',
                'count': 1
            }, token)
            
            if not audio_test:
                return False, "❌ Нет доступа к аудио API"
            
            return True, f"✅ Токен валиден. Привет, {user_name}!"
            
        except Exception as e:
            return False, f"❌ Ошибка проверки: {str(e)}"
    
    def make_request(self, method: str, params: dict, token: str = None) -> Optional[dict]:
        """Универсальный метод для запросов к API"""
        try:
            url = f"{self.base_url}/{method}"
            used_token = token or self.token
            params.update({
                'access_token': used_token,
                'v': '5.199'
            })
            
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()
            
            if 'error' in data:
                error = data['error']
                logger.error(f"VK API Error in {method}: {error}")
                
                if error.get('error_code') == 6:  # Too many requests
                    time.sleep(1)
                    return self.make_request(method, params, used_token)
                elif error.get('error_code') == 9:  # Flood control
                    time.sleep(10)
                    return self.make_request(method, params, used_token)
                
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Request error in {method}: {e}")
            return None
    
    def search_audio(self, query: str) -> Optional[Dict]:
        """Поиск аудио по названию"""
        if not self.token:
            return None
            
        data = self.make_request('audio.search', {
            'q': query,
            'count': 5,
            'auto_complete': 1,
            'sort': 2
        })
        
        if not data or not data['response']['items']:
            return None
        
        audio = data['response']['items'][0]
        return {
            'id': audio['id'],
            'owner_id': audio['owner_id'],
            'artist': audio['artist'],
            'title': audio['title'],
            'url': f"audio{audio['owner_id']}_{audio['id']}"
        }
    
    def search_playlists_by_audio(self, owner_id: int, audio_id: int) -> List[Dict]:
        """Поиск плейлистов по аудио"""
        if not self.token:
            return []
            
        data = self.make_request('audio.getPlaylistsByAudio', {
            'audio_id': f"{owner_id}_{audio_id}",
            'count': 100
        })
        
        if not data:
            return []
        
        playlists = data['response'].get('items', [])
        results = []
        
        for playlist in playlists:
            listens = playlist.get('plays', 0)
            if listens >= 200:  # MIN_LISTENS
                results.append({
                    'title': playlist.get('title', 'Без названия'),
                    'listens': listens,
                    'url': f"https://vk.com/music/playlist/{playlist['owner_id']}_{playlist['id']}",
                    'owner_id': playlist['owner_id'],
                    'playlist_id': playlist['id']
                })
        
        results.sort(key=lambda x: x['listens'], reverse=True)
        return results
    
    def extract_audio_info(self, url: str) -> Optional[Dict]:
        """Извлечение информации из ссылки на аудио"""
        try:
            patterns = [
                r'audio-?(\d+)_(\d+)',
                r'audio(\d+)_(\d+)',
                r'audios(\d+)_(\d+)',
                r'\/audio(\d+)_(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return {
                        'owner_id': int(match.group(1)),
                        'audio_id': int(match.group(2))
                    }
            return None
        except:
            return None
    
    def search(self, input_data: str) -> List[Dict]:
        """Универсальный метод поиска"""
        if not self.token:
            return []
            
        try:
            # Пытаемся извлечь из ссылки
            audio_info = self.extract_audio_info(input_data)
            if audio_info:
                return self.search_playlists_by_audio(
                    audio_info['owner_id'], 
                    audio_info['audio_id']
                )
            
            # Ищем по тексту
            audio_data = self.search_audio(input_data)
            if audio_data:
                return self.search_playlists_by_audio(
                    audio_data['owner_id'],
                    audio_data['id']
                )
            
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
