# app/serrvices/routing_retriever.py
from typing import Dict, List, Any

from pinecone import PineconeException

from app.db.clients import pinecone_client, embeddings
from app.utils.logger import divider, info


INDEX_NAME = "mtca-index"


def retrieve_routing_examples(
    state: Dict[str, Any],
    query: str,
    top_k: int = 3,
) -> List[Dict]:
    """
    Retrieves routing examples using the tenant-specific
    routing Pinecone namespace stored in LangGraph state.

    Namespace source:
        state["mongo_rules"]["pinecone"]["routingNamespace"]
    """

    tenant_config = state.get(
        "mongo_rules",
        {},
    )

    namespace = (
        tenant_config
        .get("pinecone", {})
        .get("routingNamespace")
    )

    if not namespace:
        raise ValueError(
            "Missing pinecone.routingNamespace "
            "in tenant configuration."
        )

    divider("🔍 ROUTING RETRIEVAL")

    info(
        "Namespace",
        namespace,
    )

    info(
        "Top K",
        top_k,
    )

    info(
        "Query",
        query,
    )

    try:

        embedding = embeddings.embed_query(
            query
        )

        index = pinecone_client.Index(
            INDEX_NAME
        )

        response = index.query(
            namespace=namespace,
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
        )

    except PineconeException as exc:

        raise RuntimeError(
            f"Pinecone routing retrieval failed: {exc}"
        ) from exc


    matches = response.get(
        "matches",
        [],
    )

    if not matches:

        info(
            "Result",
            "No routing examples found.",
        )

        return []


    examples = []

    for match in matches:

        metadata = match.get(
            "metadata",
            {},
        )

        examples.append(
            {
                "score": round(
                    float(
                        match.get(
                            "score",
                            0,
                        )
                    ),
                    4,
                ),

                "user_message": metadata.get(
                    "user_message",
                    "",
                ),

                "expected_action": metadata.get(
                    "expected_action",
                    "",
                ),

                "reasoning": metadata.get(
                    "reasoning",
                    "",
                ),
            }
        )


    divider(
        "✅ ROUTING RETRIEVAL COMPLETE"
    )

    return examples