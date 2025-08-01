import os
import requests
from typing import Optional, List
from utils import get_tz_isoformat, run_shell, checkhash

def list_crucible_projects(crucible_api_url, apikey):
    auth_header = {"Authorization":f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/projects"

    prop = requests.get(url=endpt, headers=auth_header).json()
    return(prop)


def get_crucible_project(project_id, crucible_api_url, apikey):
    auth_header = {"Authorization":f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/projects/{project_id}"

    prop = requests.get(url=endpt, headers=auth_header).json()
    return(prop)


def get_crucible_user(orcid, crucible_api_url, apikey):
    auth_header = {"Authorization":f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/users/{orcid}"

    user = requests.get(url=endpt, headers=auth_header).json()
    return(user)

def get_crucible_user_by_email(email, crucible_api_url, apikey):
    auth_header = {"Authorization":f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/users"

    found_user = requests.get(url=endpt, params={"email": email}, headers=auth_header).json()
    if found_user: 
        return(found_user)
    else:
        found_user = requests.get(url=endpt, params={"lbl_email": email}, headers=auth_header).json()

    return(found_user)


def get_users_on_project(project_id, crucible_api_url, apikey):
    auth_header = {"Authorization":f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/projects/{project_id}/users"

    users_on_prop = requests.get(url=endpt, headers=auth_header).json()
    return(users_on_prop)


def list_datasets(crucible_api_url, apikey, **kwargs):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets"
    datasets = requests.get(url=endpt, headers = auth_header, params = kwargs)
    return datasets


def request_ingestion(crucible_api_url, apikey, dsid, ingestor):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}/ingest"
    ingest_req = requests.post(url = endpt,
                               params = {"ingestion_class": ingestor},
                               headers = auth_header)
    return ingest_req
    

def get_dataset_info(crucible_api_url, apikey, dsid, return_scimd = False):

    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}"

    found_dataset = requests.get(url=endpt, headers = auth_header).json()
    
    if found_dataset and return_scimd:
        endpt = f"{crucible_api_url}/datasets/{dsid}/scientific_metadata"
        scimd = requests.get(url= endpt, headers = auth_header)
        
        if scimd:
            found_dataset['scientific_metadata'] = scimd.json()   
        else:
            found_dataset['scientific_metadata'] = {}

    return found_dataset


def get_dataset_access_groups(crucible_api_url, apikey, dsid):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}/access_groups"

    access_groups = requests.get(url=endpt, headers = auth_header).json()
    access_group_names = [ag['group_name'] for ag in access_groups]
    return(access_group_names)


def get_dataset_keywords(dsid, crucible_api_url, apikey):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}/keywords"

    keywords = requests.get(url=endpt, headers = auth_header).json()
    return(keywords)


def get_thumbnails_for_dataset(dsid, crucible_api_url, apikey):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}/thumbnails"

    thumbnails = requests.get(url=endpt, headers = auth_header).json()
    return thumbnails

def get_associated_files_for_dataset(dsid, crucible_api_url, apikey):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}/associated_files"

    associated_files = requests.get(url=endpt, headers = auth_header).json()
    return associated_files


def get_current_google_drive_info(dsid, crucible_api_url, apikey):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/datasets/{dsid}/drive_location"

    drive_info = requests.get(url=endpt, headers = auth_header).json()
    return drive_info

def get_organized_google_drive_info(dsid, crucible_api_url, apikey):
    
    drive_info = get_current_google_drive_info(dsid, crucible_api_url, apikey)
    org_google_drive_info = [x for x in drive_info if 'Organized' in x['folder_path_in_drive']]
    return org_google_drive_info

def add_drive_location_for_dataset(dsid, crucible_apiurl, apikey, drive_info: dict):
    #TODO define this
    pass


def update_ingestion_status(crucible_api_url, apikey, dsid, reqid, status, timezone = "America/Los_Angeles"):

    # time_completed should actually be computed here if 
    # you only add it when complete

    if status == "complete":
        completion_time = get_tz_isoformat(timezone)
        patch_json = {"id": reqid,
                      "status": status,
                      "time_completed": completion_time}
    else:
        patch_json = {"id": reqid,
                      "status": status}
        
    res = requests.request("patch",
                     url = f"{crucible_api_url}/datasets/{dsid}/ingest/{reqid}",
                     json = patch_json,
                     headers = {"Authorization":f"Bearer {apikey}"})
    
    # make this raise exception if error?
    return(res)

