#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 17:22:34 2026

@author: roncofaber
"""

from .base import BaseParser

import os

#%%

def store_variable(varname, varvalue, vardict):
    vardict[varname] = varvalue
    return

class LAMMPSParser(BaseParser):
    
    _measurement = "LAMMPS"
    
    def __init__(self, input_file, project_id=None):
        """
        Main driver, reads input file and find other relevant files, then
        reads each one to extract metadata.
        """

        # find input file
        input_file = os.path.abspath(input_file)

        # start by reading input file
        lmp_metadata = self.read_lmp_input_file(input_file)

        # build list of files to upload (only input, data, and log files)
        files_to_upload = [input_file]

        # then read data file
        data_file = os.path.join(lmp_metadata["root"], lmp_metadata["data_file"])
        data_file_metadata = self.read_data_file(data_file)
        lmp_metadata.update(data_file_metadata)
        files_to_upload.append(data_file)

        # now read LOG file
        log_file = os.path.join(lmp_metadata["root"], lmp_metadata["log_files"][0])
        log_file_metadata = self.read_log_file(log_file)
        lmp_metadata.update(log_file_metadata)
        # files_to_upload.append(log_file)

        # Note: dump files are parsed but not uploaded by default
        # They are stored in scientific_metadata for reference

        # initialize parent class with all files
        super().__init__(files_to_upload=files_to_upload, project_id=project_id)

        # store values internally
        self.scientific_metadata = lmp_metadata

        # set keywords based on parsed data
        self.keywords = ["LAMMPS", "molecular dynamics"]
        # Add elements as keywords
        if "elements" in lmp_metadata:
            self.keywords.extend(lmp_metadata["elements"])

        return
    
    
    # main driver: reads input file and find relevant associated files
    @staticmethod
    def read_lmp_input_file(input_file):
        
        # initialize empty data
        data = {}
        vardict = {}
        
        # store path
        data["root"]  = os.path.dirname(input_file)
        data["input_file"] = os.path.basename(input_file)
        
        # initialize empty arrays
        data["dump_files"] = []
        data["log_files"]  = []
        
        with open(input_file, "r") as fin:
            
            for line in fin:
                
                if line.startswith("read_data"): # see dump section
                    data_file = line.split()[1]
                    data["data_file"] = data_file
                
                if line.startswith("variable"):
                    varname  = line.split()[1]
                    varvalue = line.split()[3]
                    store_variable(varname, varvalue, vardict)
                    
                if line.startswith("dump "): #those should end up into self.associated_files
                    dumpname = line.split()[5]
                    dumpname = dumpname.replace("$", "")
                    data["dump_files"].append(dumpname.format(**vardict))
                    
                if line.startswith("log "):
                    logname = line.split()[1]
                    logname = logname.replace("$", "")
                    data["log_files"].append(logname.format(**vardict))
                    
        # if no log specified use the standard one
        if not data["log_files"]:
            data["log_files"]  = ["log.lammps"]

        return data
    
    @staticmethod
    def read_data_file(data_file):
        
        try:
            import ase.io.lammpsdata
        except:
            raise ImportError("ASE needs to be installed for LMP ingestor to work!")
            
        data = {}

        ase_atoms = ase.io.lammpsdata.read_lammps_data(data_file)
        
        #TODO this should not stay like that --> should be a json
        # data["atoms"] = ase_atoms.todict()
        
        # store some info about the system to metadata
        data['elements'] = list(set(ase_atoms.get_chemical_symbols()))
        data['natoms']   = len(ase_atoms.get_chemical_symbols())
        data["volume"]   = ase_atoms.get_volume()

        # what else do we want from the data_file

        return data    

    @staticmethod
    def read_log_file(log_file):

        data = {}

        # just read the first
        with open(log_file) as f:
            first_line = f.readline()
            
        data["lammps_version"] = first_line.strip()

        return data
    
    def to_dataset(self, mfid=None, measurement=None, project_id=None,
                   owner_orcid=None, dataset_name=None):
        """
        Convert parsed data to Crucible dataset.

        Note: measurement parameter is ignored; uses self._measurement instead.
        """
        dst = super().to_dataset(
                                 mfid=mfid,
                                 measurement=self._measurement,
                                 project_id=project_id,
                                 owner_orcid=owner_orcid,
                                 dataset_name=dataset_name
                                 )

        return dst

    def upload_dataset(self, mfid=None, project_id=None, owner_orcid=None,
                       dataset_name=None, get_user_info_function=None,
                       ingestor='ApiUploadIngestor', verbose=False,
                       wait_for_ingestion_response=True):
        """
        Upload LAMMPS dataset to Crucible.

        Automatically sets measurement type to "LAMMPS".

        Args:
            mfid (str, optional): Unique dataset identifier
            project_id (str, optional): Project ID. Uses self.project_id if not provided.
            owner_orcid (str, optional): Owner's ORCID ID
            dataset_name (str, optional): Human-readable dataset name
            get_user_info_function (callable, optional): Function to get user info if needed
            ingestor (str, optional): Ingestion class. Defaults to 'ApiUploadIngestor'
            verbose (bool, optional): Print detailed progress. Defaults to False.
            wait_for_ingestion_response (bool, optional): Wait for ingestion. Defaults to True.

        Returns:
            dict: Dictionary containing upload results
        """
        return super().upload_dataset(
            mfid=mfid,
            measurement=self._measurement,
            project_id=project_id,
            owner_orcid=owner_orcid,
            dataset_name=dataset_name,
            get_user_info_function=get_user_info_function,
            ingestor=ingestor,
            verbose=verbose,
            wait_for_ingestion_response=wait_for_ingestion_response
        )
