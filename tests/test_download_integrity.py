"""
Tests for size/hash checks, .part files and resuming downloads
"""

import asyncio
import hashlib
import pytest
from aiohttp import web

from src.downloader.file_downloader import FileDownloader, ProgressManager


CONTENT = bytes(range(256)) * 400  # 102400 bytes
SHA256 = hashlib.sha256(CONTENT).hexdigest().upper()
SERVER_NAME = "model_v1.safetensors"


@pytest.fixture
async def server(aiohttp_unused_port=None):
    """Local server that serves CONTENT with Range support and records requests"""
    requests = []
    state = {"truncate": False}

    async def handler(request):
        requests.append(dict(request.headers))
        body = CONTENT
        status = 200
        headers = {"Content-Disposition": f'attachment; filename="{SERVER_NAME}"'}
        range_header = request.headers.get("Range")
        if range_header:
            start = int(range_header.split("=")[1].split("-")[0])
            if start >= len(CONTENT):
                return web.Response(status=416)
            body = CONTENT[start:]
            status = 206
            headers["Content-Range"] = f"bytes {start}-{len(CONTENT) - 1}/{len(CONTENT)}"
        if state["truncate"]:
            # Promise the full length but stop early, like a dropped connection
            response = web.StreamResponse(status=status, headers=headers)
            response.content_length = len(body)
            await response.prepare(request)
            await response.write(body[: len(body) // 2])
            request.transport.close()
            return response
        return web.Response(body=body, status=status, headers=headers)

    app = web.Application()
    app.router.add_get("/file", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    yield {"url": f"http://127.0.0.1:{port}/file", "requests": requests, "state": state}
    await runner.cleanup()


async def download(url, path, expected=None, **settings):
    download_settings = {"max_concurrent_downloads": 1, "timeout": 5, "retry_attempts": 1,
                         "skip_existing_files": True, **settings}
    async with FileDownloader(None, download_settings) as downloader:
        return await downloader.download_file(
            url, path, asyncio.Semaphore(1), ProgressManager(1), expected=expected
        )


@pytest.mark.asyncio
async def test_fresh_download_leaves_no_part_file(server, tmp_path):
    ok, message = await download(server["url"], tmp_path / "x.safetensors", {"size": len(CONTENT)})

    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.asyncio
async def test_complete_file_skipped_without_request(server, tmp_path):
    (tmp_path / SERVER_NAME).write_bytes(CONTENT)

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)})

    assert ok and "Skipped" in message
    assert server["requests"] == []


@pytest.mark.asyncio
async def test_truncated_file_is_redownloaded(server, tmp_path):
    (tmp_path / SERVER_NAME).write_bytes(CONTENT[:1000])

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)})

    assert ok and "Downloaded" in message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT


@pytest.mark.asyncio
async def test_size_checked_against_content_length_when_unknown(server, tmp_path):
    # Existing file under the server's name, no expected size from CivitAI (e.g. CSV downloads)
    (tmp_path / SERVER_NAME).write_bytes(CONTENT[:1000])

    ok, message = await download(server["url"], tmp_path / "from-csv.safetensors")

    assert ok and "Downloaded" in message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT

    ok, message = await download(server["url"], tmp_path / "from-csv.safetensors")
    assert ok and "Skipped" in message


@pytest.mark.asyncio
async def test_partial_download_is_resumed(server, tmp_path):
    (tmp_path / f"{SERVER_NAME}.part").write_bytes(CONTENT[:40000])

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)})

    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT
    assert server["requests"][-1].get("Range") == "bytes=40000-"


@pytest.mark.asyncio
async def test_interrupted_download_is_not_treated_as_complete(server, tmp_path):
    server["state"]["truncate"] = True

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)})

    assert not ok
    assert not (tmp_path / SERVER_NAME).exists()
    assert (tmp_path / f"{SERVER_NAME}.part").exists()

    # Next run picks up where it stopped
    server["state"]["truncate"] = False
    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)})
    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT


@pytest.mark.asyncio
async def test_hash_mismatch_fails_with_verify(server, tmp_path):
    ok, message = await download(server["url"], tmp_path / SERVER_NAME,
                                 {"size": len(CONTENT), "sha256": "0" * 64}, verify_hash=True)

    assert not ok
    assert "SHA256" in message
    assert not (tmp_path / SERVER_NAME).exists()


@pytest.mark.asyncio
async def test_existing_file_with_wrong_hash_redownloaded_with_verify(server, tmp_path):
    corrupt = bytearray(CONTENT)
    corrupt[0] ^= 0xFF
    (tmp_path / SERVER_NAME).write_bytes(bytes(corrupt))

    ok, message = await download(server["url"], tmp_path / SERVER_NAME,
                                 {"size": len(CONTENT), "sha256": SHA256}, verify_hash=True)

    assert ok and "Downloaded" in message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT


@pytest.mark.parametrize("header, expected", [
    ('attachment; filename="model.safetensors"', "model.safetensors"),
    ("attachment; filename=model.safetensors", "model.safetensors"),
    ('attachment; filename="../../evil.safetensors"', "evil.safetensors"),
    ("attachment; filename*=UTF-8''my%20model.safetensors", "my model.safetensors"),
    ("inline", None),
])
def test_filename_from_content_disposition(header, expected):
    assert FileDownloader.filename_from_content_disposition(header) == expected
