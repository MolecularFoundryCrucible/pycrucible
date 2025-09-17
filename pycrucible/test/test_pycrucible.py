"""
Tests for the basic functionality of the pycrucible dataset download function.
"""

import pytest

import os
from pathlib import Path
import tempfile

from pycrucible import CrucibleClient, SecureInput

API_URL = "https://crucible.lbl.gov/testapi"
API_KEY = os.environ.get("CRUCIBLE_API_KEY")
dataset0 = '0swk4bk8exsjh000nzvhp6hj28'

class Test:
    """
    Test pycrucible
    """

    def test_api_key(self):
        print(os.environ.get("CRUCIBLE_API_KEY"))
        
    
    def test_download(self):
        """specific filename"""
       # Initialize the client
        print(API_KEY)
        client = CrucibleClient(API_URL, API_KEY)

        response = client.download_dataset(dataset0)
        assert Path('./crucible-downloads/09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser').exists()
        Path('./crucible-downloads/09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser').unlink()
        Path('./crucible-downloads/').rmdir()
        
    def test_download_filename(self):
        """specific filename"""
       # Initialize the client
        client = CrucibleClient(API_URL, API_KEY)
        response = client.download_dataset(dataset0, 
                                           file_name='09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser')
        assert Path('./crucible-downloads/09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser').exists()
        Path('./crucible-downloads/09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser').unlink()
        Path('./crucible-downloads/').rmdir()
        
    def test_download_dataset_filename_dir(self, tmp_path):
        """specific filename with directory path"""
        client = CrucibleClient(API_URL, API_KEY)
        response = client.download_dataset(dataset0, 
                                           file_name='09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser', 
                                           output_path=str(tmp_path)
                                          )
        assert (tmp_path / Path('09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser')).exists()
        
    def test_download_dataset_filename_file(self, tmp_path):
        """specific filename with file path"""
        client = CrucibleClient(API_URL, API_KEY)
        output_path = tmp_path / Path('temp.ser')
        response = client.download_dataset(dataset0, 
                                           file_name='09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser', 
                                           output_path=output_path
                                          )
        assert output_path.exists()
    
    def test_download_dataset_outputdir(self, tmp_path):
        """specific filename with directory path"""
        client = CrucibleClient(API_URL, API_KEY)
        response = client.download_dataset(dataset0,
                                           output_path=str(tmp_path)
                                          )
        assert (tmp_path / Path('09.28.46 Scanning Acquire_s-14o_34.7pm_12us_1.ser')).exists()
        
    def test_download_dataset_outputfile(self, tmp_path):
        """specific filename with file path"""
        client = CrucibleClient(API_URL, API_KEY)
        output_path = tmp_path / Path('temp.ser')
        response = client.download_dataset(dataset0,
                                           output_path=output_path
                                          )
        assert output_path.exists()