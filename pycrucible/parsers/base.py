#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 17:45:48 2026

@author: roncofaber
"""

from pycrucible import BaseDataset

#%%

class BaseParser:

    _measurement = "base"

    def __init__(self, files_to_upload=None, project_id=None,
                 metadata=None, keywords=None, mfid=None,
                 measurement=None, owner_orcid=None, dataset_name=None):
        """
        Initialize the parser with dataset properties.

        Args:
            files_to_upload (list, optional): Files to upload
            project_id (str, optional): Crucible project ID
            metadata (dict, optional): Scientific metadata
            keywords (list, optional): Keywords for the dataset
            mfid (str, optional): Unique dataset identifier
            measurement (str, optional): Measurement type
            owner_orcid (str, optional): Owner's ORCID ID
            dataset_name (str, optional): Human-readable dataset name
        """
        # Use parser's default measurement if not provided
        if measurement is None:
            measurement = self._measurement

        # Dataset properties
        self.project_id      = project_id
        self.files_to_upload = files_to_upload or []
        self.mfid            = mfid
        self.measurement     = measurement
        self.owner_orcid     = owner_orcid
        self.dataset_name    = dataset_name

        # initialize with user-provided metadata/keywords
        self.scientific_metadata = metadata or {}
        self.keywords = keywords or []
        self._client = None

        return

    def add_metadata(self, metadata_dict):
        """
        Merge additional metadata into parser's metadata.

        Args:
            metadata_dict (dict): Metadata to merge. Updates existing values.
        """
        if self.scientific_metadata is None:
            self.scientific_metadata = {}
        self.scientific_metadata.update(metadata_dict)

    def add_keywords(self, keywords_list):
        """
        Add unique keywords to parser's keyword list.

        Args:
            keywords_list (list): Keywords to add. Duplicates are ignored.
        """
        if self.keywords is None:
            self.keywords = []
        existing = set(self.keywords)
        for kw in keywords_list:
            if kw not in existing:
                self.keywords.append(kw)
                existing.add(kw)

    @property
    def client(self):
        """Get or create CrucibleClient instance."""
        if self._client is None:
            from pycrucible.config import get_client
            self._client = get_client()
        return self._client

    def to_dataset(self):
        """
        Convert parser data to a Crucible dataset object.

        Uses instance variables for all dataset properties.

        Returns:
            BaseDataset: Crucible dataset object
        """
        # Use the first file from files_to_upload as the main file
        file_to_upload = self.files_to_upload[0] if self.files_to_upload else None

        crucible_dataset = BaseDataset(
            unique_id    = self.mfid,
            measurement  = self.measurement,
            project_id   = self.project_id,
            owner_orcid  = self.owner_orcid,
            dataset_name = self.dataset_name,
            file_to_upload = file_to_upload
            )

        # Store scientific_metadata for external use
        # (Note: BaseDataset doesn't have a scientific_metadata field,
        # it's added separately via the API after dataset creation)
        crucible_dataset._scientific_metadata = self.scientific_metadata
        crucible_dataset._keywords = self.keywords

        return crucible_dataset
    
    def upload_dataset(self, ingestor='ApiUploadIngestor',
                       verbose=False, wait_for_ingestion_response=True):
        """
        Upload the parsed dataset to Crucible.

        Uses instance variables for all dataset properties (mfid, measurement,
        project_id, owner_orcid, dataset_name, metadata, keywords).

        Args:
            ingestor (str, optional): Ingestion class to use. Defaults to 'ApiUploadIngestor'
            verbose (bool, optional): Print detailed progress. Defaults to False.
            wait_for_ingestion_response (bool, optional): Wait for ingestion to complete. Defaults to True.

        Returns:
            dict: Dictionary containing 'created_record', 'scientific_metadata_record',
                  'ingestion_request', and 'uploaded_files'
        """
        # Create dataset object from instance variables
        dataset = self.to_dataset()

        # Upload to Crucible
        result = self.client.create_new_dataset_from_files(
            dataset,
            files_to_upload=self.files_to_upload,
            scientific_metadata=self.scientific_metadata,
            keywords=self.keywords,
            get_user_info_function=self.client.get_user,
            ingestor=ingestor,
            verbose=verbose,
            wait_for_ingestion_response=wait_for_ingestion_response
        )

        return result