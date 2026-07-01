# app/services/rag_retriever.py
from typing import Dict, Any

from app.db.clients import pinecone_client, embeddings
from app.utils.logger import logger


INDEX_NAME = "mtca-index"


def retrieve_vector_context(
    state: Dict[str, Any],
    query: str,
    top_k: int = 5,
) -> str:
    """
    Retrieves the most relevant knowledge base chunks
    using the tenant-specific Pinecone namespace
    stored in LangGraph state.

    Namespace source:
        state["mongo_rules"]["pinecone"]["knowledgeNamespace"]
    """

    tenant_config = state.get("mongo_rules", {})

    namespace = (
        tenant_config
        .get("pinecone", {})
        .get("knowledgeNamespace")
    )

    if not namespace:
        raise ValueError(
            "Missing pinecone.knowledgeNamespace "
            "in tenant configuration."
        )

    logger.info("")
    logger.info("=" * 100)
    logger.info("🔍 VECTOR RETRIEVAL")
    logger.info("=" * 100)
    logger.info(f"Namespace : {namespace}")
    logger.info(f"Top K     : {top_k}")
    logger.info(f"Query     : {query}")

    embedding = embeddings.embed_query(query)

    index = pinecone_client.Index(INDEX_NAME)

    results = index.query(
        namespace=namespace,
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
    )

    matches = results.get(
        "matches",
        [],
    )

    logger.info("")
    logger.info("=" * 100)
    logger.info("📚 RETRIEVED KNOWLEDGE")
    logger.info("=" * 100)

    context_blocks = []

    for i, match in enumerate(
        matches,
        start=1,
    ):

        metadata = match.get(
            "metadata",
            {},
        )

        score = match.get(
            "score",
            0,
        )

        title = metadata.get(
            "title",
            "Untitled",
        )

        text = metadata.get(
            "text",
            "",
        )

        logger.info("-" * 100)
        logger.info(f"Chunk      : {i}")
        logger.info(f"Similarity : {score:.4f}")
        logger.info(f"Title      : {title}")

        context_blocks.append(
            f"""
### {title}

{text}
""".strip()
        )

    logger.info("")
    logger.info("=" * 100)
    logger.info("✅ VECTOR RETRIEVAL COMPLETE")
    logger.info("=" * 100)

    return "\n\n".join(context_blocks)