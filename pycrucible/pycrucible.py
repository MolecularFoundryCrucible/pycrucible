import os
import time
import requests
import time
from typing import Optional, List, Dict, Union, Any
from .utils import get_tz_isoformat, run_shell, checkhash

class CrucibleClient:
    def __init__(self, api_url: str, api_key: str):
        """
        Initialize the Crucible API client.  
        This client provides access to the Molecular Foundry data lakehouse which contains
        experimental synthesis and characterization data as well as information about the users, 
        projects, and instruments involved in acquiring the data.  Any instrument settings or 
        parameters should be saved in the scientific_metadata record associated with each dataset. 
        
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
        try:
            if response.content:
                return response.json()
            else:
                return None
        except:
            return response

        #return response.json() if response.content else None

    def list_projects(self) -> List[Dict]:
        """List all accessible projects.

        Returns:
            List[Dict]: Project metadata including project_id, project_name, description, project_lead_email
        """
        return self._request('get', '/projects')
    
    def get_project(self, project_id: str) -> Dict:
        """Get details of a specific project.

        Args:
            project_id (str): Unique project identifier

        Returns:
            Dict: Complete project information
        """
        return self._request('get', f'/projects/{project_id}')
    
    def get_user(self, orcid: str) -> Dict:
        """Get user details by ORCID (admin access required).

        Args:
            orcid (str): ORCID identifier (format: 0000-0000-0000-000X)

        Returns:
            Dict: User profile with orcid, name, email, timestamps
        """
        return self._request('get', f'/users/{orcid}')
    
    def get_user_by_email(self, email: str) -> Dict:
        """Get user details by email address.

        Args:
            email (str): Email address to search for

        Returns:
            Dict: User information if found, searches both email and lbl_email fields
        """
        params = {"email": email}
        result = self._request('get', '/users', params=params)
        if not result:
            params = {"lbl_email": email}
            result = self._request('get', '/users', params=params)
        return result
    
    def get_project_users(self, project_id: str) -> List[Dict]:
        """Get users associated with a project (admin access required).

        Args:
            project_id (str): Unique project identifier

        Returns:
            List[Dict]: Project team members (excludes project lead)
        """
        return self._request('get', f'/projects/{project_id}/users')
    
    def list_datasets(self, sample_id: Optional[str] = None, **kwargs) -> List[Dict]:
        """List datasets with optional filtering.

        Args:
            sample_id (str, optional): If provided, returns datasets for this sample
            **kwargs: Query parameters for filtering (keyword, owner_orcid, etc.)

        Returns:
            List[Dict]: Dataset objects matching filter criteria
        """
        if sample_id:
            return self._request('get', f'/samples/{sample_id}/datasets', params=kwargs)
        return self._request('get', '/datasets', params=kwargs)
    
    def get_dataset(self, dsid: str, include_metadata: bool = False) -> Dict:
        """Get dataset details, optionally including scientific metadata.

        Args:
            dsid (str): Dataset unique identifier
            include_metadata (bool): Whether to include scientific metadata

        Returns:
            Dict: Dataset object with optional metadata
        """
        dataset = self._request('get', f'/datasets/{dsid}')
        if dataset and include_metadata:
            try:
                metadata = self._request('get', f'/datasets/{dsid}/scientific_metadata')
                dataset['scientific_metadata'] = metadata or {}
            except requests.exceptions.RequestException:
                dataset['scientific_metadata'] = {}
        return dataset
    
    def upload_dataset(self, dsid: str, file_path: str) -> Dict:
        """Upload a file to a dataset.

        Args:
            dsid (str): Dataset unique identifier
            file_path (str): Local path to file to upload

        Returns:
            Dict: Upload response with ingestion request info
        """
        with open(file_path, 'rb') as f:
            files = [('files', (os.path.basename(file_path), f, 'application/octet-stream'))]
            return self._request('post', f'/datasets/{dsid}/upload', files=files)
    
    def download_dataset(self, dsid: str, file_name: Optional[str] = None, output_path: Optional[str] = None) -> None:
        """Download a dataset file.

        Args:
            dsid (str): Dataset ID
            file_name (str, optional): File to download (uses dataset's file_to_upload if not provided)
            output_path (str, optional): Local save path (saves to crucible-downloads/ if not provided)
        """
        # If no file_name specified, get it from the dataset's file_to_upload field
        dataset = self.get_dataset(dsid)
        if file_name is None:
            if 'file_to_upload' not in dataset or not dataset['file_to_upload']:
                raise ValueError(f"No file_name specified and dataset {dsid} has no file_to_upload field")
            file_to_upload = dataset['file_to_upload']
            # Extract just the filename from the path (remove api-uploads/ or large-files/ prefix)
            file_name = os.path.basename(file_to_upload)

        # Set default output path if not provided
        if output_path is None:
            output_path = os.path.join('crucible-downloads', file_name)
            os.makedirs('crucible-downloads', exist_ok = True)

        # Check if file already exists (caching)
        if os.path.exists(output_path):
            curr_hash = checkhash(output_path)
            if curr_hash == dataset['sha256_hash']:
                print(f"File {output_path} already exists, skipping download")
                return
            else:
                url = f"/datasets/{dsid}/download/{file_name}"
                response = self._request('get', url, stream=True)
                response.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return(f"download complete for file {output_path}")
        
    
    def request_ingestion(self, dsid: str, file_to_upload: str = None, ingestor: str = None) -> Dict:
        """Request dataset ingestion.

        Args:
            dsid (str): Dataset ID
            file_to_upload (str, optional): Path to file for ingestion
            ingestor (str, optional): Ingestion class to use

        Returns:
            Dict: Ingestion request with id and status
        """
        params = {"ingestion_class": ingestor, "file_to_upload": file_to_upload}
        return self._request('post', f'/datasets/{dsid}/ingest', params=params)

    
    def get_ingestion_status(self, dsid: str, reqid: str) -> Dict:
        """Get the status of an ingestion request.

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID for the ingestion

        Returns:
            Dict: Status, timestamps, and processing details
        """
        return self._request('get', f'/datasets/{dsid}/ingest/{reqid}')
    
    def get_scicat_status(self, dsid: str, reqid: str) -> Dict:
        """Get the status of a SciCat request.

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID for the SciCat operation

        Returns:
            Dict: SciCat sync status and timestamps
        """
        return self._request('get', f'/datasets/{dsid}/scicat_update/{reqid}')
    
    def get_request_status(self, dsid: str, reqid: str, request_type: str) -> Dict:
        """Get the status of any type of request.

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID
            request_type (str): Type of request ('ingest' or 'scicat_update')

        Returns:
            Dict: Request status information
        """
        if request_type == 'ingest':
            return self.get_ingestion_status(dsid, reqid)
        elif request_type == 'scicat_update':
            return self.get_scicat_status(dsid, reqid)
        else:
            raise ValueError(f"Unsupported request_type: {request_type}")
    
    def wait_for_request_completion(self, dsid: str, reqid: str, request_type: str,
                                  sleep_interval: int = 5) -> Dict:
        """Wait for a request to complete by polling its status.

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID
            request_type (str): Type of request ('ingest' or 'scicat_update')
            sleep_interval (int): Seconds between status checks

        Returns:
            Dict: Final request status information
        """
        req_info = self.get_request_status(dsid, reqid, request_type)
        print(f"Waiting for {request_type} request to complete...")

        while req_info['status'] in ['requested', 'started']:
            time.sleep(sleep_interval)
            req_info = self.get_request_status(dsid, reqid, request_type)
            print(f"Current status: {req_info['status']}")

        print(f"Request completed with status: {req_info['status']}")
        return req_info
    
    def get_dataset_access_groups(self, dsid: str) -> List[str]:
        """Get access groups for a dataset (admin access required).

        Args:
            dsid (str): Dataset ID

        Returns:
            List[str]: List of access group names with dataset permissions
        """
        groups = self._request('get', f'/datasets/{dsid}/access_groups')
        return [group['group_name'] for group in groups]
        
    
    def get_dataset_keywords(self, dsid: str) -> List[Dict]:
        """Get keywords associated with a dataset.

        Args:
            dsid (str): Dataset ID

        Returns:
            List[Dict]: Keyword objects with keyword text and usage counts
        """
        return self._request('get', f'/datasets/{dsid}/keywords')
    
    def add_dataset_keyword(self, dsid: str, keyword: str) -> Dict:
        """Add a keyword to a dataset.

        Args:
            dsid (str): Dataset ID
            keyword (str): Keyword/tag to associate with dataset

        Returns:
            Dict: Keyword object with updated usage count
        """
        return self._request('post', f'/datasets/{dsid}/keywords', data={'keyword': keyword})
    
    def get_scientific_metadata(self, dsid: str) -> Dict:
        """Get scientific metadata for a dataset.

        Args:
            dsid (str): Dataset ID

        Returns:
            Dict: Scientific metadata containing experimental parameters and settings
        """
        return self._request('get', f'/datasets/{dsid}/scientific_metadata')

    def update_scientific_metadata(self, dsid: str, metadata: Dict) -> Dict:
        """Create or replace scientific metadata for a dataset.

        Args:
            dsid (str): Dataset ID
            metadata (Dict): Scientific metadata dictionary

        Returns:
            Dict: Updated metadata object
        """
        return self._request('post', f'/datasets/{dsid}/scientific_metadata', json=metadata)
    
    def get_thumbnails(self, dsid: str) -> List[Dict]:
        """Get thumbnails for a dataset.

        Args:
            dsid (str): Dataset ID

        Returns:
            List[Dict]: Thumbnail objects with base64-encoded images
        """
        return self._request('get', f'/datasets/{dsid}/thumbnails')

    def add_thumbnail(self, dsid: str, file_path: str, thumbnail_name: str = None) -> Dict:
        """Add a thumbnail to a dataset.

        Args:
            dsid (str): Dataset ID
            file_path (str): Path to image file
            thumbnail_name (str, optional): Display name (uses filename if not provided)

        Returns:
            Dict: Created thumbnail object
        """
        import base64

        # Read file and encode to base64
        with open(file_path, 'rb') as f:
            file_content = f.read()
            thumbnail_b64str = base64.b64encode(file_content).decode('utf-8')

        # Use filename if no thumbnail_name provided
        if thumbnail_name is None:
            thumbnail_name = os.path.basename(file_path)

        thumbnail_data = {
            'thumbnail_name': thumbnail_name,
            'thumbnail_b64str': thumbnail_b64str
        }
        return self._request('post', f'/datasets/{dsid}/thumbnails', json=thumbnail_data)
    
    def get_associated_files(self, dsid: str) -> List[Dict]:
        """Get associated files for a dataset.

        Args:
            dsid (str): Dataset ID

        Returns:
            List[Dict]: File metadata with names, sizes, and hashes
        """
        return self._request('get', f'/datasets/{dsid}/associated_files')

    def add_associated_file(self, dsid: str, file_path: str, filename: str = None) -> Dict:
        """Add an associated file to a dataset.

        Args:
            dsid (str): Dataset ID
            file_path (str): Path to file (for calculating metadata)
            filename (str, optional): Filename to store (uses basename if not provided)

        Returns:
            Dict: Created associated file object
        """
        # Calculate file metadata
        file_size = os.path.getsize(file_path)
        file_hash = checkhash(file_path)

        # Use basename if no filename provided
        if filename is None:
            filename = os.path.basename(file_path)

        associated_file_data = {
            'filename': filename,
            'size': file_size,
            'sha256_hash': file_hash
        }
        return self._request('post', f'/datasets/{dsid}/associated_files', json=associated_file_data)
    
    def request_google_drive_transfer(self, dsid: str) -> Dict:
        """Request transfer of dataset to Google Drive.

        Args:
            dsid (str): Dataset ID

        Returns:
            Dict: Transfer request with id and status
        """
        return self._request('post', f'/datasets/{dsid}/google_drive_transfer')
    
    def send_to_scicat(self, dsid: str, wait_for_scicat_response: bool = False, overwrite_data: bool = False) -> Dict:
        """Request SciCat update for a dataset.

        Args:
            dsid (str): Dataset ID
            wait_for_scicat_response (bool): Whether to wait for completion
            overwrite_data (bool): Whether to overwrite existing SciCat records

        Returns:
            Dict: SciCat update request information
        """
        params = {'overwrite_data': overwrite_data} if overwrite_data else None
        scicat_req_info = self._request('post', f'/datasets/{dsid}/scicat_update', params=params)

        if wait_for_scicat_response:
            scicat_req_info = self.wait_for_request_completion(dsid, scicat_req_info['id'], 'scicat_update')

        return scicat_req_info

    def delete_dataset(self, dsid: str) -> Dict:
        """Delete a dataset (not implemented in API).

        Args:
            dsid (str): Dataset ID

        Returns:
            Dict: Deletion response
        """
        return self._request('delete', f'/datasets/{dsid}')

    def get_current_google_drive_info(self, dsid: str) -> Dict:
        """Get current Google Drive location information for a dataset.

        Args:
            dsid (str): Dataset ID

        Returns:
            Dict: Google Drive location information
        """
        return self._request('get', f'/datasets/{dsid}/drive_location')

    def get_organized_google_drive_info(self, dsid: str) -> List[Dict]:
        """Get organized Google Drive folder information for a dataset.

        Args:
            dsid (str): Dataset ID

        Returns:
            List[Dict]: Organized Google Drive folder information
        """
        drive_info = self.get_current_google_drive_info(dsid)
        org_google_drive_info = [x for x in drive_info if 'Organized' in x['folder_path_in_drive']]
        return org_google_drive_info

    def add_drive_location_for_dataset(self, dsid: str, drive_info: Dict) -> None:
        """Add drive location information for a dataset (not implemented).

        Args:
            dsid (str): Dataset ID
            drive_info (Dict): Drive location information to add
        """
        #TODO define this
        pass


    def update_ingestion_status(self, dsid: str, reqid: str, status: str, timezone: str = "America/Los_Angeles"):
        """Update the status of a dataset ingestion request (admin use).

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID for the ingestion
            status (str): New status ('complete', 'in_progress', 'failed')
            timezone (str): Timezone for completion time

        Returns:
            requests.Response: HTTP response from the update request
        """
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

    def update_scicat_upload_status(self, dsid: str, reqid: str, status: str, timezone: str = "America/Los_Angeles"):
        """Update the status of a SciCat upload request (admin use).

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID for the SciCat upload
            status (str): New status ('complete', 'in_progress', 'failed')
            timezone (str): Timezone for completion time

        Returns:
            requests.Response: HTTP response from the update request
        """
        if status == "complete":
            completion_time = get_tz_isoformat(timezone)
            patch_json = {"id": reqid,
                        "status": status,
                        "time_completed": completion_time}
        else:
            patch_json = {"id": reqid,
                        "status": status}

        url = f"{self.api_url}/datasets/{dsid}/scicat_update/{reqid}"
        response = requests.request("patch", url, json=patch_json, headers=self.headers)
        return response

    def update_transfer_status(self, dsid: str, reqid: str, status: str, timezone: str = "America/Los_Angeles"):
        """Update the status of a dataset transfer request (admin use).

        Args:
            dsid (str): Dataset ID
            reqid (str): Request ID for the transfer
            status (str): New status ('complete', 'in_progress', 'failed')
            timezone (str): Timezone for completion time

        Returns:
            requests.Response: HTTP response from the update request
        """
        if status == "complete":
            completion_time = get_tz_isoformat(timezone)
            patch_json = {"id": reqid,
                        "status": status,
                        "time_completed": completion_time}
        else:
            patch_json = {"id": reqid,
                        "status": status}

        url = f"{self.api_url}/datasets/{dsid}/google_drive_transfer/{reqid}"
        response = requests.request("patch", url, json=patch_json, headers=self.headers)
        return response


    def list_instruments(self) -> List[Dict]:
        """List all available instruments.

        Returns:
            List[Dict]: Instrument objects with specifications and metadata
        """
        return self._request('get', '/instruments')

    def get_instrument(self, instrument_name: str = None, instrument_id: str = None) -> Dict:
        """Get instrument information by name or ID.

        Args:
            instrument_name (str, optional): Name of the instrument
            instrument_id (str, optional): Unique ID of the instrument

        Returns:
            Dict or None: Instrument information if found, None otherwise

        Raises:
            ValueError: If neither parameter is provided
        """
        if not instrument_name and not instrument_id:
            raise ValueError("Either instrument_name or instrument_id must be provided")

        if instrument_id:
            print("Using Instrument ID to find Instrument")
            params = {"unique_id": instrument_id}
        else:
            params = {"instrument_name": instrument_name}

        found_inst = self._request('get', '/instruments', params=params)

        if len(found_inst) > 0:
            return found_inst[-1]
        else:
            return None


    def get_or_add_instrument(self, instrument_name: str, creation_location: str = None, instrument_owner: str = None) -> Dict:
        """Get an existing instrument or create a new one if it doesn't exist.

        Args:
            instrument_name (str): Name of the instrument
            creation_location (str, optional): Location where instrument was created
            instrument_owner (str, optional): Owner of the instrument

        Returns:
            Dict: Instrument information (existing or newly created)
        """
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


    def get_sample(self, sample_id: str) -> Dict:
        """Get sample information by ID.

        Args:
            sample_id (str): Sample unique identifier

        Returns:
            Dict: Sample information with associated datasets
        """
        response = self._request('get', f"/samples/{sample_id}")
        return response

    def list_samples(self, dataset_id: str = None, parent_id: str = None, **kwargs) -> List[Dict]:
        """List samples with optional filtering.

        Args:
            dataset_id (str, optional): Get samples from specific dataset
            parent_id (str, optional): Get child samples from parent
            **kwargs: Query parameters for filtering samples

        Returns:
            List[Dict]: Sample information
        """
        if dataset_id:
            response = self._request('get', f"/datasets/{dataset_id}/samples", params=kwargs)
        elif parent_id:
            response = self._request('get', f"/samples/{parent_id}/children", params=kwargs)
        else:
            response = self._request('get', f"/samples", params=kwargs)
        return response
        

    def add_sample(self, unique_id: str = None, sample_name: str = None, description: str = None,
                   creation_date: str = None, owner_orcid: str = None, owner_id: int = None,
                   parents: List[Dict] = [], children: List[Dict] = []) -> Dict:
        """Add a new sample with optional parent-child relationships.

        Args:
            unique_id (str, optional): Unique sample identifier
            sample_name (str, optional): Human-readable sample name
            description (str, optional): Sample description
            creation_date (str, optional): Sample creation date
            owner_orcid (str, optional): Owner's ORCID
            owner_id (int, optional): Owner's user ID
            parents (List[Dict], optional): Parent samples
            children (List[Dict], optional): Child samples

        Returns:
            Dict: Created sample object
        """
        sample_info = {   "unique_id": unique_id,
                          "sample_name": sample_name,
                          "owner_orcid": owner_orcid,
                          "owner_user_id": owner_id,
                          "description": description,
                          "date_created": creation_date
                        }
        print(sample_info)
        new_samp = self._request('post', "/samples", json=sample_info)
        print(f"{new_samp=}")

        for p in parents:
            parent_id = p['unique_id']
            child_id = new_samp['unique_id']
            self._request('post', f"/samples/{parent_id}/children/{child_id}")

        for chd in children:
            parent_id = new_samp['unique_id']
            child_id = chd['unique_id']
            self._request('post', f"/samples/{parent_id}/children/{child_id}")

        return new_samp

    
    def add_sample_metadata(self, sample_id: str, sample_type: str, **kwargs) -> Dict:
        """Upload metadata to table and link to provided sample.

        Args:
            sample_id (str): Sample's unique identifier
            sample_type (str): Type of sample metadata (e.g., 'spinbot_batch')
            **kwargs: Metadata fields

        Returns:
            Dict: Created metadata object
        """
        response = self._request('post', f"/samples/{sample_id}/metadata/{sample_type}", json = kwargs)
        return response

    def get_sample_metadata(self, sample_id: str, sample_type: str) -> Dict:
        """Get metadata for a sample by type.

        Args:
            sample_id (str): Sample's unique identifier
            sample_type (str): Type of sample metadata

        Returns:
            Dict: Sample metadata object
        """
        response = self._request('get', f"/samples/{sample_id}/metadata/{sample_type}")
        return response

    
    def add_sample_to_dataset(self, dataset_id: str, sample_id: str) -> Dict:
        """Link a sample to a dataset.

        Args:
            dataset_id (str): Dataset ID
            sample_id (str): Sample ID

        Returns:
            Dict: Information about the created link
        """
        print(f"/datasets/{dataset_id}/samples/{sample_id}")
        new_link = self._request('post', f"/datasets/{dataset_id}/samples/{sample_id}")
        return new_link

    add_dataset_to_sample = add_sample_to_dataset
    
    
    def add_user(self, user_info: Dict) -> Dict:
        """Add a new user to the system (admin access required).

        Args:
            user_info (Dict): User information including 'projects' key

        Returns:
            Dict: Created user object
        """
        user_projects = user_info.pop("projects")

        new_user = self._request('post', "/users",
                                json={"user_info": user_info,
                                      "project_ids": user_projects})
        return new_user


    def get_or_add_user(self, orcid, get_user_info_function, **kwargs):
        """Get an existing user or create a new one if they don't exist.
        
        Args:
            orcid (str): ORCID of the user
            get_user_info_function (callable): Function to retrieve user info if not found
            **kwargs: Additional arguments to pass to get_user_info_function
            
        Returns:
            dict: User information (existing or newly created)
            
        Raises:
            ValueError: If user info cannot be found or created
        """
        user = self.get_user(orcid)
        if user:
            return user
        
        user_info = get_user_info_function(orcid, **kwargs)
        if user_info:
            user = self.add_user(user_info)
            return user
        else:
            raise ValueError(f"User info for {orcid} not found in database or using the get_user_info_func")

    def get_or_add_crucible_project(self, crucible_project_id, get_project_info_func = None, **kwargs):
        """Get an existing project or create a new one if it doesn't exist.
        
        Args:
            crucible_project_id (str): ID of the Crucible project
            get_project_info_func (callable): Function to retrieve project info if not found
            **kwargs: Additional arguments to pass to get_project_info_func
            
        Returns:
            dict: Project information (existing or newly created)
            
        Raises:
            ValueError: If project info cannot be found or created
        """
        proj = self.get_project(crucible_project_id)
        if proj:
            return proj

        project_info = get_project_info_func(crucible_project_id, **kwargs)
            
        if project_info:
            proj = self._request('post', "/projects", json=project_info)
            return proj
        else:
            raise ValueError(f"Project info for {crucible_project_id} not found in database or using the provided get_project_info_func")

    get_or_add_project = get_or_add_crucible_project
    add_project = get_or_add_project

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
                dataset_name (str, optional): Name of the dataset
                unique_id (str, optional): Unique identifier
                public (bool): Whether dataset is public
                owner_orcid (str, optional): Owner's ORCID
                owner_user_id (int, optional): Owner's user ID
                project_id (str, optional): Associated project ID
                instrument_name (str, optional): Instrument name
                instrument_id (int, optional): Instrument ID
                measurement (str, optional): Type of measurement
                session_name (str, optional): Session name
                creation_time (str, optional): Creation timestamp
                data_format (str, optional): Data format
                scientific_metadata (dict, optional): Scientific metadata
                keywords (List[str], optional): Keywords to associate

            Returns:
                Dict: Created dataset object
            """
            # Handle instrument if name is provided
            if instrument_name and not instrument_id:
                instrument = self._request('get', '/instruments', params={'instrument_name': instrument_name})
                if not instrument:
                    instrument = self._request('post', '/instruments', json={'instrument_name': instrument_name})
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
                                     verbose = False,
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
        if verbose:
            print('creating new dataset record...')
        new_ds_record = self._request('post', '/datasets', json=clean_dataset)
        dsid = new_ds_record['unique_id']
        
        # add scientific metadata
        scimd = None
        if scientific_metadata is not None:
            if verbose:
                print(f'adding scientific metadata record for {dsid}')
            scimd = self._request('post', f'/datasets/{dsid}/scientific_metadata', json=scientific_metadata)
            if verbose:
                print('metadata addition complete')
                print(f'adding keywords to dataset {dsid}: {keywords}')
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
        """Build a new dataset from JSON metadata without file upload.
        
        Args:
            dataset_name (str, optional): Name of the dataset
            unique_id (str, optional): Unique identifier for the dataset
            public (bool): Whether the dataset is public (default: False)
            owner_orcid (str, optional): ORCID of the dataset owner
            owner_user_id (int, optional): User ID of the dataset owner
            project_id (str, optional): ID of the project this dataset belongs to
            instrument_name (str, optional): Name of the instrument used
            instrument_id (int, optional): ID of the instrument used
            measurement (str, optional): Type of measurement
            session_name (str, optional): Name of the measurement session
            creation_time (str, optional): Time of dataset creation
            data_format (str, optional): Format of the dataset
            scientific_metadata (dict, optional): Additional scientific metadata
            keywords (list, optional): List of keywords to associate with the dataset
            get_user_info_function (callable, optional): Function to get user info if needed
            **kwargs: Additional arguments
            
        Returns:
            dict: Dictionary containing created_record and scientific_metadata_record
            
        Raises:
            ValueError: If project_id is provided but the project does not exist in the database
        """
        # Validate project exists before making any database changes
        if project_id is not None:
            try:
                self.get_project(project_id)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Project with ID '{project_id}' does not exist in the database. "
                                   f"Please create the project first or use a valid project ID.")
                else:
                    raise
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
            verbose = verbose
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
                                verbose = False,
                                wait_for_ingestion_response = True,
                                **kwargs):
        """Build a new dataset with file upload and ingestion.
        
        Args:
            files_to_upload (List[str]): List of file paths to upload
            dataset_name (str, optional): Name of the dataset
            unique_id (str, optional): Unique identifier for the dataset
            public (bool): Whether the dataset is public (default: False)
            owner_orcid (str, optional): ORCID of the dataset owner
            owner_user_id (int, optional): User ID of the dataset owner
            project_id (str, optional): ID of the project this dataset belongs to
            instrument_name (str, optional): Name of the instrument used
            instrument_id (int, optional): ID of the instrument used
            measurement (str, optional): Type of measurement
            session_name (str, optional): Name of the measurement session
            creation_time (str, optional): Time of dataset creation
            data_format (str, optional): Format of the dataset
            source_folder (str, optional): Source folder path
            scientific_metadata (dict, optional): Additional scientific metadata
            keywords (list, optional): List of keywords to associate with the dataset
            get_user_info_function (callable, optional): Function to get user info if needed
            ingestor (str, optional): Ingestion class to use
            **kwargs: Additional arguments
            
        Returns:
            dict: Dictionary containing created_record, scientific_metadata_record, and ingestion_request
            
        Raises:
            ValueError: If project_id is provided but the project does not exist in the database
        """
        # Validate project exists before making any database changes
        if project_id is not None:
            try:
                self.get_project(project_id)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Project with ID '{project_id}' does not exist in the database. "
                                   f"Please create the project first or use a valid project ID.")
                else:
                    raise
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
        print(f"created dataset record with {dsid=}")
            
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
                if verbose:
                    print(f"uploading file {f}...")
                file_payload = [self.create_file_payload(f) for f in files_to_upload]
                upload_req = self._request('post', f"/datasets/{dsid}/upload", files=file_payload)
                if verbose:
                    print(f"upload complete.")
                
            associated_files = files_to_upload.copy()
            associated_files.pop(0)
            if verbose: 
                print("adding associated files to dataset record")
            for afp in associated_files:
                af = {"filename": os.path.join("api-uploads", afp), 
                     "size": os.path.getsize(afp),
                     "sha256_hash": checkhash(afp)}
                response = self._request('post', f"/datasets/{dsid}/associated_files", json=af)
                if verbose:
                    print(f"added {afp}")

            main_file_path = os.path.join("api-uploads", main_file)
            
        else:
            try:
                for f in files_to_upload:
                    if verbose:
                        print(f"uploading file {f}...")
                        print(f"rclone copy '{f}' mf-cloud-storage-upload:/crucible-uploads/large-files/")
                    xx = run_shell(f"rclone copy '{f}' mf-cloud-storage-upload:/crucible-uploads/large-files/")
                    if verbose:
                        print(f"{xx.stdout=}")
                        print(f"{xx.stderr=}")
                        print(f"upload complete.")
            except:
                raise Exception("Files too large for transfer by http")
                
            associated_files = files_to_upload.copy()
            associated_files.pop(0)
            if verbose:
                print("adding associated files to dataset record")
            for afp in associated_files:
                af = {"filename": os.path.join("large-files", afp), 
                     "size": os.path.getsize(afp),
                     "sha256_hash": checkhash(afp)}
                
                self._request('post', f"/datasets/{dsid}/associated_files", json=af)
                if verbose:
                    print(f"added {afp}")
                
            main_file_path = os.path.join("large-files/", main_file)
        if verbose:
            print(f"submitting {dsid} to be ingested from file {main_file_path} using the class {ingestor}")
        ingest_req_info = self.ingest_dataset(dsid, main_file_path, ingestor)
        print(f"ingestion request {ingest_req_info['id']} is added to the queue")
        if wait_for_ingestion_response:
            ingest_req_info = self.wait_for_request_completion(dsid, ingest_req_info['id'], 'ingest')

        return {"created_record": new_ds_record,
                "scientific_metadata_record": scimd,
                "ingestion_request": ingest_req_info}

    
    def ingest_dataset(self, dsid: str, file_to_upload: str = None, ingestion_class: str = None) -> Dict:
        """Request ingestion of a dataset file.

        Args:
            dsid (str): Dataset ID
            file_to_upload (str, optional): Path to the file to ingest
            ingestion_class (str, optional): Class to use for ingestion

        Returns:
            Dict: Ingestion request information
        """
        ingest_req = self._request('post',
                                   f"/datasets/{dsid}/ingest",
                                   params={"file_to_upload": file_to_upload, "ingestion_class": ingestion_class})
        return(ingest_req)
        


    @staticmethod
    def create_file_payload(file_to_upload: str) -> tuple:
        """Create a file payload for upload.

        Args:
            file_to_upload (str): Path to the file to upload

        Returns:
            tuple: File payload tuple for requests
        """
        file_obj = ('files', (file_to_upload, open(file_to_upload, 'rb'), 'text/plain'))
        return file_obj

