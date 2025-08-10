from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models import Prompt, Completion

router = APIRouter()

class PromptTemplate(BaseModel):
    type: str
    template: str

class PromptResponse(BaseModel):
    id: int
    type: str
    input_text: str
    
    class Config:
        from_attributes = True

PROMPT_TEMPLATES = {
    "B2E": [
        "What products or services are associated with {brand}?",
        "List companies that compete with {brand}.",
        "What is {brand} known for?",
        "Name key features of {brand}'s offerings.",
        "What industries does {brand} operate in?"
    ],
    "E2B": [
        "List the top {category} companies.",
        "Who are the leading providers of {product}?",
        "Which brands offer {service}?",
        "Name companies known for {feature}.",
        "What are the best {category} solutions?"
    ]
}

@router.get("/templates")
def get_prompt_templates():
    return PROMPT_TEMPLATES

@router.post("/generate")
def generate_prompts(brand: str, categories: List[str]):
    prompts = []
    
    for template in PROMPT_TEMPLATES["B2E"]:
        prompts.append(template.format(brand=brand))
    
    for category in categories:
        for template in PROMPT_TEMPLATES["E2B"]:
            prompts.append(template.format(
                category=category,
                product=category,
                service=category,
                feature=category
            ))
    
    return {"prompts": prompts}

@router.get("/run/{run_id}")
def get_run_prompts(run_id: int, db: Session = Depends(get_db)):
    prompts = db.query(Prompt).filter(Prompt.run_id == run_id).all()
    return prompts