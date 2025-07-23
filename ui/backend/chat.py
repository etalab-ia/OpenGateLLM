from typing import List, Tuple, Dict, Any
from openai import OpenAI
import requests
import streamlit as st

from ui.settings import settings


def generate_stream(messages: List[dict], params: dict, rag: bool, rerank: bool) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """
    Génère un stream de réponse avec les sources et les détails des chunks utilisés.
    
    Returns:
        Tuple contenant:
        - Le stream de réponse
        - La liste des sources (noms des documents)
        - La liste des chunks détaillés utilisés dans le RAG
    """
    sources = []
    rag_chunks = []  
    if rag and params["rag_params"]["method"] == "deepsearch":
        return generate_deepsearch_stream(messages, params)
    
    if rag:
        prompt = messages[-1]["content"]
        k = params["rag_params"]["k"] * 4 if rerank else params["rag_params"]["k"]
        data = {
            "collections": params["rag_params"]["collections"],
            "k": k,
            "prompt": messages[-1]["content"],
            "method": params["rag_params"]["method"],  
            "score_threshold": None,
        }
        response = requests.post(
            url=f"{settings.playground.api_url}/v1/search", 
            json=data, 
            headers={"Authorization": f"Bearer {st.session_state['user'].api_key}"}
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
                "chunk_id": search_result["chunk"].get("id", "Unknown")
            }
            rag_chunks.append(chunk_detail)

        if rerank:
            data = {
                "prompt": prompt,
                "input": [chunk["content"] for chunk in chunks],
            }
            response = requests.post(
                url=f"{settings.playground.api_url}/v1/rerank", 
                json=data, 
                headers={"Authorization": f"Bearer {st.session_state['user'].api_key}"}
            )
            assert response.status_code == 200, f"{response.status_code} - {response.json()}"

            rerank_scores = sorted(response.json()["data"], key=lambda x: x["score"])
            chunks = [chunks[result["index"]] for result in rerank_scores[: params["rag_params"]["k"]]]
            
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

    client = OpenAI(base_url=f"{settings.playground.api_url}/v1", api_key=st.session_state["user"].api_key)
    stream = client.chat.completions.create(stream=True, messages=messages, **params["sampling_params"])

    return stream, sources, rag_chunks


def generate_deepsearch_stream(messages: List[dict], params: dict) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """
    Génère une réponse DeepSearch avec recherche web approfondie.
    
    Returns:
        Tuple contenant:
        - La réponse complète (string directe pour DeepSearch)
        - La liste des sources (URLs)
        - Une liste vide (pas de chunks pour DeepSearch)
    """
    prompt = messages[-1]["content"]
    
    data = {
        "prompt": prompt,
        "model": params["rag_params"].get("deepsearch_model", params["sampling_params"]["model"]),
        "k": params["rag_params"].get("k", 5),
        "iteration_limit": params["rag_params"].get("iteration_limit", 2),
        "num_queries": params["rag_params"].get("num_queries", 2),
        "lang": params["rag_params"].get("lang", "fr"),
        "limited_domains": True  
    }
    
    response = requests.post(
        url=f"{settings.playground.api_url}/v1/deepsearch", 
        json=data, 
        headers={"Authorization": f"Bearer {st.session_state['user'].api_key}"}
    )
    
    if response.status_code != 200:
        error_detail = response.json().get("detail", "Erreur DeepSearch")
        raise Exception(f"DeepSearch failed: {error_detail}")
    
    result = response.json()
    
    deepsearch_response = result["response"]
    sources = result["sources"]
    metadata = result["metadata"]
    
    if "deepsearch_metadata" not in st.session_state:
        st.session_state["deepsearch_metadata"] = []
    st.session_state["deepsearch_metadata"].append(metadata)
    
    rag_chunks = []
    
    return deepsearch_response, sources, rag_chunks


def check_deepsearch_status() -> dict:
    """
    Vérifie si DeepSearch est disponible.
    """
    try:
        response = requests.get(
            url=f"{settings.playground.api_url}/v1/deepsearch/status",
            headers={"Authorization": f"Bearer {st.session_state['user'].api_key}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"available": False, "message": f"Status check failed: {response.status_code}"}
    except Exception as e:
        return {"available": False, "message": f"Error: {str(e)}"}


def format_chunk_for_display(chunk: Dict[str, Any], index: int) -> str:
    """
    Formate un chunk pour l'affichage dans l'interface.
    """
    content_preview = chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
    
    score_info = ""
    if "score" in chunk:
        score_info += f"**Score:** {chunk['score']:.3f}"
    if "rerank_score" in chunk:
        score_info += f" | **Rerank:** {chunk['rerank_score']:.3f}"
    
    return f"""
**Chunk {index + 1}** - {chunk['document_name']}
{score_info}

```
{content_preview}
```
"""


def get_chunk_full_content(chunk: Dict[str, Any]) -> str:
    """
    Retourne le contenu complet d'un chunk avec ses métadonnées.
    """
    metadata_str = "\n".join([f"**{k}:** {v}" for k, v in chunk["metadata"].items() if k != "content"])
    
    return f"""
### 📄 {chunk['document_name']}

#### Métadonnées
{metadata_str}

#### Contenu complet
```
{chunk['content']}
```
"""


def format_deepsearch_metadata(metadata: Dict[str, Any]) -> str:
    """
    Formate les métadonnées DeepSearch pour l'affichage.
    """
    return f"""
### 🔍 Métadonnées DeepSearch

- **Modèle utilisé :** {metadata.get('model_used', 'Unknown')}
- **Domaines :** Configuration par défaut (domaines restreints)
- **Temps d'exécution :** {metadata['elapsed_time']:.1f}s
- **Itérations :** {metadata['iterations']}
- **Requêtes générées :** {metadata['total_queries']}
- **Sources trouvées :** {metadata['sources_found']}
- **Tokens utilisés :** {metadata['total_input_tokens'] + metadata['total_output_tokens']:,}
  - Entrée : {metadata['total_input_tokens']:,}
  - Sortie : {metadata['total_output_tokens']:,}
"""