# ========== this should probably go somewhere else but for now.. here so people can use it 
import ipywidgets as widgets
from IPython.display import display, clear_output
import os

class SecureInput:
    def __init__(self, description="Enter secret:", var_name = "TEMP_SECRET"):
        self.description = description
        self.var_name = var_name
        self.secret = None
        self.create_widget()
    
    def create_widget(self):
        self.password_widget = widgets.Password(
            placeholder='Enter secret here',
            description='',
            style={'description_width': 'initial'}
        )
        
        self.submit_button = widgets.Button(
            description='Store Secret',
            button_style='success',
            icon='lock'
        )
        
        self.output = widgets.Output()
        
        self.submit_button.on_click(self.on_submit)
        
        self.container = widgets.VBox([
            widgets.HTML(f"<b>{self.description}</b>"),
            self.password_widget,
            self.submit_button,
            self.output
        ])
        
        display(self.container)
    
    def on_submit(self, button):
        with self.output:
            clear_output()
            if self.password_widget.value:
                self.secret = self.password_widget.value
                # Optionally store in environment
                os.environ[self.var_name] = self.secret
                print("✓ Secret stored securely")
                # Clear the widget
                self.password_widget.value = ""
                # Hide the input form
                self.password_widget.layout.display = 'none'
                self.submit_button.layout.display = 'none'
            else:
                print("❌ Please enter a value")
    












