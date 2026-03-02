from openai import AsyncOpenAI
from app.settings import SETTINGS

client = AsyncOpenAI(
    api_key=SETTINGS.OPENAI_API_KEY.get_secret_value(),
    base_url=f"{SETTINGS.OPENAI_API_BASE_URL}",
)


async def _embed_openai(text: str) -> list[float]:
    response = await client.embeddings.create(
        input=text, model="openai/text-embedding-3-small"
    )
    return response.data[0].embedding
