from typing import Any

from openai import OpenAI
import requests
import streamlit as st

from playground.configuration import configuration


def generate_stream(messages: list[dict], params: dict, rag: bool, rerank: bool) -> tuple[str, list[str], list[dict[str, Any]]]:
    """
    Génère un stream de réponse avec les sources et les détails des chunks utilisés.

    Returns:
        Tuple contenant:
        - Le stream de réponse
        - La liste des sources (noms des documents)
        - La liste des chunks détaillés utilisés dans le RAG
    """
    sources = []
    rag_chunks = []  # Nouveau : stockage des chunks détaillés

    if rag:
        prompt = messages[-1]["content"]
        # Use "rag_params" instead of "rag"
        k = params["rag_params"]["k"] * 4 if rerank else params["rag_params"]["k"]
        data = {
            "collections": params["rag_params"]["collections"],
            "k": k,
            "prompt": messages[-1]["content"],
            "method": params["rag_params"]["method"],  # Add method from rag_params
            "score_threshold": None,
        }
        response = requests.post(
            url=f"{configuration.playground.api_url}/v1/search", json=data, headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
        )
        assert response.status_code == 200, f"{response.status_code} - {response.json()}"

        prompt_template = """Réponds à la question suivante de manière claire en te basant sur les extraits de documents ci-dessous. Si les documents ne sont pas pertinents pour répondre à la question, réponds que tu ne sais pas ou réponds directement la question à l'aide de tes connaissances. Réponds en français. La question de l'utilisateur est : {prompt}

Les documents sont :

{chunks} """
        chunks = [chunk["chunk"] for chunk in response.json()["data"]]

        # Stocker les chunks détaillés AVANT le reranking
        for search_result in response.json()["data"]:
            chunk_detail = {
                "content": search_result["chunk"]["content"],
                "metadata": search_result["chunk"]["metadata"],
                "score": search_result.get("score", 0),
                "document_name": search_result["chunk"]["metadata"].get("document_name", "Unknown"),
                "chunk_id": search_result["chunk"].get("id", "Unknown"),
            }
            rag_chunks.append(chunk_detail)

        if rerank:
            data = {
                "prompt": prompt,
                "input": [chunk["content"] for chunk in chunks],
            }
            response = requests.post(
                url=f"{configuration.playground.api_url}/v1/rerank",
                json=data,
                headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"},
            )
            assert response.status_code == 200, f"{response.status_code} - {response.json()}"

            rerank_scores = sorted(response.json()["data"], key=lambda x: x["score"])
            # Use "rag_params" instead of "rag"
            chunks = [chunks[result["index"]] for result in rerank_scores[: params["rag_params"]["k"]]]

            # Réorganiser les chunks détaillés selon le reranking
            reranked_chunks = []
            for result in rerank_scores[: params["rag_params"]["k"]]:
                original_chunk = rag_chunks[result["index"]]
                original_chunk["rerank_score"] = result["score"]
                reranked_chunks.append(original_chunk)
            rag_chunks = reranked_chunks

        sources = list(set([chunk["metadata"]["document_name"] for chunk in chunks]))
        chunks = [chunk["content"] for chunk in chunks]
        prompt = prompt_template.format(prompt=prompt, chunks="\n\n".join(chunks))
        messages = messages[:-1] + [{"role": "user", "content": prompt}]

    client = OpenAI(base_url=f"{configuration.playground.api_url}/v1", api_key=st.session_state["user"].api_key)
    stream = client.chat.completions.create(stream=True, messages=messages, **params["sampling_params"])

    return stream, sources, rag_chunks


def format_chunk_for_display(chunk: dict[str, Any], index: int) -> str:
    """
    Formate un chunk pour l'affichage dans l'interface.
    """
    content_preview = chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]

    score_info = ""
    if "score" in chunk:
        score_info += f"**Score:** {chunk["score"]:.3f}"
    if "rerank_score" in chunk:
        score_info += f" | **Rerank:** {chunk["rerank_score"]:.3f}"

    return f"""
**Chunk {index + 1}** - {chunk["document_name"]}
{score_info}

```
{content_preview}
```
"""


def get_chunk_full_content(chunk: dict[str, Any]) -> str:
    """
    Retourne le contenu complet d'un chunk avec ses métadonnées.
    """
    metadata_str = "\n".join([f"**{k}:** {v}" for k, v in chunk["metadata"].items() if k != "content"])

    return f"""
### 📄 {chunk["document_name"]}

#### Métadonnées
{metadata_str}

#### Contenu complet
```
{chunk["content"]}
```
"""
