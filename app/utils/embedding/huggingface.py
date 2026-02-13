import httpx
from app.settings import SETTINGS

MODEL_ID = "flax-sentence-embeddings/st-codesearch-distilroberta-base"
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_ID}/pipeline/feature-extraction"


async def _embed_huggingface(text: str) -> list[float]:
    """генерирует вектор через HuggingFace Inference API (Async)."""
    headers = {"Authorization": f"Bearer {SETTINGS.HF_TOKEN.get_secret_value()}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            API_URL, 
            headers=headers, 
            json={"inputs": text},
            timeout=30.0
        )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"HF API Error: {response.status_code} - {response.text}")
