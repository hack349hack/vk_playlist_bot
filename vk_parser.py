import requests
import re
from typing import List, Dict, Optional
from config import VK_ACCESS_TOKEN, VK_USER_ID, MIN_LISTENS

class VKParser:
    def __init__(self):
        self.access_token = VK_ACCESS_TOKEN
        self.user_id = VK_USER_ID
        self.base_url = "https://api.vk.com/method"
        
    def extract_audio_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию об аудио из ссылки ВК"""
        try:
            # Для прямых ссылок на аудио
            if 'audio' in url:
                pattern = r'audio-?(\d+)_(\d+)'
                match = re.search(pattern, url)
                if match:
                    return {'owner_id': match.group(1), 'audio_id': match.group(2)}
            
            # Для поиска по названию
            return {'search_query': url}
        except Exception as e:
            print(f"Error extracting audio info: {e}")
            return None
    
    def search_audio(self, query: str) -> Optional[Dict]:
        """Ищет аудио по названию"""
        try:
            url = f"{self.base_url}/audio.search"
            params = {
                'access_token': self.access_token,
                'v': '5.131',
                'q': query,
                'count': 1,
                'auto_complete': 1
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'response' in data and data['response']['items']:
                audio = data['response']['items'][0]
                return {
                    'id': audio['id'],
                    'owner_id': audio['owner_id'],
                    'artist': audio['artist'],
                    'title': audio['title'],
                    'duration': audio['duration']
                }
            return None
        except Exception as e:
            print(f"Error searching audio: {e}")
            return None
    
    def get_user_playlists(self) -> List[Dict]:
        """Получает все плейлисты пользователя"""
        try:
            url = f"{self.base_url}/audio.getPlaylists"
            params = {
                'access_token': self.access_token,
                'v': '5.131',
                'owner_id': self.user_id,
                'count': 100
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'response' in data:
                return data['response']['items']
            return []
        except Exception as e:
            print(f"Error getting playlists: {e}")
            return []
    
    def search_audio_in_playlists(self, audio_owner_id: int, audio_id: int) -> List[Dict]:
        """Ищет аудио во всех плейлистах пользователя"""
        try:
            playlists = self.get_user_playlists()
            results = []
            
            for playlist in playlists:
                # Получаем аудио из плейлиста
                url = f"{self.base_url}/audio.get"
                params = {
                    'access_token': self.access_token,
                    'v': '5.131',
                    'owner_id': playlist['owner_id'],
                    'playlist_id': playlist['id'],
                    'count': 1000
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'response' in data:
                    audio_items = data['response']['items']
                    listens = playlist.get('plays', 0)
                    
                    # Проверяем наличие нужного аудио
                    for audio in audio_items:
                        if (audio['owner_id'] == audio_owner_id and 
                            audio['id'] == audio_id and 
                            listens >= MIN_LISTENS):
                            
                            results.append({
                                'playlist': playlist,
                                'listens': listens,
                                'playlist_url': f"https://vk.com/music/playlist/{playlist['owner_id']}_{playlist['id']}"
                            })
                            break
            
            # Сортируем по количеству прослушиваний
            results.sort(key=lambda x: x['listens'], reverse=True)
            return results
            
        except Exception as e:
            print(f"Error searching in playlists: {e}")
            return []

    def search_by_query_in_playlists(self, query: str) -> List[Dict]:
        """Ищет трек по названию во всех плейлистах"""
        try:
            # Сначала ищем сам трек
            audio_info = self.search_audio(query)
            if not audio_info:
                return []
            
            # Затем ищем в плейлистах
            return self.search_audio_in_playlists(
                audio_info['owner_id'], 
                audio_info['id']
            )
            
        except Exception as e:
            print(f"Error searching by query: {e}")
            return []
