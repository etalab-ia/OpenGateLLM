# Models

OpenGateLLM allows you to configure 4 types of models:

-   text-generation: language model
-   text-embeddings-inference: embeddings model
-   automatic-speech-recognition: audio transcription model
-   text-classification: reranking model

To configure the connection to these models, see the
[deployment](../deployment.md) documentation.

## text-generation

For language models, you can use any API compatible with the
[OpenAI](https://platform.openai.com/docs/api-reference/chat/create)
format, meaning it has a `/v1/chat/completions` endpoint.

If you want to deploy a language model, we recommend using
[vLLM](https://github.com/vllm-project/vllm). Example of a language
model:
[guillaumetell-7b](https://huggingface.co/AgentPublic/guillaumetell-7b).

**⚠️ OpenGateLLM can be run without a text-generation model**

## text-embeddings-inference

For embeddings models, you can use any API compatible with the
[OpenAI](https://platform.openai.com/docs/api-reference/embeddings)
format, meaning it has a `/v1/embeddings` endpoint.

If you want to deploy an embeddings model, we recommend using
[HuggingFace Text Embeddings
Inference](https://github.com/huggingface/text-embeddings-inference).
Example of an embeddings model:
[multilingual-e5-large](https://huggingface.co/intfloat/multilingual-e5-large).

**⚠️ OpenGateLLM needs a text-embeddings-inference model to run.**

## automatic-speech-recognition

For audio transcription models, you can use any API compatible with the
[OpenAI](https://platform.openai.com/docs/api-reference/audio/create-transcription)
format, meaning it has a `/v1/audio/transcriptions` endpoint.

If you want to deploy an audio transcription model, we recommend using
[Whisper OpenAI API](https://github.com/etalab-ia/whisper-openai-api).
Example of an audio transcription model:
[whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo).

**⚠️ OpenGateLLM can be run without a automatic-speech-recognition model**

## text-classification

For reranking models, you must use an API compatible with the format
provided by the [HuggingFace Text Embeddings
Inference](https://huggingface.github.io/text-embeddings-inference/)
API, meaning it has a `/rerank` endpoint.

If you want to deploy a reranking model, we recommend using [HuggingFace
Text Embeddings
Inference](https://github.com/huggingface/text-embeddings-inference).
Example of a reranking model:
[bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3).

**⚠️ OpenGateLLM can be run without a text-classification model**