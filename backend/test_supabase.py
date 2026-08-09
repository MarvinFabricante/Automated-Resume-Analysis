"""
Quick smoke-test for the Supabase Storage integration.

Run:  python test_supabase.py
"""

import asyncio
import os
import sys

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()


async def main():
    from app.utils.supabase_storage import (
        upload_resume,
        download_resume,
        get_public_url,
        list_resumes,
        delete_resume,
    )

    print("=" * 60)
    print("  Supabase Storage Integration Test")
    print("=" * 60)

    # 1. Upload a test file
    test_content = b"This is a test resume file for Supabase integration."
    test_filename = "test_resume_supabase.txt"

    print("\n[1/5] Uploading test file...")
    result = await upload_resume(
        file_bytes=test_content,
        original_filename=test_filename,
        candidate_id=9999,
    )
    print(f"  ✅ Uploaded!")
    print(f"     Storage path: {result['storage_path']}")
    print(f"     Public URL:   {result['public_url']}")
    print(f"     Filename:     {result['filename']}")

    storage_path = result["storage_path"]

    # 2. Get public URL
    print("\n[2/5] Getting public URL...")
    url = get_public_url(storage_path)
    print(f"  ✅ Public URL: {url}")

    # 3. Download the file
    print("\n[3/5] Downloading file...")
    downloaded = await download_resume(storage_path)
    assert downloaded == test_content, "Downloaded content does not match!"
    print(f"  ✅ Downloaded {len(downloaded)} bytes (content matches)")

    # 4. List files
    print("\n[4/5] Listing files in bucket...")
    files = await list_resumes("resumes/9999")
    print(f"  ✅ Found {len(files)} file(s) under resumes/9999:")
    for f in files:
        print(f"     - {f.get('name', 'unknown')}")

    # 5. Delete the test file
    print("\n[5/5] Deleting test file...")
    deleted = await delete_resume(storage_path)
    print(f"  ✅ Deleted: {deleted}")

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
