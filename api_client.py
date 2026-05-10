import requests
from typing import List, Dict, Any
from config import Config


class APIClient:
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or Config.QURAN_API_URL
        self.mushaf = Config.MUSHAF
        self.page_size = 200  # Number of verses per request
    
    def get_verses(self) -> List[Dict[str, Any]]:
        all_verses = []
        offset = 0
        
        print("📥 Get verses (with pagination)...")
        
        while True:
            response = requests.get(
                f"{self.base_url}/ayahs/",
                params={
                    "mushaf": self.mushaf,
                    "offset": offset
                }
            )
            response.raise_for_status()
            verses = response.json()
            
            if not verses:
                break
            
            all_verses.extend(verses)
            
            if len(verses) < self.page_size:
                break
            
            offset += self.page_size
            print(f"   📄 offset {offset} → {len(all_verses)} The verse was received")
        
        return all_verses
    
    def get_translations(self, translator_uuid: str) -> List[Dict[str, Any]]:
        all_translations = []
        offset = 0
        
        print("📥 Get translations (with pagination)...")
        
        while True:
            response = requests.get(
                f"{self.base_url}/translations/{translator_uuid}/ayahs/",
                params={
                    "mushaf": self.mushaf,
                    "offset": offset
                }
            )
            response.raise_for_status()
            translations = response.json()
            
            if not translations:
                break
            
            all_translations.extend(translations)
            
            if len(translations) < self.page_size:
                break
            
            offset += self.page_size
            print(f"   📄 offset {offset} → {len(all_translations)} Translation received")
        
        return all_translations
