import requests
import re
import time
from typing import List, Dict, Optional
from config import VK_ACCESS_TOKEN, VK_USER_ID, MIN_LISTENS

class VKParser:
    def __init__(self):
        self.access_token = VK_ACCESS_TOKEN
        self.user_id = VK_USER_ID
        self.base_url = "https://api.vk.com/method"
        self.min_listens = MIN_LISTENS  # Сохраняем значение
        
    def extract_audio_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию об аудио из ссылки ВК"""
        try:
            # Для прямых ссылок на аудио
            if 'audio' in url:
                pattern = r'audio-?(\d+)_(\d+)'
                match = re.search(pattern, url)
                if match:
                    return {
                        'owner_id': int(match.group(1)), 
                        'audio_id': int(match.group(2))
                    }
            
            # Для ссылок вида vk.com/audio123456789_123456789
            pattern = r'audio(\d+)_(\d+)'
            match = re.search(pattern, url)
            if match:
                return {
                    'owner_id': int(match.group(1)), 
                    'audio_id': int(match.group(2))
                }
            
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
                'count': 10,  # Увеличиваем для лучшего поиска
                'auto_complete': 1,
                'sort': 2  # По популярности
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
                    'duration': audio['duration'],
                    'url': f"audio{audio['owner_id']}_{audio['id']}"
                }
            return None
        except Exception as e:
            print(f"Error searching audio: {e}")
            return None
    
    def search_playlists_global_by_audio(self, owner_id: int, audio_id: int) -> List[Dict]:
        """Глобальный поиск плейлистов по аудио"""
        try:
            print(f"Searching playlists for audio: {owner_id}_{audio_id}")
            
            url = f"{self.base_url}/audio.getPlaylistsByAudio"
            params = {
                'access_token': self.access_token,
                'v': '5.131',
                'audio_id': f"{owner_id}_{audio_id}",
                'count': 100  # Максимальное количество
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            print(f"API Response: {data}")
            
            if 'response' in data and 'items' in data['response']:
                playlists = data['response']['items']
                print(f"Found {len(playlists)} playlists")
                
                results = []
                for playlist in playlists:
                    listens = playlist.get('plays', 0)
                    if listens >= self.min_listens:  # Используем self.min_listens
                        owner_info = self.get_user_info(playlist['owner_id'])
                        results.append({
                            'playlist': playlist,
                            'listens': listens,
                            'playlist_url': f"https://vk.com/music/playlist/{playlist['owner_id']}_{playlist['id']}",
                            'owner_info': owner_info
                        })
                
                # Сортируем по количеству прослушиваний
                results.sort(key=lambda x: x['listens'], reverse=True)
                return results
            
            return []
            
        except Exception as e:
            print(f"Error in global audio search: {e}")
            return []

    def search_playlists_global_by_query(self, query: str) -> List[Dict]:
        """Глобальный поиск плейлистов по названию трека"""
        try:
            print(f"Searching audio for query: {query}")
            
            # Сначала находим трек
            audio_info = self.search_audio(query)
            if not audio_info:
                print("Audio not found")
                return []
            
            print(f"Found audio: {audio_info['artist']} - {audio_info['title']}")
            
            # Затем ищем плейлисты с этим треком
            return self.search_playlists_global_by_audio(
                audio_info['owner_id'], 
                audio_info['id']
            )
            
        except Exception as e:
            print(f"Error in global query search: {e}")
            return []

    def get_user_info(self, user_id: int) -> Dict:
        """Получает информацию о пользователе"""
        try:
            # Для групп (отрицательные ID)
            if user_id < 0:
                url = f"{self.base_url}/groups.getById"
                params = {
                    'access_token': self.access_token,
                    'v': '5.131',
                    'group_ids': abs(user_id),
                    'fields': 'name,screen_name'
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'response' in data and data['response']:
                    group = data['response'][0]
                    return {
                        'first_name': group['name'],
                        'last_name': '',
                        'profile_url': f"https://vk.com/{group.get('screen_name', '')}",
                        'is_group': True
                    }
            else:
                # Для пользователей
                url = f"{self.base_url}/users.get"
                params = {
                    'access_token': self.access_token,
                    'v': '5.131',
                    'user_ids': user_id,
                    'fields': 'first_name,last_name,screen_name'
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'response' in data and data['response']:
                    user = data['response'][0]
                    return {
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'profile_url': f"https://vk.com/{user.get('screen_name', 'id' + str(user_id))}",
                        'is_group': False
                    }
            return {}
            
        except Exception as e:
            print(f"Error getting user info: {e}")
            return {}

    def get_current_user(self):
        """Получает информацию о текущем пользователе (для отладки)"""
        try:
            url = f"{self.base_url}/users.get"
            params = {
                'access_token': self.access_token,
                'v': '5.131'
            }
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            return {'error': str(e)}
