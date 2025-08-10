import re
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from app.models import Entity, Mention, Completion, Brand
import spacy

class EntityExtractor:
    def __init__(self, db: Session):
        self.db = db
        self.nlp = None
        self._load_nlp()
        self.brand_cache = self._build_brand_cache()
    
    def _load_nlp(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
    
    def _build_brand_cache(self) -> Dict[str, int]:
        cache = {}
        brands = self.db.query(Brand).all()
        for brand in brands:
            cache[brand.name.lower()] = brand.id
            for alias in brand.aliases or []:
                cache[alias.lower()] = brand.id
        return cache
    
    def extract_entities(self, text: str) -> List[Dict]:
        entities = []
        
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "PERSON"]:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
        
        brand_pattern = "|".join(re.escape(brand) for brand in self.brand_cache.keys())
        if brand_pattern:
            for match in re.finditer(brand_pattern, text, re.IGNORECASE):
                entities.append({
                    "text": match.group(),
                    "label": "BRAND",
                    "start": match.start(),
                    "end": match.end()
                })
        
        list_pattern = r'(?:^|\n)\s*(?:\d+\.?|\-|\*)\s*([^,\n]+)'
        rank = 1
        for match in re.finditer(list_pattern, text):
            item_text = match.group(1).strip()
            if item_text:
                entities.append({
                    "text": item_text,
                    "label": "LIST_ITEM",
                    "start": match.start(1),
                    "end": match.end(1),
                    "rank": rank
                })
                rank += 1
        
        return entities
    
    def canonicalize_entity(self, entity_text: str) -> Optional[int]:
        normalized = entity_text.lower().strip()
        
        if normalized in self.brand_cache:
            return self.brand_cache[normalized]
        
        existing = self.db.query(Entity).filter(
            Entity.label == entity_text
        ).first()
        
        if existing:
            return existing.id if existing.canonical_id else existing.id
        
        new_entity = Entity(label=entity_text, type="UNKNOWN")
        self.db.add(new_entity)
        self.db.flush()
        return new_entity.id
    
    def process_completion(self, completion_id: int):
        completion = self.db.query(Completion).get(completion_id)
        if not completion:
            return
        
        entities = self.extract_entities(completion.text)
        
        for ent in entities:
            entity_id = self.canonicalize_entity(ent["text"])
            
            mention = Mention(
                completion_id=completion_id,
                entity_id=entity_id,
                start_idx=ent.get("start"),
                rank_pos=ent.get("rank"),
                confidence=0.8
            )
            self.db.add(mention)
        
        self.db.commit()