def update_scicat_upload_status(crucible_api_url, apikey, dsid, reqid, status, timezone = "America/Los_Angeles"):

    # time_completed should actually be computed here if 
    # you only add it when complete

    if status == "complete":
        completion_time = get_tz_isoformat(timezone)
        patch_json = {"id": reqid,
                      "status": status,
                      "time_completed": completion_time}
    else:
        patch_json = {"id": reqid,
                      "status": status}
        
    res = requests.request("patch",
                     url = f"{crucible_api_url}/datasets/{dsid}/scicat_update/{reqid}",
                     json = patch_json,
                     headers = {"Authorization":f"Bearer {apikey}"})
    
    # make this raise exception if error?
    return(res)

def update_transfer_status(crucible_api_url, apikey, dsid, reqid, status, timezone = "America/Los_Angeles"):

    # time_completed should actually be computed here if 
    # you only add it when complete

    if status == "complete":
        completion_time = get_tz_isoformat(timezone)
        patch_json = {"id": reqid,
                      "status": status,
                      "time_completed": completion_time}
    else:
        patch_json = {"id": reqid,
                      "status": status}
        
    res = requests.request("patch",
                     url = f"{crucible_api_url}/datasets/{dsid}/google_drive_transfer/{reqid}",
                     json = patch_json,
                     headers = {"Authorization":f"Bearer {apikey}"})
    
    # make this raise exception if error?
    return(res)


def get_instrument(crucible_api_url,
                   apikey, 
                   instrument_name = None,
                   instrument_id = None):
        
    auth_header = {"Authorization":f"Bearer {apikey}"}
    if not instrument_name and not instrument_id:
        raise ValueError
    
    if instrument_id:
        print("Using Instrument ID to find Instument")
        get_endpt = f"{crucible_api_url}/instruments?id={instrument_id}"
        found_inst = requests.get(url = get_endpt, headers = auth_header).json()

    else:
        get_endpt = f"{crucible_api_url}/instruments?instrument_name={instrument_name}"
        found_inst = requests.get(url = get_endpt, headers = auth_header).json()

    if len(found_inst) > 0:
        return found_inst[-1]
    else:
        return None


def get_or_add_instrument(crucible_api_url,
                          apikey, 
                          instrument_name,
                          creation_location = None,
                          instrument_owner = None):

    auth_header = {"Authorization":f"Bearer {apikey}"}
    found_inst = get_instrument(crucible_api_url, apikey, instrument_name)

    if found_inst:
        return found_inst

    # should really just make these fields nullable
    if not instrument_owner:
        instrument_owner = "undefined"
        
    if not creation_location:
        creation_location = ""
        
    new_instrum = {"instrument_name": instrument_name,
                   "location": creation_location,
                   "owner": instrument_owner}
    
    post_endpt = f"{crucible_api_url}/instruments"
    instrument = requests.post(url = post_endpt, 
                                json = new_instrum, 
                                headers = auth_header).json()
    return(instrument)


def get_sample(crucible_api_url, apikey, sample_id):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/samples/{sample_id}"

    sample = requests.get(url=endpt, headers = auth_header)
    return sample

def list_samples(crucible_api_url, apikey, **kwargs):
    auth_header = {"Authorization": f"Bearer {apikey}"}
    endpt = f"{crucible_api_url}/samples"
    samples = requests.get(url=endpt, headers = auth_header, params = kwargs)
    return samples
    

def add_sample(crucible_api_url,
               apikey,
               sample_name,
               sample_description,
               sample_creation_date = None,
               sample_owner_orcid = None,
               owner_id = None):

    sample_info = {"sample_name": sample_name, 
                   "owner_orcid": sample_owner_orcid,
                   "owner_user_id": owner_id,
                   "description": sample_description,
                   "date_created": sample_creation_date
                  }
    
    endpt = f"{crucible_api_url}/samples"
    auth_header = {"Authorization":f"Bearer {apikey}"}
    new_samp = requests.post(endpt,
                            headers=auth_header,
                            json = sample_info)
    return new_samp

