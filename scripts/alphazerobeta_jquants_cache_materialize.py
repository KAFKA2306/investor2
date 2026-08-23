#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

MAGIC = b"JQHF1"
NONCE_BYTES = 12
KEY_DOMAIN = b"investor2-jquants-hf-cache-v1\x00"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize an encrypted private J-Quants Hugging Face snapshot for ephemeral use."
    )
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def derive_key(api_key: str) -> bytes:
    return hashlib.sha256(KEY_DOMAIN + api_key.encode("utf-8")).digest()


def decrypt_blob(payload: bytes, *, key: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not payload.startswith(MAGIC) or len(payload) <= len(MAGIC) + NONCE_BYTES:
        raise ValueError("invalid encrypted J-Quants cache blob")
    nonce_start = len(MAGIC)
    nonce_end = nonce_start + NONCE_BYTES
    nonce = payload[nonce_start:nonce_end]
    ciphertext = payload[nonce_end:]
    return AESGCM(key).decrypt(nonce, ciphertext, aad)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required to decrypt the cache")

    source = args.source_dir
    manifest_path = source / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing encrypted-cache manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    encryption = manifest.get("encryption", {})
    if encryption.get("algorithm") != "AES-256-GCM":
        raise ValueError("unsupported or missing cache encryption contract")
    if encryption.get("plaintext_raw_data_on_hf") is not False:
        raise ValueError("manifest does not prove plaintext raw data is absent from HF snapshot")

    output = args.output_dir
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    key = derive_key(api_key)

    for encrypted_path in sorted(source.rglob("*.enc")):
        relative_encrypted = encrypted_path.relative_to(source)
        relative_raw = Path(str(relative_encrypted)[: -len(".enc")])
        plaintext = decrypt_blob(
            encrypted_path.read_bytes(),
            key=key,
            aad=relative_raw.as_posix().encode("utf-8"),
        )
        destination = output / relative_raw
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(plaintext)

    expected = {item["path"]: item["sha256"] for item in manifest.get("files", [])}
    for relative, expected_sha in expected.items():
        path = output / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing decrypted cache file: {relative}")
        if sha256_file(path) != expected_sha:
            raise AssertionError(f"decrypted cache hash mismatch: {relative}")

    shutil.copy2(manifest_path, output / "manifest.json")
    print(
        json.dumps(
            {
                "materialized_files": len(expected),
                "source_snapshot": manifest.get("snapshot_id"),
                "hash_verification": "passed",
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
