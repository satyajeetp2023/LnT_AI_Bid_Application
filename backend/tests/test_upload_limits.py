import asyncio
import io

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.routes import read_limited_upload


def test_chunked_upload_reader_returns_content_within_limits():
    upload=UploadFile(filename="small.txt",file=io.BytesIO(b"abcdef"))
    data,size=asyncio.run(read_limited_upload(upload,file_limit=10,batch_remaining=20,chunk_size=2))
    assert data==b"abcdef"
    assert size==6


def test_chunked_upload_reader_rejects_file_during_read_when_limit_crossed():
    upload=UploadFile(filename="large.txt",file=io.BytesIO(b"abcdefghij"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_limited_upload(upload,file_limit=5,batch_remaining=20,chunk_size=2))
    assert exc.value.status_code==413
    assert "File exceeds" in exc.value.detail


def test_chunked_upload_reader_rejects_batch_remaining_limit():
    upload=UploadFile(filename="batch.txt",file=io.BytesIO(b"abcdef"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_limited_upload(upload,file_limit=10,batch_remaining=4,chunk_size=2))
    assert exc.value.status_code==413
    assert "Batch exceeds" in exc.value.detail
