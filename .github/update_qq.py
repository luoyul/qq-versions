import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

PRIMARY_CONFIG = "https://qq-web.cdn-go.cn/im.qq.com_new/latest/rainbow/mobileConfig.json"
FALLBACK_CONFIG = "https://im.qq.com/proxy/domain/qq-web.cdn-go.cn/im.qq.com_new/latest/rainbow/mobileConfig.json"
SIGN_ENDPOINT = "https://im.qq.com/http2rpc/gotrpc/noauth/trpc.qqntv2.urlsign.UrlSign/GetSign"
PACKAGE = "com.tencent.mobileqq"
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "luoyul/qq-versions")
ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
CATALOG_PATH = ROOT / "catalog" / "qq.json"
CHECKSUM_PATH = ROOT / "checksums" / "QQ-SHA256SUMS.txt"


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "qq-versions-updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def get_signed_url(url):
    body = json.dumps({"url": url}).encode("utf-8")
    request = urllib.request.Request(
        SIGN_ENDPOINT,
        data=body,
        headers={
            "User-Agent": "qq-versions-updater",
            "Content-Type": "application/json",
            "x-oidb": json.dumps({"uint32_command": "0x9b8e", "uint32_service_type": 1}),
            "Origin": "https://im.qq.com",
            "Referer": "https://im.qq.com/",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        signed = ((result.get("data") or {}).get("url"))
        return signed or url
    except Exception:
        return url


def run(*args, check=True, capture=False):
    return subprocess.run(args, check=check, text=True, capture_output=capture)


def aapt_path():
    sdk_root = Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or "/opt/android-sdk")
    candidates = sorted(sdk_root.joinpath("build-tools").glob("*/aapt2"))
    if not candidates:
        raise RuntimeError("aapt2 was not found")
    return str(candidates[-1])


def read_badging(apk):
    output = run(aapt_path(), "dump", "badging", str(apk), capture=True).stdout
    match = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", output)
    if not match:
        raise RuntimeError("Unable to read APK package metadata")
    return match.group(1), match.group(2), match.group(3)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    cache_query = "?t=" + uuid.uuid4().hex
    try:
        config = fetch_json(PRIMARY_CONFIG + cache_query)
    except Exception:
        config = fetch_json(FALLBACK_CONFIG + cache_query)

    android = config.get("android") or {}
    version_name = str(android.get("version") or "")
    download_url = android.get("x64Link")
    if not version_name or not download_url:
        raise RuntimeError("Official config does not contain android.version or android.x64Link")

    filename_match = re.search(r"/(?:[^/]*?)(\d+\.\d+\.\d+)(?:\.|[_/-]|$)", download_url)
    if not filename_match or filename_match.group(1) != version_name:
        raise RuntimeError(f"Cannot extract versionName from official URL: {download_url}")
    file_name = f"QQ{version_name}.apk"

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8-sig"))
    versions = catalog.setdefault("versions", [])

    with tempfile.TemporaryDirectory() as temp_dir:
        apk = Path(temp_dir) / file_name
        signed_url = get_signed_url(download_url)
        cache_busted_url = signed_url if signed_url != download_url else download_url + ("&" if "?" in download_url else "?") + "t=" + uuid.uuid4().hex
        request = urllib.request.Request(cache_busted_url, headers={"User-Agent": "qq-versions-updater", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=120) as response, apk.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)

        package_name, actual_code, actual_name = read_badging(apk)
        if package_name != PACKAGE or actual_name != version_name:
            raise RuntimeError(f"APK metadata mismatch: {package_name} {actual_name} {actual_code}")

        version_code = actual_code
        release_tag = f"qq-{version_name}-{version_code}"
        if any(str(item.get("versionName")) == version_name and str(item.get("versionCode")) == version_code for item in versions):
            print(f"Already catalogued: {release_tag}")
            return

        digest = sha256(apk)
        size = apk.stat().st_size
        notes = f"Version: {version_name}\nVersion code: {version_code}\nPackage: {PACKAGE}\nSHA-256: {digest}\nSize: {size} bytes"
        release = subprocess.run(["gh", "release", "view", release_tag, "--repo", REPOSITORY], capture_output=True, text=True)
        if release.returncode == 0:
            run("gh", "release", "upload", release_tag, str(apk), "--repo", REPOSITORY, "--clobber")
            run("gh", "release", "edit", release_tag, "--repo", REPOSITORY, "--title", f"QQ {version_name} ({version_code})", "--notes", notes)
        else:
            run("gh", "release", "create", release_tag, str(apk), "--repo", REPOSITORY, "--title", f"QQ {version_name} ({version_code})", "--notes", notes)

    record = {
        "product": "qq",
        "packageName": PACKAGE,
        "versionName": version_name,
        "fileName": file_name,
        "size": size,
        "sha256": digest,
        "sourcePage": PRIMARY_CONFIG,
        "downloadedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "releaseTag": release_tag,
        "releaseUrl": f"https://github.com/{REPOSITORY}/releases/tag/{release_tag}",
        "versionCode": int(version_code),
    }
    versions[:] = [item for item in versions if item.get("releaseTag") != release_tag]
    versions.append(record)
    versions.sort(key=lambda item: (tuple(int(part) for part in str(item.get("versionName", "0")).split(".")), int(item.get("versionCode", 0))), reverse=True)
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = []
    if CHECKSUM_PATH.exists():
        lines = [line for line in CHECKSUM_PATH.read_text(encoding="utf-8-sig").splitlines() if file_name not in line]
    lines.append(f"{digest}  {file_name}")
    CHECKSUM_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"Published {release_tag}: {digest}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
