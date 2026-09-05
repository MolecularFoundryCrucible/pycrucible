#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Package-wide constants for the Crucible API client.
"""

DEFAULT_LIMIT = 100   # default page size for list requests
API_PAGE_MAX  = 1000  # server hard cap per request

PROJECT_MEMBER_ROLES = ('viewer', 'contributor', 'editor', 'admin')
PROJECT_SCOPES = ('assigned', 'shared', 'all')

# Multipart upload defaults (tuned via benchmarking — see testing/tune_results.jsonl)
UPLOAD_CHUNK_SIZE_MB = 64   # GCS XML multipart part size in MiB
UPLOAD_MAX_WORKERS   = 8    # concurrent upload threads

AVAILABLE_INGESTORS = [
    'ApiUploadIngestor',
    'AFMIngestor',
    'TitanXSessionIngestor',
    'Team05SessionIngestor',
    'SimpleTiledImageScopeFoundryH5Ingestor',
    'BioGlowIngestor',
    'QSpleemSVRampIngestor',
    'QSpleemImageIngestor',
    'QSpleemARRESEKIngestor',
    'QSpleemARRESMMIngestor',
    'CanonCaptureScopeFoundryH5Ingestor',
    'SingleSpecScopeFoundryH5Ingestor',
    'HyperspecScopeFoundryH5Ingestor',
    'HyperspecSweepScopeFoundryH5Ingestor',
    'ToupcamLiveScopeFoundryH5Ingestor',
    'CLSyncRasterScanIngestor',
    'CLHyperspecIngestor',
    'SpinbotSpecLineIngestor',
    'SpinbotCameraCaptureIngestor',
    'SpinbotPhotoRunIngestor',
    'InSituPlIngestor',
    'CziIngestor',
    'DigitalMicrographIngestor',
    'SerIngestor',
    'BcfIngestor',
    'EmdIngestor',
    'SpinbotSpecRunIngestor',
    'ImageIngestor'
]
