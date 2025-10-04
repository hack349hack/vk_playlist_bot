import requests
import re
from typing import List, Dict, Optional
from config import VK_USER_TOKEN, MIN_LISTENS

class VKParser:
    def __init__(self):
        self.user_token = VK_USER_TOKEN
        self.base_url = "https://api.vk.com/method"
        self.min_listens = MIN_LISTENS
        
        self.check_token()
        
    def check_token(self):
        """Проверяет валидность user token"""
        try:
            url = f"{self.base_url}/users.get"
            params = {
                'access_token': self.user_token,
                'v': '5.199'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'error' in data:
                error_msg = data['error']['error_msg']
                raise Exception(f"Invalid user token: {error_msg}")
                    
            print("✅ User token is valid")
            return True
            
        except Exception as e:
            print(f"❌ User token check failed: {e}")
            raise
    
    def search_audio(self, query: str) -> Optional[Dict]:
        """Ищет аудио по названию"""
        try:
            url = f"{self.base_url}/audio.search"
            params = {
                'access_token': self.user_token,
                'v': '5.199',
                'q': query,
                'count': 1,
                'auto_complete': 1
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            print(f"Audio search response: {data}")
            
            if 'error' in data:
                error_msg = data['error']['error_msg']
                print(f"VK API Error: {error_msg}")
                return None
            
            if 'response' in data and data['response']['items']:
                audio = data['response']['items'][0]
                return {
                    'id': audio['id'],
                    'owner_id': audio['owner_id'],
                    'artist': audio['artist'],
                    'title': audio['title'],
                    'url': f"audio{audio['owner_id']}_{audio['id']}"
                }
            return None
        except Exception as e:
            print(f"Error searching audio: {e}")
            return None
    
    def search_playlists_by_audio(self, owner_id: int, audio_id: int) -> List[Dict]:
        """Ищет плейлисты по аудио"""
        try:
            print(f"Searching playlists for: {owner_id}_{audio_id}")
            
            url = f"{self.base_url}/audio.getPlaylistsByAudio"
            params = {
                'access_token': self.user_token,
                'v': '5.199',
                'audio_id': f"{owner_id}_{audio_id}",
                'count': 50
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            print(f"Playlists response: {data}")
            
            if 'error' in data:
                error_msg = data['error']['error_msg']
                print(f"VK API Error: {error_msg}")
                return []
            
            if 'response' in data and 'items' in data['response']:
                playlists = data['response']['items']
                print(f"Found {len(playlists)} playlists")
                
                results = []
                for playlist in playlists:
                    listens = playlist.get('plays', 0)
                    if listens >= self.min_listens:
                        results.append({
                            'title': playlist.get('title', 'Без названия'),
                            'listens': listens,
                            'url': f"https://vk.com/music/playlist/{playlist['owner_id']}_{playlist['id']}",
                            'owner_id': playlist['owner_id']
                        })
                
                results.sort(key=lambda x: x['listens'], reverse=True)
                return results
            
            return []
            
        except Exception as e:
            print(f"Error searching playlists: {e}")
            return []

    def extract_audio_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию об аудио из ссылки"""
        try:
            # Разные форматы ссылок ВК
            patterns = [
                r'audio-?(\d+)_(\d+)',
                r'audio(\d+)_(\d+)',
                r'audios(\d+)_(\d+)'
            ]
            
            for pattern in patterns:
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

    def search_by_query(self, query: str) -> List[Dict]:
        """Поиск плейлистов по названию трека"""
        try:
            print(f"Searching for query: {query}")
            
            audio_info = self.search_audio(query)
            if not audio_info:
                print("Audio not found")
                return []
            
            print(f"Found audio: {audio_info['artist']} - {audio_info['title']}")
            
            return self.search_playlists_by_audio(
                audio_info['owner_id'], 
                audio_info['id']
            )
            
        except Exception as e:
            print(f"Error in query search: {e}")
            return []
