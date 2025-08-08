import os
import requests
from typing import Optional, List, Dict, Union, Any
from .utils import get_tz_isoformat, run_shell, checkhash

class CrucibleClient:
    def __init__(self, api_url: str, api_key: str):
        """Initialize the Crucible API client.
        
        Args:
            api_url: Base URL for the Crucible API
            api_key: API key for authentication
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method (get, post, put, delete)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests
        
        Returns:
            Parsed JSON response
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        kwargs['headers'] = {**kwargs.get('headers', {}), **self.headers}
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def list_projects(self) -> List[Dict]:
        """List all accessible projects."""
        return self._request('get', '/projects')
    
    def get_project(self, project_id: str) -> Dict:
        """Get details of a specific project."""
        return self._request('get', f'/projects/{project_id}')
    
    def get_user(self, orcid: str) -> Dict:
        """Get user details by ORCID."""
        return self._request('get', f'/users/{orcid}')
    
    def get_user_by_email(self, email: str) -> Dict:
        """Get user details by email."""
        params = {"email": email}
        result = self._request('get', '/users', params=params)
        if not result:
            params = {"lbl_email": email}
            result = self._request('get', '/users', params=params)
        return result
    
    def get_project_users(self, project_id: str) -> List[Dict]:
        """Get users associated with a project."""
        return self._request('get', f'/projects/{project_id}/users')
    
    def list_datasets(self, **kwargs) -> List[Dict]:
        """List datasets with optional filtering."""
        return self._request('get', '/datasets', params=kwargs)
    
    def get_dataset(self, dsid: str, include_metadata: bool = False) -> Dict:
        """Get dataset details, optionally including scientific metadata."""
        dataset = self._request('get', f'/datasets/{dsid}')
        if dataset and include_metadata:
            try:
                metadata = self._request('get', f'/datasets/{dsid}/scientific_metadata')
                dataset['scientific_metadata'] = metadata or {}
            except requests.exceptions.RequestException:
                dataset['scientific_metadata'] = {}
        return dataset
    
    def upload_dataset(self, dsid: str, file_path: str) -> Dict:
        """Upload a file to a dataset."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            return self._request('post', f'/datasets/{dsid}/upload', files=files)
    
    def download_dataset(self, dsid: str, file_name: str, output_path: str) -> None:
        """Download a dataset file.
        TODO:  I think we want this to not require a file_name, but just download all files or have option for main vs. associated.
        """
        url = f"/datasets/{dsid}/download/{file_name}"
        response = self._request('get', url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def request_ingestion(self, dsid: str, ingestor: str) -> Dict:
        """Request dataset ingestion."""
        params = {"ingestion_class": ingestor}
        return self._request('post', f'/datasets/{dsid}/ingest', params=params)
    
    def get_dataset_access_groups(self, dsid: str) -> List[str]:
        """Get access groups for a dataset."""
        groups = self._request('get', f'/datasets/{dsid}/access_groups')
        return [group['group_name'] for group in groups]
    
    def get_dataset_keywords(self, dsid: str) -> List[Dict]:
        """Get keywords associated with a dataset."""
        return self._request('get', f'/datasets/{dsid}/keywords')
    
    def add_dataset_keyword(self, dsid: str, keyword: str) -> Dict:
        """Add a keyword to a dataset."""
        return self._request('post', f'/datasets/{dsid}/keywords', params={'keyword': keyword})
    
    def get_scientific_metadata(self, dsid: str) -> Dict:
        """Get scientific metadata for a dataset."""
        return self._request('get', f'/datasets/{dsid}/scientific_metadata')

    # post vs. patch
    def update_scientific_metadata(self, dsid: str, metadata: Dict) -> Dict:
        """Update scientific metadata for a dataset."""
        return self._request('post', f'/datasets/{dsid}/scientific_metadata', json=metadata)
    
    def get_thumbnails(self, dsid: str) -> List[Dict]:
        """Get thumbnails for a dataset."""
        return self._request('get', f'/datasets/{dsid}/thumbnails')

    # this is not the right payload - should be bytes and caption
    def add_thumbnail(self, dsid: str, file_path: str, description: str = None) -> Dict:
        """Add a thumbnail to a dataset."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'description': description} if description else {}
            return self._request('post', f'/datasets/{dsid}/thumbnails', files=files, data=data)
    
    def get_associated_files(self, dsid: str) -> List[Dict]:
        """Get associated files for a dataset."""
        return self._request('get', f'/datasets/{dsid}/associated_files')

    # files is not the arg here - we need path, size, hash
    def add_associated_file(self, dsid: str, file_path: str, description: str = None) -> Dict:
        """Add an associated file to a dataset."""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'description': description} if description else {}
            return self._request('post', f'/datasets/{dsid}/associated_files', files=files, data=data)
    
    def request_google_drive_transfer(self, dsid: str, folder_id: str) -> Dict:
        """Request transfer of dataset to Google Drive."""
        data = {"folder_id": folder_id}
        return self._request('post', f'/datasets/{dsid}/google_drive_transfer', json=data)
    
    def request_scicat_update(self, dsid: str) -> Dict:
        """Request SciCat update for a dataset."""
        return self._request('post', f'/datasets/{dsid}/scicat_update')
    
    def delete_dataset(self, dsid: str) -> Dict:
        """Delete a dataset."""
        return self._request('delete', f'/datasets/{dsid}')

    def get_current_google_drive_info(self, dsid):
        return self._request('get', f'/datasets/{dsid}/drive_location')

    def get_organized_google_drive_info(self, dsid):
        drive_info = self.get_current_google_drive_info(dsid)
        org_google_drive_info = [x for x in drive_info if 'Organized' in x['folder_path_in_drive']]
        return org_google_drive_info

    def add_drive_location_for_dataset(self, dsid, drive_info: dict):
        #TODO define this
        pass


    def update_ingestion_status(self, dsid, reqid, status, timezone = "America/Los_Angeles"):
        if status == "complete":
            completion_time = get_tz_isoformat(timezone)
            patch_json = {"id": reqid,
                        "status": status,
                        "time_completed": completion_time}
        else:
            patch_json = {"id": reqid,
                        "status": status}
            
        url = f"{self.api_url}/datasets/{dsid}/ingest/{reqid}"
        response = requests.request("patch", url, json=patch_json, headers=self.headers)
        return response

    def update_scicat_upload_status(self, dsid, reqid, status, timezone = "America/Los_Angeles"):
        if status == "complete":
            completion_time = get_tz_isoformat(timezone)
            patch_json = {"id": reqid,
                        "status": status,
                        "time_completed": completion_time}
        else:
            patch_json = {"id": reqid,
                        "status": status}
            
        url = f"{self.api_url}/datasets/{dsid}/ingest/{reqid}"
        response = requests.request("patch", url, json=patch_json, headers=self.headers)
        return response

    def update_transfer_status(self, dsid, reqid, status, timezone = "America/Los_Angeles"):
        if status == "complete":
            completion_time = get_tz_isoformat(timezone)
            patch_json = {"id": reqid,
                        "status": status,
                        "time_completed": completion_time}
        else:
            patch_json = {"id": reqid,
                        "status": status}
            
        url = f"{self.api_url}/datasets/{dsid}/ingest/{reqid}"
        response = requests.request("patch", url, json=patch_json, headers=self.headers)
        return response


    def get_instrument(self, instrument_name=None, instrument_id=None):
        if not instrument_name and not instrument_id:
            raise ValueError("Either instrument_name or instrument_id must be provided")
        
        if instrument_id:
            print("Using Instrument ID to find Instrument")
            params = {"id": instrument_id}
        else:
            params = {"instrument_name": instrument_name}
            
        found_inst = self._request('get', '/instruments', params=params)
        
        if len(found_inst) > 0:
            return found_inst[-1]
        else:
            return None


    def get_or_add_instrument(self, instrument_name, creation_location=None, instrument_owner=None):
        found_inst = self.get_instrument(instrument_name)
        
        if found_inst:
            return found_inst
        
        if not instrument_owner:
            instrument_owner = "undefined"
            
        if not creation_location:
            creation_location = ""
            
        new_instrum = {"instrument_name": instrument_name,
                      "location": creation_location,
                      "owner": instrument_owner}
        
        instrument = self._request('post', '/instruments', json=new_instrum)
        return instrument


    def get_sample(self, sample_id):
        response = self._request('get', f"/samples/{sample_id}")
        return response

    def list_samples(self, **kwargs):
        response = self._request('get', f"/samples", params=kwargs)
        return response
        

    def add_sample(self, unique_id = None, sample_name = None, description=None, creation_date=None, owner_orcid=None, owner_id=None, parents = [], children = []):
        sample_info = {"sample_name": sample_name, 
                      "owner_orcid": owner_orcid,
                      "owner_user_id": owner_id,
                      "description": description,
                      "date_created": creation_date,
                      "parents": [{'unique_id':p} for p in parents], 
                      "children": [{'unique_id':chd} for chd in children]}
        
        if unique_id is not None:
            sample_info['unique_id'] = unique_id
            
        new_samp = self._request('post', "/samples", json=sample_info)
        return new_samp

    
    def add_sample_to_dataset(self, sample_id, dataset_id):
        print(f"/datasets/{dataset_id}/samples/{sample_id}")
        new_link = self._request('post', f"/datasets/{dataset_id}/samples/{sample_id}")
        return new_link


    def add_project(self, project_info):
        new_prop = self._request('post', "/projects", json=project_info)
        return new_prop


    def add_user(self, user_info):
        user_projects = user_info.pop("projects")
        
        new_user = self._request('post', "/users", 
                                json={"user_info": user_info,
                                      "project_ids": user_projects})
        return new_user


    def get_or_add_user(self, orcid, get_user_info_function, **kwargs):
        user = self.get_user(orcid)
        if user:
            return user
        
        user_info = get_user_info_function(orcid, **kwargs)
        if user_info:
            user = self.add_user(user_info)
            return user
        else:
            raise ValueError(f"User info for {orcid} not found in database or using the get_user_info_func")


    def get_or_add_crucible_project(self, crucible_project_id, get_project_info_func, **kwargs):
        proj = self.get_project(crucible_project_id)
        if proj:
            return proj
        
        proj_info = get_project_info_func(crucible_project_id, **kwargs)
        if proj_info:
            proj = self.add_project(proj_info)
            return proj
        else:
            raise ValueError(f"Project info for {crucible_project_id} not found in database or using the provided get_project_info_func")


    # ==== Main utility for instrument integration
    def create_dataset(self, 
                    dataset_name: Optional[str] = None,
                    unique_id: Optional[str] = None, 
                    public: bool = False,
                    owner_orcid: Optional[str] = None,
                    owner_user_id: Optional[int] = None,
                    project_id: Optional[str] = None,
                    instrument_name: Optional[str] = None,
                    instrument_id: Optional[int] = None,
                    measurement: Optional[str] = None, 
                    session_name: Optional[str] = None,
                    creation_time: Optional[str] = None,
                    data_format: Optional[str] = None, 
                    scientific_metadata: Optional[dict] = None,
                    keywords: List[str] = None) -> Dict:
            
            """Create a new dataset with metadata.
            
            Args:
                dataset_name: Name of the dataset
                unique_id: Unique identifier for the dataset
                public: Whether the dataset is public
                owner_orcid: ORCID of the dataset owner
                owner_user_id: User ID of the dataset owner
                project_id: ID of the project this dataset belongs to
                instrument_name: Name of the instrument used
                instrument_id: ID of the instrument used
                measurement: Type of measurement
                session_name: Name of the measurement session
                creation_time: Time of dataset creation
                data_format: Format of the dataset
                scientific_metadata: Additional scientific metadata
                keywords: List of keywords to associate with the dataset
                
            Returns:
                Dictionary containing the created dataset record and metadata
            """
            # Handle instrument if name is provided
            if instrument_name and not instrument_id:
                instrument = self._request('get', '/instruments', params={'name': instrument_name})
                if not instrument:
                    instrument = self._request('post', '/instruments', json={'name': instrument_name})
                instrument_id = instrument['id']

            # Create dataset
            dataset = {
                "unique_id": unique_id,
                "dataset_name": dataset_name,
                "public": public,
                "owner_user_id": owner_user_id,
                "owner_orcid": owner_orcid,
                "project_id": project_id,
                "instrument_id": instrument_id,
                "measurement": measurement,
                "session_name": session_name,
                "creation_time": creation_time,
                "data_format": data_format
            }
            clean_dataset = {k: v for k, v in dataset.items() if v is not None}
            
            new_dataset = self._request('post', '/datasets', json=clean_dataset)
            dsid = new_dataset['unique_id']
            
            # Add scientific metadata if provided
            if scientific_metadata:
                self._request('post', f'/datasets/{dsid}/scientific_metadata', json=scientific_metadata)
                
            # Add keywords if provided
            if keywords:
                for keyword in keywords:
                    self.add_dataset_keyword(dsid, keyword)
                    
            return new_dataset

    def _create_dataset_with_metadata(self, 
                                     dataset_name: Optional[str] = None,
                                     unique_id: Optional[str] = None, 
                                     public: bool = False,
                                     owner_orcid: Optional[str] = None,
                                     owner_user_id: Optional[int] = None,
                                     project_id: Optional[str] = None,
                                     instrument_name: Optional[str] = None,
                                     instrument_id: Optional[int] = None,
                                     measurement: Optional[str] = None, 
                                     session_name: Optional[str] = None,
                                     creation_time: Optional[str] = None,
                                     data_format: Optional[str] = None, 
                                     scientific_metadata: Optional[dict] = None,
                                     keywords: List[str] = None,
                                     get_user_info_function = None,
                                     **extra_fields) -> Dict:
        """Shared helper method to create a dataset with metadata."""
        if keywords is None:
            keywords = []
            
        # get owner_id if orcid provided
        if owner_orcid is not None and get_user_info_function is not None:
            owner = self.get_or_add_user(owner_orcid, get_user_info_function)
            owner_user_id = owner['id']
        
        # get instrument_id if instrument_name provided
        if instrument_name is not None:
            instrument = self.get_or_add_instrument(instrument_name)
            instrument_id = instrument['id']

        # create the dataset with available metadata
        dataset = {"unique_id": unique_id,
                   "dataset_name": dataset_name,
                   "public": public,
                   "owner_user_id": owner_user_id,
                   "owner_orcid": owner_orcid,
                   "project_id": project_id,
                   "instrument_id": instrument_id,
                   "measurement": measurement, 
                   "session_name": session_name,
                   "creation_time": creation_time,
                   "data_format": data_format}
        
        # Add any extra fields
        dataset.update(extra_fields)
        
        clean_dataset = {k: v for k, v in dataset.items() if v is not None}
        new_ds_record = self._request('post', '/datasets', json=clean_dataset)
        dsid = new_ds_record['unique_id']
        
        # add scientific metadata
        scimd = None
        if scientific_metadata is not None:
            scimd = self._request('post', f'/datasets/{dsid}/scientific_metadata', json=scientific_metadata)
            
        # add keywords
        for kw in keywords:
            self.add_dataset_keyword(dsid, kw)

        return {"created_record": new_ds_record, "scientific_metadata_record": scimd, "dsid": dsid}

    def build_new_dataset_from_json(self, 
                                dataset_name: Optional[str] = None,
                                unique_id: Optional[str] = None, 
                                public: bool = False,
                                owner_orcid: Optional[str] = None,
                                owner_user_id: Optional[int] = None,
                                project_id: Optional[str] = None,
                                instrument_name: Optional[str] = None,
                                instrument_id: Optional[int] = None,
                                measurement: Optional[str] = None, 
                                session_name: Optional[str] = None,
                                creation_time: Optional[str] = None,
                                data_format: Optional[str] = None, 
                                scientific_metadata: Optional[dict] = None,
                                keywords: List[str] = None, 
                                get_user_info_function = None, 
                                **kwargs):
        result = self._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            public=public,
            owner_orcid=owner_orcid,
            owner_user_id=owner_user_id,
            project_id=project_id,
            instrument_name=instrument_name,
            instrument_id=instrument_id,
            measurement=measurement,
            session_name=session_name,
            creation_time=creation_time,
            data_format=data_format,
            scientific_metadata=scientific_metadata,
            keywords=keywords,
            get_user_info_function=get_user_info_function
        )
        
        print(f"dsid={result['dsid']}")
        return {"created_record": result["created_record"],
                "scientific_metadata_record": result["scientific_metadata_record"]}

    
    def build_new_dataset_from_file(self,
                                files_to_upload: List[str], 
                                dataset_name: Optional[str] = None,
                                unique_id: Optional[str] = None, 
                                public: bool = False,
                                owner_orcid: Optional[str] = None,
                                owner_user_id: Optional[int] = None,
                                project_id: Optional[str] = None,
                                instrument_name: Optional[str] = None,
                                instrument_id: Optional[int] = None,
                                measurement: Optional[str] = None, 
                                session_name: Optional[str] = None,
                                creation_time: Optional[str] = None,
                                data_format: Optional[str] = None, 
                                source_folder: Optional[str] = None,
                                scientific_metadata: Optional[dict] = None,
                                keywords: List[str] = None, 
                                get_user_info_function = None, 
                                ingestor = None,
                                **kwargs):
        # Create dataset using shared helper with file-specific fields
        main_file = files_to_upload[0]
        extra_fields = {
            "file_to_upload": os.path.join("api-uploads", main_file),
            "source_folder": source_folder
        }
        
        result = self._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            public=public,
            owner_orcid=owner_orcid,
            owner_user_id=owner_user_id,
            project_id=project_id,
            instrument_name=instrument_name,
            instrument_id=instrument_id,
            measurement=measurement,
            session_name=session_name,
            creation_time=creation_time,
            data_format=data_format,
            scientific_metadata=scientific_metadata,
            keywords=keywords,
            get_user_info_function=get_user_info_function,
            **extra_fields
        )
        
        new_ds_record = result["created_record"]
        scimd = result["scientific_metadata_record"]
        dsid = result["dsid"]
        print(f"{dsid=}")
            
        # Send the file as bytes if small enough
        use_upload_endpoint = True
        for f in files_to_upload:
            if os.path.getsize(f) < 1e8:
                continue
            else:
                use_upload_endpoint = False
                break
                
        if use_upload_endpoint:
            for f in files_to_upload:
                file_payload = [self.create_file_payload(f) for f in files_to_upload]
                upload_req = self._request('post', f"/datasets/{dsid}/upload", files=file_payload)

            associated_files = files_to_upload.copy()
            associated_files.pop(0)
            print(f"{associated_files=}")
            for afp in associated_files:
                af = {"filename": os.path.join("api-uploads", afp), 
                     "size": os.path.getsize(afp),
                     "sha256_hash": checkhash(afp)}
                response = self._request('post', f"/datasets/{dsid}/associated_files", json=af)
                print(f"add af out {response}")

            main_file_path = os.path.join("api-uploads", main_file)
            
        else:
            try:
                for f in files_to_upload:
                    print(f"rclone copy '{f}' mf-cloud-storage-upload:/crucible-uploads/large-files/")
                    xx = run_shell(f"rclone copy '{f}' mf-cloud-storage-upload:/crucible-uploads/large-files/")
                    print(f"{xx.stdout=}")
                    print(f"{xx.stderr=}")
            except:
                raise Exception("Files too large for transfer by http")
                
            associated_files = files_to_upload.copy()
            associated_files.pop(0)
            for afp in associated_files:
                af = {"filename": os.path.join("large-files", afp), 
                     "size": os.path.getsize(afp),
                     "sha256_hash": checkhash(afp)}
                
                self._request('post', f"/datasets/{dsid}/associated_files", json=af)

            main_file_path = os.path.join("large-files/", main_file)

        ingest_req_info = self.ingest_dataset(dsid, main_file_path, ingestor)
        return {"created_record": new_ds_record,
                "scientific_metadata_record": scimd,
                "ingestion_request": ingest_req_info}

    
    def ingest_dataset(self, dsid, file_to_upload = None, ingestion_class = None):
            ingest_req = self._request('post', f"/datasets/{dsid}/ingest", params={"file_to_upload": file_to_upload, "ingestion_class": ingestion_class})
            return(ingest_req)
        


    @staticmethod
    def create_file_payload(file_to_upload):
        file_obj = ('files', (file_to_upload, open(file_to_upload, 'rb'), 'text/plain'))
        return file_obj