def add_dataset_to_sample(crucible_api_url, apikey, sample_id, dataset_id):
    ''' 
    might make more sense to have this function add an actual Dataset object to a sample
    then return all the datasets associated with that sample...

    then have reverse function and show all samples for a dataset
    '''
    endpt = f"{crucible_api_url}/datasets/{dataset_id}/samples/{sample_id}"
    auth_header = {"Authorization":f"Bearer {apikey}"}
    new_link = requests.post(endpt, headers=auth_header)
    return new_link



def add_project(project_info, crucible_api_url, apikey):
    endpt = f"{crucible_api_url}/projects"
    auth_header = {"Authorization":f"Bearer {apikey}"}
    # TODO: add checks for project info fields / validate
    new_prop = requests.post(endpt,
                            headers=auth_header,
                            json = project_info)
    return new_prop


def add_user(crucible_api_url, apikey, user_info):
    endpt = f"{crucible_api_url}/users"
    auth_header = {"Authorization":f"Bearer {apikey}"}
    user_projects = user_info.pop("projects")
    
    new_user = requests.post(endpt, 
                             headers = auth_header, 
                             json = {"user_info": user_info,
                                     "project_ids": user_projects})
    return(new_user)


def get_or_add_user(orcid, get_user_info_function, crucible_api_url, apikey, **kwargs):
    user = get_crucible_user(orcid, crucible_api_url, apikey)
    if user:
        return user
    
    user_info = get_user_info_function(orcid, **kwargs)
    if user_info:
        user = add_user(crucible_api_url, apikey, user_info)
        return(user)
    else:
        raise ValueError(f"User info for {orcid} not found in database or using the get_user_info_func")


def get_or_add_crucible_project(crucible_project_id, get_project_info_func, crucible_api_url, apikey, **kwargs):
    proj = get_crucible_project(crucible_project_id, crucible_api_url, apikey)
    if proj:
        return proj
    
    proj_info = get_project_info_func(crucible_project_id, **kwargs)
    if proj_info:
        proj = add_project(proj_info, crucible_api_url, apikey)
        return proj
    else:
        raise ValueError(f"Project info for {crucible_project_id} not found in database or using the provided get_project_info_func")


# ==== Main utility for instrument integration
def build_new_dataset_from_json(crucible_api_url, 
                                apikey, 
                                dataset_name: Optional[str] = None,
                                unique_id: Optional[str] = None, 
                                public: Optional[str] = False,
                                owner_orcid: Optional[str] = None,
                                owner_user_id: Optional[int] = None,
                                project_id: Optional[str] = None,
                                instrument_name: Optional[str] = None,
                                instrument_id: Optional[int] = None,
                                measurement: Optional[str] = None, 
                                session_name: Optional[str] = None,
                                creation_time:Optional[str] = None,
                                data_format: Optional[str] = None, 
                                scientific_metadata: Optional[dict] = None,
                                comments: Optional[str] = None,
                                keywords=[], 
                                get_user_info_function = None, 
                                **kwargs):
    # get owner_id if orcid provided
    if owner_orcid is not None:
        owner = get_or_add_user(owner_orcid, get_user_info_function, crucible_api_url, apikey, **kwargs)
        owner_user_id = owner['id']
    
    # get instrument_id if instrument_name provided
    if instrument_name is not None:
        instrument = get_or_add_instrument(crucible_api_url, apikey, instrument_name)
        instrument_id = instrument['id']

    # create the dataset with available metadata
    dataset = { "unique_id": unique_id,
                "dataset_name": dataset_name,
                "public": public,
                "owner_user_id": owner_user_id,
                "owner_orcid": owner_orcid,
                "project_id": project_id,
                "instrument_id": instrument_id,
                "measurement,": measurement, 
                "session_name": session_name,
                "creation_time": creation_time,
                "data_format": data_format}
    
    clean_dataset = {k: v for k, v in dataset.items() if v is not None}


    endpt = f"{crucible_api_url}/datasets"
    auth_header = {"Authorization":f"Bearer {apikey}"}
    new_ds_record = requests.post(url=endpt, 
                           json = clean_dataset, 
                           headers = auth_header)
    if new_ds_record:
        new_ds_record = new_ds_record.json()
        
    dsid = new_ds_record['unique_id']
    print(f"{dsid=}")
    
    # add scimd
    if scimd is not None:
        endpt = f"{crucible_api_url}/datasets/{dsid}/scientific_metadata"
        scimd = requests.post(url = endpt, 
                           json = scimd, 
                           headers = auth_header).json()
    else:
        scimd = None
        
    # add tags as keywords
    endpt = f"{crucible_api_url}/datasets/{dsid}/keywords"
    for kw in keywords:
        resp = requests.post(url = endpt, 
                    params = {"keyword":kw}, 
                    headers = auth_header).json()

    return {"created_record": new_ds_record,
            "scientific_metadata_record": scimd,
            "ingestion_request": ingest_req}

    
