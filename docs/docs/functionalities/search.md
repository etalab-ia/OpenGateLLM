# Search

The Albert API allows you to interact with a vector database (_vector store_) to perform [RAG](https://en.wikipedia.org/wiki/Retrieval-augmented_generation). The API lets you feed this vector store by importing files, which are automatically processed and inserted into the _vector store_.

Collections are the storage spaces in this _vector store_. They are used to organize the files imported by the API. These files are converted into documents containing the extracted text. These documents are then split into chunks and converted into vectors using an embeddings model. These vectors, along with the vectorized text, are stored in the vector database.

Integration therefore occurs in 3 phases:

- **File**: the original file (not stored)
- **Document**: text extracted from a file
- **Chunk**: a portion of text split from a document

<p align="center">
  <img src="../../static/img/collections_005.png" width="40%"></img>
</p>

Once imported, you can query the API to retrieve the documents or chunks you are interested in by following this hierarchy based on the 3 entities:

- **Collection**: the storage space for documents and chunks  
- **Document**: a portion of text extracted from a file  
- **Chunk**: a portion of text split from a document  

<p align="center">
  <img src="../../static/img/collections_001.png" width="20%"></img>
</p>

## Creating a Collection

Before importing a file, you must first create a collection using the `POST /v1/collections` endpoint. This endpoint performs three operations in sequence:

1. Creates a unique ID (_collection_id_).
2. Creates a collection named after the ID.
3. Creates an entry in the collection named _collections_ that stores metadata for the other collections. This metadata includes the collection name, the number of files in the collection, and the embeddings model associated with the collection. This entry uses the same ID as the collection ID.

![](../../static/img/collections_002.png)

You can list your collections using the `GET /v1/collections` endpoint.

**Why store the name of an embeddings model for each collection?**

It is important to understand that each collection is associated with an embeddings model because this determines similarity search between multiple collections. Since an embeddings model defines its own vector space, it would be inconsistent to perform a similarity search between vectors that were not created by the same embeddings model.

As a result, the API design makes it impossible to perform similarity searches across files stored in collections associated with different embeddings models. Additionally, by defining an embeddings model at collection creation, you ensure that all files in the same collection are vectorized with the same model.

## Importing a File

Once the collection is created, you can import files into the API using the `POST /v1/files` endpoint. The API accepts multiple file types, including JSON, PDF, Markdown, and HTML. The endpoint performs the following steps:

1. Detects the file type if not specified by the user.
2. Creates a unique ID (_document_id_).
3. Creates an entry in a collection named _documents_ that stores the document's metadata. This entry uses the same ID as the document ID.
4. Runs the processing pipeline:
   1. _parsing_: extracts text from the file (conversion into a _document_)
   2. _chunking_: splits the file into paragraphs (conversion into _chunks_)
   3. _vectorization_: creates a vector for each _chunk_
   4. _indexation_: inserts the _chunks_ and their vectors into the _vector store_

![](../../static/img/collections_003.png)

You can view the imported documents in a collection using the `GET /v1/documents/{collection}` endpoint by specifying the collection ID. Similarly, you can view a document’s _chunks_ using the `GET /v1/chunks/{collection}/{document}` endpoint by specifying the document ID.

**Specific Case for JSON**

The JSON format is suitable for bulk importing data into the Albert API. Unlike other file types, JSON will be decomposed by the API into multiple documents, each of which will then be converted into chunks. The JSON must follow a defined structure.

![](../../static/img/collections_004.png)

### Metadata

The JSON file must be structured as a list of documents:

```json
[{"text": "hello world", "title": "my document"}, ...]
```
You can add metadata to each imported document when using JSON format. Metadata is optional and is currently available only for JSON files.

To do this, specify it as follows:

```json
[{"text": "hello world", "title": "my document", "metadata": {"author": "me"}}, ...]}
```

This metadata will be returned along with the chunk associated with the document when performing a search with the POST /search endpoint.
### Chunking

The chunking strategy is configurable via parameters in the POST /v1/files endpoint. Several chunkers are available:

NoSplitter: the file is considered as a single chunk

LangchainRecursiveCharacterTextSplitter: see the [Langchain documentation](https://python.langchain.com/v0.1/docs/modules/data_connection/document_transformers/recursive_text_splitter/) for more details

The chunker parameters (size, separator, etc.) are passed as parameters to the POST /v1/files endpoint in the chunker_args parameter [the documentation](https://albert.api.etalab.gouv.fr/documentation#tag/Retrieval-Augmented-Generation/operation/upload_file_v1_files_post).
