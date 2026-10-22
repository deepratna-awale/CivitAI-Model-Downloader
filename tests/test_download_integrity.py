"""
Tests for size/hash checks, .part files and resuming downloads
"""

import asyncio
import hashlib
import shutil
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
    state = {"truncate": False, "chunk_limit": None}

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
        if state["chunk_limit"]:
            # Drop the connection after a few bytes on every request, like a flaky network
            response = web.StreamResponse(status=status, headers=headers)
            response.content_length = len(body)
            await response.prepare(request)
            await response.write(body[: state["chunk_limit"]])
            await asyncio.sleep(0.1)  # Let the client read it before the connection drops
            request.transport.close()
            return response
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


ENGINES = [
    pytest.param(False, id="aiohttp"),
    pytest.param(True, id="aria2", marks=pytest.mark.skipif(not shutil.which("aria2c"), reason="aria2c not installed")),
]


@pytest.fixture(params=ENGINES)
def engine(request):
    return request.param


async def download(url, path, expected=None, use_aria2=False, **settings):
    download_settings = {"max_concurrent_downloads": 1, "timeout": 5, "read_timeout": 5, "retry_attempts": 1,
                         "skip_existing_files": True, "use_aria2": use_aria2,
                         "aria2_args": ["--retry-wait=0", "--max-tries=1"], **settings}
    async with FileDownloader(None, download_settings) as downloader:
        return await downloader.download_file(
            url, path, asyncio.Semaphore(1), ProgressManager(1), expected=expected
        )


@pytest.mark.asyncio
async def test_fresh_download_leaves_no_part_file(server, tmp_path, engine):
    # With metadata, the expected name is CivitAI's file name, which the server also sends
    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)}, use_aria2=engine)

    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.asyncio
async def test_complete_file_skipped_without_request(server, tmp_path, engine):
    (tmp_path / SERVER_NAME).write_bytes(CONTENT)

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)}, use_aria2=engine)

    assert ok and "Skipped" in message
    assert server["requests"] == []


@pytest.mark.asyncio
async def test_truncated_file_is_redownloaded(server, tmp_path, engine):
    (tmp_path / SERVER_NAME).write_bytes(CONTENT[:1000])

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)}, use_aria2=engine)

    assert ok and "Downloaded" in message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT


@pytest.mark.asyncio
async def test_size_checked_against_content_length_when_unknown(server, tmp_path, engine):
    # Existing file under the server's name, no expected size from CivitAI (e.g. CSV downloads)
    (tmp_path / SERVER_NAME).write_bytes(CONTENT[:1000])

    ok, message = await download(server["url"], tmp_path / "from-csv.safetensors", use_aria2=engine)

    assert ok and "Downloaded" in message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT

    ok, message = await download(server["url"], tmp_path / "from-csv.safetensors", use_aria2=engine)
    assert ok
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT
    if not engine:
        # aria2c confirms the file with the server instead of reporting a skip
        assert "Skipped" in message


@pytest.mark.asyncio
async def test_partial_download_is_resumed(server, tmp_path, engine):
    (tmp_path / f"{SERVER_NAME}.part").write_bytes(CONTENT[:40000])

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)}, use_aria2=engine)

    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT
    # Only the rest is fetched (aria2c resumes from its last full block)
    range_starts = [int(h["Range"].split("=")[1].split("-")[0]) for h in server["requests"] if "Range" in h]
    assert range_starts and 0 < min(range_starts) <= 40000


@pytest.mark.asyncio
async def test_interrupted_download_is_not_treated_as_complete(server, tmp_path, engine):
    server["state"]["truncate"] = True

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)}, use_aria2=engine)

    assert not ok
    # The unfinished download is marked as such: our .part file, or aria2's control file
    final = tmp_path / SERVER_NAME
    assert (not final.exists() and (tmp_path / f"{SERVER_NAME}.part").exists()) or \
        (tmp_path / f"{SERVER_NAME}.aria2").exists()

    # Next run picks up where it stopped
    server["state"]["truncate"] = False
    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)}, use_aria2=engine)
    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT


@pytest.mark.asyncio
async def test_hash_mismatch_fails_with_verify(server, tmp_path, engine):
    ok, message = await download(server["url"], tmp_path / SERVER_NAME,
                                 {"size": len(CONTENT), "sha256": "0" * 64}, use_aria2=engine, verify_hash=True)

    assert not ok
    assert "SHA256" in message
    assert not (tmp_path / SERVER_NAME).exists()


@pytest.mark.asyncio
async def test_existing_file_with_wrong_hash_redownloaded_with_verify(server, tmp_path, engine):
    corrupt = bytearray(CONTENT)
    corrupt[0] ^= 0xFF
    (tmp_path / SERVER_NAME).write_bytes(bytes(corrupt))

    ok, message = await download(server["url"], tmp_path / SERVER_NAME,
                                 {"size": len(CONTENT), "sha256": SHA256}, use_aria2=engine, verify_hash=True)

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


@pytest.mark.asyncio
async def test_keeps_retrying_while_making_progress(server, tmp_path):
    # Every connection drops after 30000 bytes; with retry_attempts=1 the download
    # still finishes because each attempt resumes and makes progress
    server["state"]["chunk_limit"] = 30000

    ok, message = await download(server["url"], tmp_path / SERVER_NAME, {"size": len(CONTENT)})

    assert ok, message
    assert (tmp_path / SERVER_NAME).read_bytes() == CONTENT
    assert [h.get("Range") for h in server["requests"]] == [
        None, "bytes=30000-", "bytes=60000-", "bytes=90000-"
    ]


@pytest.mark.asyncio
async def test_gives_up_when_no_progress(server, tmp_path):
    server["state"]["chunk_limit"] = 30000
    (tmp_path / f"{SERVER_NAME}.part").write_bytes(CONTENT[:1000])
    server["state"]["chunk_limit"] = None
    server["state"]["truncate"] = True

    # A server that sends nothing useful: each attempt adds no bytes
    async def no_progress(*args, **kwargs):
        raise IOError("connection reset")

    async with FileDownloader(None, {"retry_attempts": 2, "use_aria2": False, "timeout": 5}) as downloader:
        downloader._write_body = no_progress
        ok, message = await downloader.download_file(
            server["url"], tmp_path / SERVER_NAME, asyncio.Semaphore(1), ProgressManager(1),
            expected={"size": len(CONTENT)}
        )

    assert not ok
    assert "connection reset" in message
    assert len(server["requests"]) == 2