def build_new_dataset_from_file(crucible_api_url,
                                apikey,
                                files_to_upload: List[str], 
                                dataset_name: Optional[str] = None,
                                unique_id: Optional[str] = None, 
                                public: Optional[str] = False,
                                owner_orcid: Optional[str] = None,
                                owner_user_id: Optional[int] = None,
                                project_id: Optional[str] = None,
                                instrument_name: Optional[str] = None,
                                instrument_id: Optional[int] = None,
                                measurement: Optional[str] = None, 
                                session_name: Optional[str] = None,
                                creation_time:Optional[str] = None,
                                data_format: Optional[str] = None, 
                                source_folder: Optional[str] = None,
                                scientific_metadata: Optional[dict] = None,
                                keywords=[], 
                                get_user_info_function = None, 
                                ingestor = None,
                                **kwargs):
    '''
    This function will create a new dataset record in the Crucible Database for the file provided. 
    If an owner orcid is provided in the args, it will get the associated user ID. 
    If an instrument name is provided, it will get the associated instrument ID. 

    Order of operations: 
    An API call to create dataset will be made. 
        This API call will add a dataset record to the table with the provided metadata. 
        
    If scientific metadata was provided, a scientific metadata entry will be created
    and associated with the dataset ID

    If keywords were provided, they will be added. 

    Finally the upload API endpoint will be called with the file that was provided. 
    
    '''
    # get owner_id if orcid provided
    if owner_orcid is not None:
        owner = get_or_add_user(owner_orcid, get_user_info_function, crucible_api_url, apikey, **kwargs)
        owner_user_id = owner['id']
    
    # get instrument_id if instrument_name provided
    if instrument_name is not None:
        instrument = get_or_add_instrument(crucible_api_url, apikey, instrument_name)
        instrument_id = instrument['id']

    # create the dataset with available metadata
    main_file = files_to_upload[0]
    dataset = { "unique_id": unique_id,
                "dataset_name": dataset_name,
                "file_to_upload": os.path.join("api-uploads", main_file),
                "public": public,
                "owner_user_id": owner_user_id,
                "owner_orcid": owner_orcid,
                "project_id": project_id,
                "instrument_id": instrument_id,
                "measurement,": measurement, 
                "session_name": session_name,
                "creation_time": creation_time,
                "data_format": data_format, 
                "source_folder": source_folder}
    
    clean_dataset = {k: v for k, v in dataset.items() if v is not None}


    endpt = f"{crucible_api_url}/datasets"
    auth_header = {"Authorization":f"Bearer {apikey}"}
    new_ds_record = requests.post(url=endpt, 
                                  json = clean_dataset, 
                                  headers = auth_header)
    if new_ds_record:
        new_ds_record = new_ds_record.json()
        
    dsid = new_ds_record['unique_id']
    print(f"{dsid=}")
    
    # add comments as scimd
    if scientific_metadata is not None:
        endpt = f"{crucible_api_url}/datasets/{dsid}/scientific_metadata"
        scimd = requests.post(url = endpt, 
                           json = scientific_metadata, 
                           headers = auth_header).json()
    else:
        scimd = None
        
    # add tags as keywords
    endpt = f"{crucible_api_url}/datasets/{dsid}/keywords"
    for kw in keywords:
        resp = requests.post(url = endpt, 
                    params = {"keyword":kw}, 
                    headers = auth_header).json()
        
    # Send the file as bytes if small enough
    use_upload_endpoint = True
    for f in files_to_upload:
        if os.path.getsize(f) < 1e8:
            continue
        else:
            use_upload_endpoint = False
            break
            
    if use_upload_endpoint:
        endpt = f"{crucible_api_url}/datasets/{dsid}/upload"
        
        for f in files_to_upload:
            file_payload = [create_file_payload(f) for f in files_to_upload]
            upload_req = requests.post(url = endpt, 
                                       headers = auth_header,
                                       files = file_payload)

        associated_files = files_to_upload.copy()
        associated_files.pop(0)
        print(f"{associated_files=}")
        for afp in associated_files:
            af = {"filename": os.path.join("api-uploads", afp), 
                  "size": os.path.getsize(afp),
                  "sha256_hash": checkhash(afp)
                 }
            out = add_associated_file(crucible_api_url, apikey, dsid, af)
            print(f"add af out {out}")

        
        endpt = f"{crucible_api_url}/datasets/{dsid}/ingest"
        ingest_req = requests.post(url = endpt,
                                   params = {"file_to_upload": os.path.join("api-uploads", main_file),
                                             "ingestion_class": ingestor},
                                   headers = auth_header)
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
                  "sha256_hash": checkhash(afp)
                 }
            add_associated_file(crucible_api_url, apikey, dsid, af)

        
        endpt = f"{crucible_api_url}/datasets/{dsid}/ingest"
        main_file_path = os.path.join("large-files/", main_file)
        ingest_req = requests.post(url = endpt,
                                   params = {"file_to_upload": main_file_path,"ingestion_class": ingestor},
                                   headers = auth_header)

    return {"created_record": new_ds_record,
            "scientific_metadata_record": scimd,
            "ingestion_request": ingest_req}


