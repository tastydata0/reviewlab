import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models.embedding import Embedding1536, Embedding768
from ..utils.embedding.main import (
    EmbeddingStrategy1536,
    EmbeddingStrategy768,
    embed_1536,
    embed_768,
)


class EmbeddingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_embedding_768(
        self, text: str, strategy: EmbeddingStrategy768 = EmbeddingStrategy768.HF
    ) -> Embedding768:
        """Эмбеддит текст в вектор размера 768 и сохраняет в БД."""
        vector = await embed_768(text, strategy)

        db_embedding = Embedding768(embedding=vector)
        self.session.add(db_embedding)
        await self.session.commit()
        await self.session.refresh(db_embedding)

        return db_embedding

    async def create_embedding_1536(
        self, text: str, strategy: EmbeddingStrategy1536 = EmbeddingStrategy1536.OPENAI
    ) -> Embedding1536:
        """Эмбеддит текст в вектор размера 1536 и сохраняет в БД."""
        vector = await embed_1536(text, strategy)

        db_embedding = Embedding1536(embedding=vector)
        self.session.add(db_embedding)
        await self.session.commit()
        await self.session.refresh(db_embedding)

        return db_embedding

    async def get_or_create_embedding_1536(
        self,
        text: str,
        task_id: str | None,
        user_id: str | None,
        submission_id: str | None,
        strategy: EmbeddingStrategy1536 = EmbeddingStrategy1536.OPENAI,
    ) -> Embedding1536:
        chunk_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Ищем, есть ли уже такой хэш (независимо от того, кто его отправил)
        # Если кто-то уже эмбеддил этот точный кусок кода, мы можем переиспользовать вектор
        stmt = select(Embedding1536).where(Embedding1536.chunk_hash == chunk_hash).limit(1)
        res = await self.session.execute(stmt)
        existing = res.scalars().first()

        if existing:
            vector = existing.embedding
        else:
            vector = await embed_1536(text, strategy)

        # Сохраняем новую запись, чтобы её можно было искать по task_id/user_id/submission_id
        db_embedding = Embedding1536(
            chunk_hash=chunk_hash,
            task_id=task_id,
            user_id=user_id,
            submission_id=submission_id,
            embedding=vector,
        )
        self.session.add(db_embedding)
        await self.session.commit()
        await self.session.refresh(db_embedding)

        return db_embedding
