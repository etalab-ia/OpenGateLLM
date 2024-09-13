import base64
import uuid
from typing import List, Optional, Union

from fastapi import APIRouter, Response, Security, UploadFile, HTTPException
from botocore.exceptions import ClientError
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import Filter, FieldCondition, MatchAny

from app.schemas.files import File, Files, Upload, Uploads
from app.schemas.config import PRIVATE_COLLECTION_TYPE
from app.utils.config import LOGGER
from app.utils.security import check_api_key
from app.utils.data import get_chunks, get_collection_id, delete_contents, create_collection
from app.utils.lifespan import clients
from app.helpers import S3FileLoader


router = APIRouter()


@router.post("/files")
async def upload_files(
    collection: str,
    embeddings_model: str,
    files: List[UploadFile],
    chunk_size: Optional[int] = 512,
    chunk_overlap: Optional[int] = 0,
    chunk_min_size: Optional[int] = None,
    user: str = Security(check_api_key),
) -> Uploads:
    """
    Upload multiple files to be processed, chunked, and stored into a vector database. Supported file types : docx, pdf, json.

    **Parameters**:
    - **collection** (string): The collection name where the files will be stored.
    - **embeddings_model** (string): The embedding model to use for creating vectors. A collection must have only one embedding model.
    - **chunk_size** (int): The maximum number of characters of each text chunk.
    - **chunk_overlap** (int): The number of characters overlapping between chunks.
    - **chunk_min_size** (int): The minimum number of characters of a chunk to be considered valid.

    Supported files types:
    - **docx**: Microsoft Word file.
    - **pdf**: Portable Document Format file.
    - **json**: JavaScript Object Notation file.
        For JSON, file structure like: {"documents": [{"text": "hello world", "metadata": {"title": "my document"}}, ...]} or {"documents": [{"text": "hello world"}, ...]}
        Each document must have a "text" key and "metadata" key (optional) with dict type value.

    **Request body**
    - **files** : Files to upload.
    """

    # if collection already exists, return collection ID too
    collection_id = create_collection(
        collection=collection,
        vectorstore=clients["vectors"],
        embeddings_model=embeddings_model,
        user=user,
    )

    # upload
    data = list()
    loader = S3FileLoader(
        s3=clients["files"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_min_size=chunk_min_size,
    )

    try:
        clients["files"].head_bucket(Bucket=collection_id)
    except ClientError:
        clients["files"].create_bucket(Bucket=collection_id)

    for file in files:
        file_id = str(uuid.uuid4())
        file_name = file.filename.strip()
        encoded_file_name = base64.b64encode(file_name.encode("utf-8")).decode("ascii")
        try:
            # upload files into S3 bucket
            clients["files"].upload_fileobj(
                file.file,
                collection_id,
                file_id,
                ExtraArgs={
                    "ContentType": file.content_type,
                    "Metadata": {
                        "filename": encoded_file_name,
                        "id": file_id,
                    },
                },
            )
        except Exception as e:
            LOGGER.error(f"store {file_name}:\n{e}")
            data.append(Upload(id=file_id, filename=file_name, status="failed"))
            continue

        try:
            # convert files into langchain documents
            documents = loader._get_elements(
                file_id=file_id,
                bucket=collection_id,
            )
        except Exception as e:
            LOGGER.error(f"convert {file_name} into documents:\n{e}")
            clients["files"].delete_object(Bucket=collection_id, Key=file_id)
            data.append(Upload(id=file_id, filename=file_name, status="failed"))
            continue

        try:
            # create vectors from documents
            db = await QdrantVectorStore.afrom_documents(
                documents=documents,
                embedding=clients["models"][embeddings_model].embedding,
                collection_name=collection_id,
                url=clients["vectors"].url,
                api_key=clients["vectors"].api_key,
            )
        except Exception as e:
            LOGGER.error(f"create vectors of {file_name}:\n{e}")
            clients["files"].delete_object(Bucket=collection_id, Key=file_id)
            data.append(Upload(id=file_id, filename=file_name, status="failed"))
            continue

        data.append(Upload(id=file_id, filename=file_name, status="success"))

    return Uploads(data=data)


@router.get("/files/{collection}/{file}")
@router.get("/files/{collection}")
async def files(
    collection: str,
    file: Optional[str] = None,
    user: str = Security(check_api_key),
) -> Union[File, Files]:
    """
    Get files from a collection. Only files from private collections are returned.
    """

    collection_id = get_collection_id(
        vectorstore=clients["vectors"],
        collection=collection,
        user=user,
        type=PRIVATE_COLLECTION_TYPE,
    )

    data = list()
    objects = clients["files"].list_objects_v2(Bucket=collection_id).get("Contents", [])
    objects = [object | clients["files"].head_object(Bucket=collection_id, Key=object["Key"])["Metadata"] for object in objects]  # fmt: off
    file_ids = [object["Key"] for object in objects]
    filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=file_ids))])
    chunks = get_chunks(vectorstore=clients["vectors"], collection=collection, filter=filter, user=user)

    for object in objects:
        chunk_ids = list()
        for chunk in chunks:
            if chunk.metadata["file_id"] == object["Key"]:
                chunk_ids.append(chunk.id)

        object = File(
            id=object["Key"],
            object="file",
            bytes=object["Size"],
            filename=base64.b64decode(object["filename"].encode("ascii")).decode("utf-8"),
            chunk_ids=chunk_ids,
            created_at=round(object["LastModified"].timestamp()),
        )
        data.append(object)

        if str(object.id) == file:
            return object

    LOGGER.debug(f"files: {data}")
    if file:  # if loop pass without return data
        raise HTTPException(status_code=404, detail="File not found.")

    return Files(data=data)


@router.delete("/files/{collection}/{file}")
@router.delete("/files/{collection}")
async def delete_file(
    collection: str, file: Optional[str] = None, user: str = Security(check_api_key)
) -> Response:
    """
    Delete files and relative collections. Only files from private collections can be deleted.
    """

    response = delete_contents(
        s3=clients["files"],
        vectorstore=clients["vectors"],
        user=user,
        collection=collection,
        file=file,
    )

    return response