def create_file_payload(file_to_upload):
    file_obj = ('files', (file_to_upload, open(file_to_upload, 'rb'), 'text/plain'))
    return(file_obj)


def add_associated_file(crucible_api_url, apikey, dsid, af):
    res = requests.post(url =  f"{crucible_api_url}/datasets/{dsid}/associated_files", 
            json = af, 
            headers = {"Authorization":f"Bearer {apikey}"})
    print(res.content)














'''
Make These!


# send the data
ds = requests.patch(url=f"{crucible_api_url}/datasets/{ig.unique_id}", headers = {"Authorization":f"Bearer {apikey}"}, json = D)
print(f"UPDATED DS: {ds.json()=}")


# this all additive so OK from database perspective
i = 0
for thumbnail in thumbnails:
    i+=1
    res = requests.post(url =  f"{crucible_api_url}/datasets/{dsid}/thumbnails", 
            json = {"thumbnail_b64str":thumbnail["thumbnail"], "thumbnail_name":thumbnail['caption']}, 
            headers = {"Authorization":f"Bearer {apikey}"})
    res.content
print(f"Thumbnail update complete. Added {i} thumbnails")

i = 0
for k,v in associated_files.items():
    i+=1
    print({"filename": k, "size":v['size'], "sha256_hash":v['sha256_hash']})
    res = requests.post(url =  f"{crucible_api_url}/datasets/{dsid}/associated_files", 
            json = {"filename": k, "size":v['size'], "sha256_hash":v['sha256_hash']}, 
            headers = {"Authorization":f"Bearer {apikey}"})
    print(res.content)
print(f"Associated File update complete. Added {i} associated files.")


for kw in keywords:
    res = requests.post(url =  f"{crucible_api_url}/datasets/{dsid}/keywords", 
            params = {"keyword":kw}, 
            headers = {"Authorization":f"Bearer {apikey}"})
    print(res.content)
print(f"Keyword addition complete Added these keywords: {keywords}")


# metadata dictionary
res = requests.patch(url = f"{crucible_api_url}/datasets/{dsid}/scientific_metadata", 
                    json = md, 
                    headers = {"Authorization":f"Bearer {apikey}"})
print(res.content)

return(ig,  storage_bucket)


'''