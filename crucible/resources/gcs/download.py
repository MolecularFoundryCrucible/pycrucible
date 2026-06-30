#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCS download helpers for Crucible datasets.

Standalone functions — take an explicit `client` argument so they can be
tested in isolation and reused outside of any resource class.
"""

import fnmatch
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def bare_name(file_record: Dict, dsid: str) -> str:
    """Extract the display filename from a file record.

    Strips the GCS bucket and dataset prefix from storage_path when present,
    falls back to the filename field.
    """
    sp     = file_record.get('storage_path') or ''
    prefix = f'mf-storage-prod/{dsid}/'
    if sp.startswith(prefix):
        return sp[len(prefix):]
    if sp:
        return os.path.basename(sp)
    return os.path.basename(file_record.get('filename') or '')


def download_dataset_files(client, dsid: str, output_dir: str,
                           link_map: Dict[str, str],
                           all_files: List[Dict],
                           overwrite_existing: bool = True,
                           include: Optional[List[str]] = None,
                           exclude: Optional[List[str]] = None,
                           max_workers: int = 4) -> List[str]:
    """Download ingested files for a dataset into output_dir.

    Args:
        client:            CrucibleClient instance.
        dsid:              Dataset unique identifier.
        output_dir:        Local directory to write files into.
        link_map:          {mfid: signed_url} from get_download_links().
        all_files:         List of file records from list_files(dsid).
        overwrite_existing: Overwrite existing local files (default True).
        include:           Glob patterns — only download matching filenames.
        exclude:           Glob patterns — skip matching filenames.
        max_workers:       Concurrent download threads (default 4).

    Returns:
        List[str]: Paths of all downloaded files.
    """
    # Build (file_record, name, signed_url) candidates using mfid as key
    candidates = []
    for f in all_files:
        name = bare_name(f, dsid)
        if not name:
            continue
        url = link_map.get(f.get('mfid', ''))
        if url:
            candidates.append((f, name, url))

    if include:
        candidates = [(f, n, u) for f, n, u in candidates
                      if any(fnmatch.fnmatch(n, p) for p in include)]
    if exclude:
        candidates = [(f, n, u) for f, n, u in candidates
                      if not any(fnmatch.fnmatch(n, p) for p in exclude)]

    if not candidates:
        return []

    def _download_one(args):
        _, name, signed_url = args
        download_path = os.path.join(output_dir, name)

        if not overwrite_existing and os.path.exists(download_path):
            return download_path

        dest_dir = os.path.dirname(download_path) or output_dir
        os.makedirs(dest_dir, exist_ok=True)

        response = client._session.get(signed_url, stream=True)
        response.raise_for_status()

        tmp_fd, tmp_path = tempfile.mkstemp(dir=dest_dir)
        try:
            with os.fdopen(tmp_fd, 'wb') as fh:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    fh.write(chunk)
            os.replace(tmp_path, download_path)
        except Exception:
            os.unlink(tmp_path)
            raise

        logger.debug(f"Downloaded {name}")
        return download_path

    downloads = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_download_one, c): c[1] for c in candidates}
        for future in as_completed(futures):
            name = futures[future]
            try:
                downloads.append(future.result())
            except Exception as e:
                logger.error(f"Failed to download {name}: {e}")

    return sorted(downloads)
