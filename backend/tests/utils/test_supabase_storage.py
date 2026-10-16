import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.utils.supabase_storage as ss


def test_content_type():
    assert ss._content_type("resume.pdf") == "application/pdf"
    assert ss._content_type("doc.docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert ss._content_type("file.doc") == "application/msword"
    assert ss._content_type("notes.txt") == "text/plain"
    assert ss._content_type("photo.png") == "image/png"
    assert ss._content_type("avatar.jpg") == "image/jpeg"
    assert ss._content_type("avatar.jpeg") == "image/jpeg"
    assert ss._content_type("icon.webp") == "image/webp"
    assert ss._content_type("data.unknown") == "application/octet-stream"


def test_get_client_missing_env():
    with patch.object(ss, "_supabase_client", None):
        with patch.object(ss, "SUPABASE_URL", ""):
            with pytest.raises(RuntimeError) as exc_info:
                ss._get_client()
            assert "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY" in str(exc_info.value)


def test_get_client_success():
    mock_client = MagicMock()
    with patch.object(ss, "_supabase_client", None):
        with patch.object(ss, "SUPABASE_URL", "https://xyz.supabase.co"), \
             patch.object(ss, "SUPABASE_SERVICE_ROLE_KEY", "role_key_123"):
            with patch("supabase.create_client", return_value=mock_client) as mock_create:
                client = ss._get_client()
                assert client == mock_client
                mock_create.assert_called_once_with("https://xyz.supabase.co", "role_key_123")
                # Subsequent call uses singleton
                assert ss._get_client() == mock_client


@pytest.mark.asyncio
async def test_upload_resume_success():
    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage
    mock_storage.get_public_url.return_value = "https://supabase.co/resume.pdf"

    file_bytes = b"%PDF-1.4 test resume bytes"
    filename = "John Doe Resume.pdf"

    with patch.object(ss, "_get_client", return_value=mock_sb_client):
        with patch("app.utils.supabase_storage.set_cache", new_callable=AsyncMock) as mock_set_cache, \
             patch("app.utils.supabase_storage.clear_cache_pattern", new_callable=AsyncMock):

            # Candidate ID provided
            res = await ss.upload_resume(file_bytes, filename, candidate_id=42)
            assert "resumes/42/" in res["storage_path"]
            assert res["public_url"] == "https://supabase.co/resume.pdf"
            mock_storage.upload.assert_called_once()

            # Candidate ID None
            res_no_cand = await ss.upload_resume(file_bytes, filename, candidate_id=None)
            assert "resumes/" in res_no_cand["storage_path"]
            assert not res_no_cand["storage_path"].startswith("resumes/None/")


@pytest.mark.asyncio
async def test_upload_resume_failure():
    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage
    mock_storage.upload.side_effect = Exception("Supabase S3 error")

    with patch.object(ss, "_get_client", return_value=mock_sb_client):
        with pytest.raises(Exception) as exc_info:
            await ss.upload_resume(b"bytes", "err.pdf", candidate_id=1)
        assert "Supabase S3 error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download_resume_cache_hit():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = b"cached_resume_bytes"

    with patch("app.utils.supabase_storage.get_async_redis", return_value=mock_redis):
        data = await ss.download_resume("resumes/1/test.pdf")
        assert data == b"cached_resume_bytes"


@pytest.mark.asyncio
async def test_download_resume_cache_miss_and_error():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage
    mock_storage.download.return_value = b"downloaded_from_supabase"

    with patch("app.utils.supabase_storage.get_async_redis", return_value=mock_redis):
        with patch.object(ss, "_get_client", return_value=mock_sb_client):
            data = await ss.download_resume("resumes/2/cv.pdf")
            assert data == b"downloaded_from_supabase"
            mock_redis.setex.assert_awaited_once()

            # Error case
            mock_storage.download.side_effect = Exception("Not found")
            with pytest.raises(Exception):
                await ss.download_resume("resumes/2/cv.pdf")


def test_get_public_url():
    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage
    mock_storage.get_public_url.return_value = "https://supabase/public/url"

    with patch.object(ss, "_get_client", return_value=mock_sb_client):
        url = ss.get_public_url("resumes/path.pdf")
        assert url == "https://supabase/public/url"


@pytest.mark.asyncio
async def test_delete_resume():
    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage

    with patch.object(ss, "_get_client", return_value=mock_sb_client), \
         patch("app.utils.supabase_storage.delete_cache", new_callable=AsyncMock), \
         patch("app.utils.supabase_storage.clear_cache_pattern", new_callable=AsyncMock):

        # Success
        deleted = await ss.delete_resume("resumes/path.pdf")
        assert deleted is True
        mock_storage.remove.assert_called_once_with(["resumes/path.pdf"])

        # Error
        mock_storage.remove.side_effect = Exception("Delete failed")
        assert await ss.delete_resume("resumes/path.pdf") is False


@pytest.mark.asyncio
async def test_list_resumes():
    with patch("app.utils.supabase_storage.get_cache", new_callable=AsyncMock) as mock_get_cache, \
         patch("app.utils.supabase_storage.set_cache", new_callable=AsyncMock):

        # Cache hit
        mock_get_cache.return_value = [{"name": "file1.pdf"}]
        files = await ss.list_resumes("resumes/")
        assert files == [{"name": "file1.pdf"}]

        # Cache miss
        mock_get_cache.return_value = None
        mock_sb_client = MagicMock()
        mock_storage = MagicMock()
        mock_sb_client.storage.from_.return_value = mock_storage
        mock_storage.list.return_value = [{"name": "file2.pdf"}]

        with patch.object(ss, "_get_client", return_value=mock_sb_client):
            files2 = await ss.list_resumes("resumes/")
            assert files2 == [{"name": "file2.pdf"}]

            # Error case
            mock_storage.list.side_effect = Exception("List failed")
            assert await ss.list_resumes("resumes/") == []


@pytest.mark.asyncio
async def test_profile_image_operations():
    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage
    mock_storage.get_public_url.return_value = "https://supabase/profile.png"
    mock_storage.download.return_value = b"profile_bytes"

    with patch.object(ss, "_get_client", return_value=mock_sb_client), \
         patch("app.utils.supabase_storage.set_cache", new_callable=AsyncMock), \
         patch("app.utils.supabase_storage.get_cache", new_callable=AsyncMock) as mock_get_cache, \
         patch("app.utils.supabase_storage.delete_cache", new_callable=AsyncMock), \
         patch("app.utils.supabase_storage.clear_cache_pattern", new_callable=AsyncMock):

        # Upload async
        res = await ss.upload_profile_image(b"img", "avatar.png", user_role="candidate", user_id=12)
        assert res["public_url"] == "https://supabase/profile.png"
        assert "candidate_12_" in res["storage_path"]

        # Upload sync
        res_sync = ss.upload_profile_image_sync(b"img", "avatar.png", user_role="hr", user_id=5)
        assert res_sync["public_url"] == "https://supabase/profile.png"
        assert "hr_5_" in res_sync["storage_path"]

        # Public URL
        url = ss.get_profile_image_url("profiles/hr_5_avatar.png")
        assert url == "https://supabase/profile.png"

        # Download async (cache miss)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("app.utils.supabase_storage.get_async_redis", return_value=mock_redis):
            img_data = await ss.download_profile_image("profiles/img.png")
            assert img_data == b"profile_bytes"

        # Delete async
        del_ok = await ss.delete_profile_image("profiles/img.png")
        assert del_ok is True

        # List
        mock_get_cache.return_value = None
        mock_storage.list.return_value = [{"name": "avatar.png"}]
        files = await ss.list_profile_images()
        assert files == [{"name": "avatar.png"}]


@pytest.mark.asyncio
async def test_resume_image_operations():
    mock_sb_client = MagicMock()
    mock_storage = MagicMock()
    mock_sb_client.storage.from_.return_value = mock_storage
    mock_storage.get_public_url.return_value = "https://supabase/resume_img.png"
    mock_storage.download.return_value = b"resume_image_bytes"

    with patch.object(ss, "_get_client", return_value=mock_sb_client), \
         patch("app.utils.supabase_storage.set_cache", new_callable=AsyncMock), \
         patch("app.utils.supabase_storage.get_cache", new_callable=AsyncMock) as mock_get_cache, \
         patch("app.utils.supabase_storage.delete_cache", new_callable=AsyncMock), \
         patch("app.utils.supabase_storage.clear_cache_pattern", new_callable=AsyncMock):

        # Upload async
        res = await ss.upload_resume_image(b"r_img", "page1.png")
        assert res["public_url"] == "https://supabase/resume_img.png"

        # Upload sync
        res_sync = ss.upload_resume_image_sync(b"r_img", "page2.png")
        assert res_sync["public_url"] == "https://supabase/resume_img.png"

        # Public URL
        url = ss.get_resume_image_url("resumeimages/page1.png")
        assert url == "https://supabase/resume_img.png"

        # Download async (cache miss)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("app.utils.supabase_storage.get_async_redis", return_value=mock_redis):
            data = await ss.download_resume_image("resumeimages/page1.png")
            assert data == b"resume_image_bytes"

        # Delete async
        del_ok = await ss.delete_resume_image("resumeimages/page1.png")
        assert del_ok is True

        # List
        mock_get_cache.return_value = None
        mock_storage.list.return_value = [{"name": "page1.png"}]
        files = await ss.list_resume_images()
        assert files == [{"name": "page1.png"}]
