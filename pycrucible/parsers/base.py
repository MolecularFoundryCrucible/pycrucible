#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 17:45:48 2026

@author: roncofaber
"""

from pycrucible import BaseDataset

#%%

class BaseParser:

    def __init__(self, files_to_upload=None, project_id=None):

        # store info
        self.project_id      = project_id
        self.files_to_upload = files_to_upload or []

        # initialize variables
        self.scientific_metadata = {}
        self.keywords = []
        self._client = None

        return

    @property
    def client(self):
        """Get or create CrucibleClient instance."""
        if self._client is None:
            from pycrucible.config import get_client
            self._client = get_client()
        return self._client

    def to_dataset(self, mfid=None, measurement=None,
                   project_id=None, owner_orcid=None, dataset_name=None):

        if project_id is None:
            project_id = self.project_id

        # Use the first file from files_to_upload as the main file
        file_to_upload = self.files_to_upload[0] if self.files_to_upload else None

        crucible_dataset = BaseDataset(
            unique_id    = mfid,
            measurement  = measurement,
            project_id   = project_id,
            owner_orcid  = owner_orcid,
            dataset_name = dataset_name,
            file_to_upload = file_to_upload
            )

        # Store scientific_metadata for external use
        # (Note: BaseDataset doesn't have a scientific_metadata field,
        # it's added separately via the API after dataset creation)
        crucible_dataset._scientific_metadata = self.scientific_metadata
        crucible_dataset._keywords = self.keywords

        return crucible_dataset
    
    def upload_dataset(self, mfid=None, measurement=None, project_id=None,
                       owner_orcid=None, dataset_name=None,
                       get_user_info_function=None, ingestor='ApiUploadIngestor',
                       verbose=False, wait_for_ingestion_response=True):
        """
        Upload the parsed dataset to Crucible.

        Args:
            mfid (str, optional): Unique dataset identifier. If None, one will be generated.
            measurement (str, optional): Measurement type (e.g., "LAMMPS", "XRD")
            project_id (str, optional): Project ID. Uses self.project_id if not provided.
            owner_orcid (str, optional): Owner's ORCID ID
            dataset_name (str, optional): Human-readable dataset name
            get_user_info_function (callable, optional): Function to get user info if needed
            ingestor (str, optional): Ingestion class to use. Defaults to 'ApiUploadIngestor'
            verbose (bool, optional): Print detailed progress. Defaults to False.
            wait_for_ingestion_response (bool, optional): Wait for ingestion to complete. Defaults to True.

        Returns:
            dict: Dictionary containing 'created_record', 'scientific_metadata_record',
                  'ingestion_request', and 'uploaded_files'
        """
        # Create dataset object
        dataset = self.to_dataset(
            mfid=mfid,
            measurement=measurement,
            project_id=project_id,
            owner_orcid=owner_orcid,
            dataset_name=dataset_name
        )

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