import requests
import re
from typing import List, Dict, Optional
from config import VK_SERVICE_TOKEN, MIN_LISTENS

class VKParser:
    def __init__(self):
        self.service_token = VK_SERVICE_TOKEN
        self.base_url = "https://api.vk.com/method"
        self.min_listens = MIN_LISTENS
        
        self.check_token()
        
    def check_token(self):
        """Проверяет валидность service token"""
        try:
            # Простая проверка через API wall.get (не требует прав)
            url = f"{self.base_url}/wall.get"
            params = {
                'access_token': self.service_token,
                'v': '5.199',
                'owner_id': 1,
                'count': 1
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'error' in data:
                error_code = data['error']['error_code']
                if error_code == 5:  # Authorization failed
                    raise Exception("Invalid service token")
                # Другие ошибки могут быть нормальными (например, нет доступа к стене)
            
            print("✅ Service token is valid")
            return True
            
        except Exception as e:
            print(f"❌ Service token check failed: {e}")
            raise
    
    def search_audio(self, query: str) -> Optional[Dict]:
        """Ищет аудио по названию"""
        try:
            url = f"{self.base_url}/audio.search"
            params = {
                'access_token': self.service_token,
                'v': '5.199',
                'q': query,
                'count': 10,
                'auto_complete': 1,
                'sort': 2
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'error' in data:
                print(f"VK API Error in audio.search: {data['error']}")
                return None
            
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
                'access_token': self.service_token,
                'v': '5.199',
                'audio_id': f"{owner_id}_{audio_id}",
                'count': 100
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'error' in data:
                print(f"VK API Error: {data['error']}")
                return []
            
            if 'response' in data and 'items' in data['response']:
                playlists = data['response']['items']
                print(f"Found {len(playlists)} playlists")
                
                results = []
                for playlist in playlists:
                    listens = playlist.get('plays', 0)
                    if listens >= self.min_listens:
                        owner_info = self.get_user_info(playlist['owner_id'])
                        results.append({
                            'playlist': playlist,
                            'listens': listens,
                            'playlist_url': f"https://vk.com/music/playlist/{playlist['owner_id']}_{playlist['id']}",
                            'owner_info': owner_info
                        })
                
                results.sort(key=lambda x: x['listens'], reverse=True)
                return results
            
            return []
            
        except Exception as e:
            print(f"Error in global audio search: {e}")
            return []

    def extract_audio_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию об аудио из ссылки ВК"""
        try:
            if 'audio' in url:
                pattern = r'audio-?(\d+)_(\d+)'
                match = re.search(pattern, url)
                if match:
                    return {
                        'owner_id': int(match.group(1)), 
                        'audio_id': int(match.group(2))
                    }
            
            pattern = r'audio(\d+)_(\d+)'
            match = re.search(pattern, url)
            if match:
                return {
                    'owner_id': int(match.group(1)), 
                    'audio_id': int(match.group(2))
                }
            
            return {'search_query': url}
            
        except Exception as e:
            print(f"Error extracting audio info: {e}")
            return None

    def search_playlists_global_by_query(self, query: str) -> List[Dict]:
        """Глобальный поиск плейлистов по названию трека"""
        try:
            print(f"Searching audio for query: {query}")
            
            audio_info = self.search_audio(query)
            if not audio_info:
                print("Audio not found")
                return []
            
            print(f"Found audio: {audio_info['artist']} - {audio_info['title']}")
            
            return self.search_playlists_global_by_audio(
                audio_info['owner_id'], 
                audio_info['id']
            )
            
        except Exception as e:
            print(f"Error in global query search: {e}")
            return []

    def get_user_info(self, user_id: int) -> Dict:
        """Получает информацию о пользователе через service token"""
        try:
            if user_id < 0:  # Группа
                url = f"{self.base_url}/groups.getById"
                params = {
                    'access_token': self.service_token,
                    'v': '5.199',
                    'group_ids': abs(user_id)
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'response' in data and data['response']:
                    group = data['response'][0]
                    return {
                        'name': group['name'],
                        'is_group': True,
                        'profile_url': f"https://vk.com/public{abs(user_id)}"
                    }
            else:  # Пользователь
                url = f"{self.base_url}/users.get"
                params = {
                    'access_token': self.service_token,
                    'v': '5.199',
                    'user_ids': user_id
                }
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'response' in data and data['response']:
                    user = data['response'][0]
                    return {
                        'name': f"{user['first_name']} {user['last_name']}",
                        'is_group': False,
                        'profile_url': f"https://vk.com/id{user_id}"
                    }
            return {'name': 'Неизвестно', 'is_group': False}
            
        except Exception as e:
            print(f"Error getting user info: {e}")
            return {'name': 'Ошибка получения', 'is_group': False}

    def get_current_user(self):
        """Информация о текущем приложении"""
        try:
            url = f"{self.base_url}/users.get"
            params = {
                'access_token': self.service_token,
                'v': '5.199',
                'user_ids': 1
            }
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            return {'error': str(e)}
