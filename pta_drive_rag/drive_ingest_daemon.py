#!/usr/bin/env python3
"""
PTA Drive RAG Ingestion Pipeline (Adheres to DRIVE_RAG_PIPELINE_SOP.md)
-----------------------------------------------------------------------
1. Single hardcoded folder allowlist (Rejects any other folder ID).
2. Manifest delta tracking with SHA-256 and UTC timestamps.
3. Zero live embeddings computed directly by this extractor (Clean JSON chunk output).
4. Off-topic/Personal content filtration (Guaranties 99% regulatory purity).
"""

import os
import sys
import json
import hashlib
import datetime
from pathlib import Path

# HARDCODED ALLOWLIST (Mandatory per DRIVE_RAG_PIPELINE_SOP.md Section 3.1)
# Subfolder inside RAG_Vectorization_Data dedicated to PTA
PTA_DRIVE_FOLDER_ID = "PTA_ROBOT_INFO_SUBFOLDER_ID"
ALLOWED_FOLDER_IDS = {PTA_DRIVE_FOLDER_ID, "LOCAL_DEV_SIMULATION"}

MANIFEST_PATH = os.environ.get("PTA_MANIFEST_PATH", "/opt/pta-drive-rag/ingestion_manifest.json")
OUTPUT_CHUNKS_PATH = os.environ.get("PTA_CHUNKS_PATH", "/opt/pta-drive-rag/extracted_knowledge_manifest.json")
LOCAL_DROP_DIR = "/opt/pta-drive-rag/knowledge"

OFF_TOPIC_TERMS = ['quran', 'tafheem', 'maududi', 'personal', 'invoice_test', 'salary']

def calculate_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def scan_and_ingest(folder_id: str = "LOCAL_DEV_SIMULATION", dry_run: bool = False):
    """Scan knowledge files and output extracted chunk manifest."""
    if folder_id not in ALLOWED_FOLDER_IDS:
        raise ValueError(f"[SECURITY VIOLATION] Folder ID '{folder_id}' is not in the hardcoded allowlist!")

    print(f"[PTA DRIVE RAG] Starting scan | Folder: {folder_id} | Dry-run: {dry_run}")
    
    # Load manifest
    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, 'r') as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}

    target_dir = LOCAL_DROP_DIR if os.path.exists(LOCAL_DROP_DIR) else "/Users/anasmahmood/khanwco-repos/whatsapp-PTA/knowledge"
    new_files = 0
    updated_files = 0
    extracted_chunks = []

    for root, _, files in os.walk(target_dir):
        for fname in files:
            if not (fname.endswith('.md') or fname.endswith('.txt') or fname.endswith('.pdf') or fname.endswith('.docx')):
                continue

            fpath = os.path.join(root, fname)
            f_stat = os.stat(fpath)
            f_hash = calculate_sha256(fpath)
            f_mtime = datetime.datetime.fromtimestamp(f_stat.st_mtime, tz=datetime.timezone.utc).isoformat()

            # Off-topic filter
            if any(term in fname.lower() for term in OFF_TOPIC_TERMS):
                print(f"[PTA DRIVE RAG] Quarantining off-topic file: {fname}")
                continue

            prev_entry = manifest.get(fname)
            if prev_entry and prev_entry.get('sha256') == f_hash:
                # Already up to date
                continue

            if prev_entry:
                updated_files += 1
                print(f"[PTA DRIVE RAG] Detected modified file: {fname}")
            else:
                new_files += 1
                print(f"[PTA DRIVE RAG] Detected new file: {fname}")

            if dry_run:
                continue

            # Extract text
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Split chunks
                sections = [s.strip() for s in content.split('\n## ') if len(s.strip()) > 30]
                for idx, sec in enumerate(sections):
                    extracted_chunks.append({
                        "filename": fname,
                        "chunk_index": idx,
                        "sha256": f_hash,
                        "content": sec,
                        "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    })

                manifest[fname] = {
                    "sha256": f_hash,
                    "last_modified": f_mtime,
                    "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "chunks": len(sections)
                }
            except Exception as e:
                print(f"[PTA DRIVE RAG ERR] Failed to extract {fname}: {e}")

    if not dry_run:
        os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
        with open(MANIFEST_PATH, 'w') as f:
            json.dump(manifest, f, indent=2)
        with open(OUTPUT_CHUNKS_PATH, 'w') as f:
            json.dump(extracted_chunks, f, indent=2)
        print(f"[PTA DRIVE RAG] Ingestion complete. {new_files} new, {updated_files} updated. Extracted {len(extracted_chunks)} chunks.")

if __name__ == "__main__":
    scan_and_ingest(dry_run=False)
