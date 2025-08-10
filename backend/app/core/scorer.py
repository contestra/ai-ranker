import numpy as np
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from scipy import stats
from app.models import Run, Prompt, Completion, Mention, Entity, Brand, Metric

class Scorer:
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_mention_rate(self, brand_id: int, run_id: int) -> Tuple[float, float, float]:
        prompts = self.db.query(Prompt).filter(Prompt.run_id == run_id).all()
        total_completions = 0
        mentions = 0
        
        for prompt in prompts:
            completions = self.db.query(Completion).filter(
                Completion.prompt_id == prompt.id
            ).all()
            
            for completion in completions:
                total_completions += 1
                has_mention = self.db.query(Mention).join(Entity).filter(
                    Mention.completion_id == completion.id,
                    Entity.canonical_id == brand_id
                ).first() is not None
                
                if has_mention:
                    mentions += 1
        
        if total_completions == 0:
            return 0.0, 0.0, 0.0
        
        rate = mentions / total_completions
        ci_low, ci_high = self._wilson_confidence_interval(mentions, total_completions)
        
        return rate, ci_low, ci_high
    
    def calculate_avg_rank(self, brand_id: int, run_id: int) -> float:
        ranks = []
        
        prompts = self.db.query(Prompt).filter(Prompt.run_id == run_id).all()
        for prompt in prompts:
            completions = self.db.query(Completion).filter(
                Completion.prompt_id == prompt.id
            ).all()
            
            for completion in completions:
                mention = self.db.query(Mention).join(Entity).filter(
                    Mention.completion_id == completion.id,
                    Entity.canonical_id == brand_id,
                    Mention.rank_pos.isnot(None)
                ).first()
                
                if mention:
                    ranks.append(mention.rank_pos)
        
        return np.mean(ranks) if ranks else float('inf')
    
    def calculate_weighted_score(
        self, 
        mention_rate: float, 
        avg_rank: float,
        max_rank: int = 10
    ) -> float:
        if avg_rank == float('inf'):
            return 0.0
        
        rank_weight = max(0, 1 - (avg_rank - 1) / max_rank)
        return mention_rate * rank_weight
    
    def _wilson_confidence_interval(
        self, 
        successes: int, 
        trials: int, 
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        if trials == 0:
            return 0.0, 0.0
        
        p_hat = successes / trials
        z = stats.norm.ppf((1 + confidence) / 2)
        
        denominator = 1 + z**2 / trials
        center = (p_hat + z**2 / (2 * trials)) / denominator
        margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials) / denominator
        
        return max(0, center - margin), min(1, center + margin)
    
    def calculate_stability(self, brand_id: int, run_id: int) -> float:
        mention_rates = []
        
        prompts = self.db.query(Prompt).filter(Prompt.run_id == run_id).all()
        grouped_prompts = {}
        for prompt in prompts:
            key = prompt.input_text
            if key not in grouped_prompts:
                grouped_prompts[key] = []
            grouped_prompts[key].append(prompt)
        
        for prompt_group in grouped_prompts.values():
            group_mentions = 0
            group_total = 0
            
            for prompt in prompt_group:
                completions = self.db.query(Completion).filter(
                    Completion.prompt_id == prompt.id
                ).all()
                
                for completion in completions:
                    group_total += 1
                    has_mention = self.db.query(Mention).join(Entity).filter(
                        Mention.completion_id == completion.id,
                        Entity.canonical_id == brand_id
                    ).first() is not None
                    
                    if has_mention:
                        group_mentions += 1
            
            if group_total > 0:
                mention_rates.append(group_mentions / group_total)
        
        if len(mention_rates) < 2:
            return 1.0
        
        mean_rate = np.mean(mention_rates)
        if mean_rate == 0:
            return 1.0
        
        cv = np.std(mention_rates) / mean_rate
        return 1 - min(cv, 1)
    
    def save_metrics(self, run_id: int, brand_id: int, concept_id: Optional[int] = None):
        mention_rate, ci_low, ci_high = self.calculate_mention_rate(brand_id, run_id)
        avg_rank = self.calculate_avg_rank(brand_id, run_id)
        weighted_score = self.calculate_weighted_score(mention_rate, avg_rank)
        
        metric = Metric(
            run_id=run_id,
            brand_id=brand_id,
            concept_id=concept_id,
            mention_rate=mention_rate,
            avg_rank=avg_rank if avg_rank != float('inf') else None,
            weighted_score=weighted_score,
            ci_low=ci_low,
            ci_high=ci_high
        )
        
        self.db.add(metric)
        self.db.commit()
        
        return metric