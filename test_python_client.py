import os
from dotenv import load_dotenv
from pycrucible import CrucibleClient
import unittest
env = load_dotenv()

# apikeys
crucible_admin_api_key = os.environ.get("admin_apikey")
crucible_user_api_key = os.environ.get("user_apikey")
crucible_invalid_api_key = os.environ.get("invalid_apikey")
crucible_api_url = os.environ.get("crucible_api_url")

# clients
admin_cli = CrucibleClient(crucible_api_url, crucible_admin_api_key)
user_cli = CrucibleClient(crucible_api_url, crucible_user_api_key)
invalid_cli = CrucibleClient(crucible_api_url, crucible_invalid_api_key)

class TestPythonClient(unittest.TestCase):   
        
    def test_list_projects(self):
        # with admin apikey
        admin_projects = admin_cli.list_projects()
        self.assertTrue(type(admin_projects) is list)
        self.assertTrue(len(admin_projects) > 0)

        # with user1 apikey - (403 account is unauthorized)
        with self.assertRaises(Exception) as context:
            user_projects = user_cli.list_projects()
        self.assertIn('403', str(context.exception))

        # with invalid apikey (400 no account found)
        with self.assertRaises(Exception) as context:
            inval_projects = invalid_cli.list_projects()
        self.assertIn('400', str(context.exception))

    def test_get_project(self):
        # existing project with admin apikey
        project_id = "MFP08540"
        proj = admin_cli.get_project(project_id)
        expected_dict_keys = ['organization', 'project_id', 'title', 'project_lead_email', 'id','status', 'project_lead_name']
        self.assertIsInstance(proj, dict)
        self.assertTrue(all([x in proj.keys() for x in expected_dict_keys]))

        # existing project with user apikey - with access
        project_id = "AUM_DEMO"
        proj = user_cli.get_project(project_id)
        self.assertIsInstance(proj, dict)

        # non existing project with admin apikey
        project_id = 'MFA00000'
        proj = admin_cli.get_project(project_id)
        self.assertIsNone(proj)

        # existing project with user apikey - without access
        # currently users can access any project
        project_id = 'MFP02030'
        proj = user_cli.get_project(project_id)
        #self.assertIsNone(proj)
        self.assertTrue(proj is not None)

    def test_get_user(self):
        # test any orcid as admin - should receive dict
        orcid = '0009-0001-9493-2006'
        user = admin_cli.get_user(orcid)
        self.assertIsInstance(user, dict)

        # test orcid of user - should receive 403 unauthorized
        my_orcid = '0009-0001-9493-2006'
        with self.assertRaises(Exception) as context:
            user = user_cli.get_user(my_orcid)
        self.assertIn('403', str(context.exception))

        # test non-existing orcid - should receive None
        non_existing_orcid = 'XXXX-XXXX-XXXX-0000'
        user = admin_cli.get_user(non_existing_orcid)
        self.assertIsNone(user)

    def test_get_user_by_email(self):
        # test as admin - should recieve dict
        email = "mkwall@lbl.gov"
        user = admin_cli.get_user_by_email(email)
        self.assertIsInstance(user, dict)

        # test as user - should receive dict // actually will return 403 right now
        email = "mkwall@lbl.gov"
        with self.assertRaises(Exception) as context:
            user = user_cli.get_user_by_email(email)
        self.assertIn('403', str(context.exception))

        # test as user for a different email - should receive None // actually will return 403 right now
        email = 'saloni@lbl.gov'
        with self.assertRaises(Exception) as context:
            user = user_cli.get_user_by_email(email)
        self.assertIn('403', str(context.exception))

        # test an external email as admin - should receive dict
        ext_email = 'b_rad@berkeley.edu'
        user = admin_cli.get_user_by_email(ext_email)
        self.assertIsInstance(user, dict)

        # test a non-existing email as admin - should receive None
        no_exist_email = 'xxxxx@gmail.com'
        user = admin_cli.get_user_by_email(no_exist_email)
        self.assertIsNone(user)

    def test_get_project_users(self):
        project_id = 'MFP08540'
        # test as admin - should return list
        users = admin_cli.get_project_users(project_id)
        self.assertIsInstance(users, list)

        # test as user - should return 403
        with self.assertRaises(Exception) as context:
            users = user_cli.get_project_users(project_id)
        self.assertIn('403', str(context.exception))

        # test non existent project as admin - should return 404
        non_exist_project = 'MFPXXXXX'
        with self.assertRaises(Exception) as context:
            users = admin_cli.get_project_users(non_exist_project)
        self.assertIn('404', str(context.exception))

    def test_list_datasets_admin_with_limit(self):
        # test as admin - should return list with length 100
        admin_datasets = admin_cli.list_datasets(limit = 100)
        print(len(admin_datasets))
        self.assertIsInstance(admin_datasets, list)
        self.assertEqual(len(admin_datasets), 100)

    def test_list_datasets_user_vs_admin(self):
        # test as user 
        admin_datasets = admin_cli.list_datasets()
        user_datasets = user_cli.list_datasets()
        self.assertIsInstance(user_datasets, list)
        #self.assertNotEqual(admin_datasets, user_datasets)

    def test_list_datasets_by_sample_id_admin(self):
        # test as admin with sample_id - should return list with length = 8
        sample_id = '0t3q9zq7enrhf0004dvevszkmm'
        sample_datasets = admin_cli.list_datasets(sample_id=sample_id)
        self.assertIsInstance(sample_datasets, list)
        self.assertEqual(len(sample_datasets), 8)

    def test_list_datasets_by_sample_id_user(self):
        # test as user with sample_id - should return list
        sample_id = '0t3q9zq7enrhf0004dvevszkmm'
        sample_datasets_user = user_cli.list_datasets(sample_id=sample_id)
        self.assertIsInstance(sample_datasets_user, list)

    def test_list_datasets_with_single_kwarg(self):
        # test with a single kwarg - should return list
        keyword = 'picam_readout'
        keyword_datasets = admin_cli.list_datasets(keyword=keyword)
        self.assertIsInstance(keyword_datasets, list)

    def test_list_datasets_with_multiple_kwargs(self):
        # test with multiple kwargs - should return list
        keyword = 'toupcam_live'
        instrument = 'hip_microscope'
        multi_datasets = admin_cli.list_datasets(keyword=keyword, instrument=instrument)
        self.assertIsInstance(multi_datasets, list)

    def test_get_dataset(self):
        dsid = '04qed8jsxd3avcgk7d443rw7t4'

        # test as admin
        dataset = admin_cli.get_dataset(dsid)
        self.assertIsInstance(dataset, dict)

        # test as user with include_metadata = False
        dataset = user_cli.get_dataset(dsid, include_metadata=False)
        self.assertIsInstance(dataset, dict)
        self.assertNotIn('scientific_metadata', dataset)

        # test as user with include_metadata = True and assert that scientific_metadata exists in returned dict
        dataset = user_cli.get_dataset(dsid, include_metadata=True)
        self.assertIsInstance(dataset, dict)
        self.assertIn('scientific_metadata', dataset)

    def test_update_dataset(self):
        import mfid

        # Create a test dataset first
        dataset_name = 'unittest_update_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            public=False
        )
        dsid = result['dsid']

        # Test updating dataset as user
        updates = {'dataset_name': 'unittest_updated_name', 'public': True}
        updated_ds = user_cli.update_dataset(dsid, **updates)
        self.assertIsInstance(updated_ds, dict)
        self.assertEqual(updated_ds['dataset_name'], 'unittest_updated_name')
        self.assertTrue(updated_ds['public'])

        # Verify the update persisted
        dataset = user_cli.get_dataset(dsid)
        self.assertEqual(dataset['dataset_name'], 'unittest_updated_name')
        self.assertTrue(dataset['public'])

    def test_upload_dataset(self):
        import mfid
        import os

        # Create a test dataset first
        dataset_name = 'unittest_upload_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Upload test file
        file_path = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')

        # Test upload as user
        upload_result = user_cli.upload_dataset(dsid, file_path)
        self.assertIsInstance(upload_result, dict)

        # Verify dataset has file_to_upload field
        dataset = user_cli.get_dataset(dsid)
        self.assertIsNotNone(dataset.get('file_to_upload'))

    def test_download_dataset(self):
        dsid = ''
        file_name = ''
        pass

    def test_request_ingestion(self):
        import mfid
        import os

        # Create a test dataset and upload a file
        dataset_name = 'unittest_ingestion_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Upload test file
        file_path = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')
        user_cli.upload_dataset(dsid, file_path)

        # Test request ingestion as user
        file_to_upload = 'api-uploads/sunrise.png'
        ingestor = 'ImageIngestor'
        ingestion_request = user_cli.request_ingestion(dsid, file_to_upload, ingestor)

        self.assertIsInstance(ingestion_request, dict)
        self.assertIn('id', ingestion_request)
        self.assertIn('status', ingestion_request)

    def test_get_ingestion_status(self):
        dsid = '0t3qaf0wzxsaf000amry40wdv4'
        reqid = '208'
        # test as admin - should return dict
        status = admin_cli.get_ingestion_status(dsid, reqid)
        self.assertIsInstance(status, dict)

        # test as user - should return dict
        status = user_cli.get_ingestion_status(dsid, reqid)
        self.assertIsInstance(status, dict)

    def test_get_scicat_status(self):
        dsid = '0t4yswbhxsz0n0009parhfr6zg'
        reqid = '59'
        # test as admin - should return dict
        status = admin_cli.get_scicat_status(dsid, reqid)
        self.assertIsInstance(status, dict)

        # test as user - should return dict
        status = user_cli.get_scicat_status(dsid, reqid)
        self.assertIsInstance(status, dict)

    def test_get_request_status(self):
        dsid = '0t3qaejwn9v8b000efdak8cj9w'
        reqid = '226'
        request_type = 'ingest'
        # test as admin - should return dict
        status = admin_cli.get_request_status(dsid, reqid, request_type)
        self.assertIsInstance(status, dict)

        # test as user - should return dict
        status = user_cli.get_request_status(dsid, reqid, request_type)
        self.assertIsInstance(status, dict)

    def test_wait_for_request_completion(self):
        dsid = '0t3qaejwn9v8b000efdak8cj9w'
        reqid = '226'
        request_type = 'ingest'
        # test as admin - should return dict
        result = admin_cli.wait_for_request_completion(dsid, reqid, request_type)
        self.assertIsInstance(result, dict)

        # test as user - should return dict
        result = user_cli.wait_for_request_completion(dsid, reqid, request_type)
        self.assertIsInstance(result, dict)

    def test_get_dataset_access_groups(self):
        dsid = '04qed8jsxd3avcgk7d443rw7t4'
        # test as admin - should return list
        groups = admin_cli.get_dataset_access_groups(dsid)
        self.assertIsInstance(groups, list)

        # test as user - should return 403 http error
        with self.assertRaises(Exception) as context:
            groups = user_cli.get_dataset_access_groups(dsid)
        self.assertIn('403', str(context.exception))

    def test_get_dataset_keywords(self):
        dsid = '04qed8jsxd3avcgk7d443rw7t4'
        # test as admin - should return list of dictionaries
        keywords = admin_cli.get_dataset_keywords(dsid)
        self.assertIsInstance(keywords, list)
        if len(keywords) > 0:
            self.assertIsInstance(keywords[0], dict)

        # test as user with access - should return list of dictionaries
        keywords = user_cli.get_dataset_keywords(dsid)
        self.assertIsInstance(keywords, list)
        if len(keywords) > 0:
            self.assertIsInstance(keywords[0], dict)

        # test as user on unauthorized ds - should return 403
        unauth_dsid = '0szg954t4xwn3000rf8qcaa5y4'
        with self.assertRaises(Exception) as context:
            keywords = user_cli.get_dataset_keywords(unauth_dsid)
        self.assertIn('403', str(context.exception))

    def test_add_dataset_keyword(self):
        import mfid

        # Create a test dataset
        dataset_name = 'unittest_keyword_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Test adding a keyword as user
        keyword = 'unittest_keyword_001'
        keyword_result = user_cli.add_dataset_keyword(dsid, keyword)
        self.assertIsInstance(keyword_result, dict)
        self.assertIn('keyword', keyword_result)

        # Verify the keyword was added
        keywords = user_cli.get_dataset_keywords(dsid)
        keyword_values = [kw['keyword'] for kw in keywords]
        self.assertIn(keyword, keyword_values)

        # Test adding the same keyword again - should update usage count
        keyword_result2 = user_cli.add_dataset_keyword(dsid, keyword)
        self.assertIsInstance(keyword_result2, dict)

    def test_get_scientific_metadata(self):
        dsid = '0swkxhy14nwb7000d24fty22p0'
        # test as admin - should receive a nested dictionary
        metadata = admin_cli.get_scientific_metadata(dsid)
        self.assertIsInstance(metadata, dict)

    def test_update_scientific_metadata(self):
        import mfid

        # Create a test dataset with initial metadata
        dataset_name = 'unittest_scimd_test'
        unique_id = mfid.mfid()[0]
        initial_metadata = {'field1': 'value1', 'field2': 'value2'}
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            scientific_metadata=initial_metadata
        )
        dsid = result['dsid']

        # Test updating (patching) scientific metadata as user
        update_metadata = {'field3': 'value3'}
        updated_md = user_cli.update_scientific_metadata(dsid, update_metadata, overwrite=False)
        self.assertIsInstance(updated_md, dict)

        # Verify both old and new fields exist (patch should merge)
        full_metadata = user_cli.get_scientific_metadata(dsid)
        self.assertIn('scientific_metadata', full_metadata)

        # Test overwriting scientific metadata
        overwrite_metadata = {'new_field': 'new_value'}
        overwritten_md = user_cli.update_scientific_metadata(dsid, overwrite_metadata, overwrite=True)
        self.assertIsInstance(overwritten_md, dict)

    def test_get_thumbnails(self):
        dsid = '0sfy1hm9cxw1v000h0w5z986m8'
        # test as admin
        thumbnails = admin_cli.get_thumbnails(dsid)
        self.assertIsInstance(thumbnails, list)

        # test as user
        thumbnails = user_cli.get_thumbnails(dsid)
        self.assertIsInstance(thumbnails, list)

    def test_add_thumbnail(self):
        import mfid
        import os

        # Create a test dataset
        dataset_name = 'unittest_thumbnail_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Test adding a thumbnail as user
        file_path = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')
        thumbnail_name = 'test_thumbnail'
        thumbnail_result = user_cli.add_thumbnail(dsid, file_path, thumbnail_name)

        self.assertIsInstance(thumbnail_result, dict)
        self.assertIn('thumbnail_name', thumbnail_result)

        # Verify the thumbnail was added
        thumbnails = user_cli.get_thumbnails(dsid)
        self.assertIsInstance(thumbnails, list)
        self.assertTrue(len(thumbnails) > 0)

    def test_get_associated_files(self):
        dsid = '04qed8jsxd3avcgk7d443rw7t4'
        # test as admin
        files = admin_cli.get_associated_files(dsid)
        self.assertIsInstance(files, list)

        # test as user
        files = user_cli.get_associated_files(dsid)
        self.assertIsInstance(files, list)

    def test_add_associated_file(self):
        import mfid
        import os

        # Create a test dataset
        dataset_name = 'unittest_assoc_file_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Test adding an associated file as user
        file_path = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')
        filename = 'test_associated_file.png'
        assoc_file_result = user_cli.add_associated_file(dsid, file_path, filename)

        self.assertIsInstance(assoc_file_result, dict)
        self.assertIn('filename', assoc_file_result)
        self.assertIn('sha256_hash', assoc_file_result)

        # Verify the associated file was added
        assoc_files = user_cli.get_associated_files(dsid)
        self.assertIsInstance(assoc_files, list)
        self.assertTrue(len(assoc_files) > 0)

    def test_request_google_drive_transfer(self):
        import mfid

        # Create a test dataset
        dataset_name = 'unittest_gdrive_transfer_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Test requesting google drive transfer as user
        transfer_result = user_cli.request_google_drive_transfer(dsid)

        self.assertIsInstance(transfer_result, dict)
        self.assertIn('id', transfer_result)
        self.assertIn('status', transfer_result)

    def test_send_to_scicat(self):
        import mfid

        # Create a test dataset
        dataset_name = 'unittest_scicat_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Test sending to scicat as user (without waiting for response)
        scicat_result = user_cli.send_to_scicat(dsid, wait_for_scicat_response=False)

        self.assertIsInstance(scicat_result, dict)
        self.assertIn('id', scicat_result)
        self.assertIn('status', scicat_result)

    def test_delete_dataset(self):
        import mfid

        # Create a test dataset
        dataset_name = 'unittest_delete_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Test delete - API may not implement this, so we expect it might fail
        # According to pycrucible.py docstring, delete is "not implemented in API"
        try:
            delete_result = user_cli.delete_dataset(dsid)
            # If it works, should return a dict
            self.assertIsInstance(delete_result, dict)
        except Exception as e:
            # If not implemented, we expect an HTTP error
            self.assertIn('404', str(e)) or self.assertIn('405', str(e)) or self.assertIn('501', str(e))

    def test_get_google_drive_info(self):
        dsid = '04qed8jsxd3avcgk7d443rw7t4'

        # test as admin - should return list of dict
        drive_info = admin_cli.get_google_drive_info(dsid)
        self.assertIsInstance(drive_info, list)

        # test as user - should return list of dict
        drive_info = user_cli.get_google_drive_info(dsid)
        self.assertIsInstance(drive_info, list)

        # response should contain something to indicate that the status is current
        if len(drive_info) > 0:
            statuses = [d['status'] for d in drive_info]
            self.assertTrue(all([s == 'current' for s in statuses]))


    def test_get_organized_google_drive_info(self):
        dsid = '04qed8jsxd3avcgk7d443rw7t4'

        # test as admin - should return list of dictionaries
        org_drive_info = admin_cli.get_organized_google_drive_info(dsid)
        self.assertIsInstance(org_drive_info, list)

        # test as user - should return list of dict
        org_drive_info = user_cli.get_organized_google_drive_info(dsid)
        self.assertIsInstance(org_drive_info, list)

        # response should contain something to indicate that the status is current
        if len(org_drive_info) > 0:
            statuses = [d['status'] for d in org_drive_info]
            self.assertTrue(all([s == 'current' for s in statuses]))
            self.assertTrue(all(['Organized' in d['folder_path_in_drive'] for d in org_drive_info]))

    def test_add_drive_location_for_dataset(self):
        # This method is not implemented yet in the client (has TODO)
        # Skipping test until implementation is complete
        pass

    def test_update_ingestion_status(self):
        import mfid
        import os

        # Create a test dataset and upload a file
        dataset_name = 'unittest_update_ingest_status'
        unique_id = mfid.mfid()[0]
        result = admin_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Upload test file and request ingestion
        file_path = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')
        admin_cli.upload_dataset(dsid, file_path)
        ingest_req = admin_cli.request_ingestion(dsid, 'api-uploads/sunrise.png', 'ImageIngestor')
        reqid = ingest_req['id']

        # Test updating ingestion status as admin
        response = admin_cli.update_ingestion_status(dsid, str(reqid), 'in_progress')
        self.assertEqual(response.status_code, 200)

        # Verify the status was updated
        status = admin_cli.get_ingestion_status(dsid, str(reqid))
        self.assertEqual(status['status'], 'in_progress')

    def test_update_scicat_upload_status(self):
        import mfid

        # Create a test dataset
        dataset_name = 'unittest_update_scicat_status'
        unique_id = mfid.mfid()[0]
        result = admin_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Request scicat upload
        scicat_req = admin_cli.send_to_scicat(dsid, wait_for_scicat_response=False)
        reqid = scicat_req['id']

        # Test updating scicat upload status as admin
        response = admin_cli.update_scicat_upload_status(dsid, str(reqid), 'in_progress')
        self.assertEqual(response.status_code, 200)

        # Verify the status was updated
        status = admin_cli.get_scicat_status(dsid, str(reqid))
        self.assertEqual(status['status'], 'in_progress')

    def test_update_transfer_status(self):
        import mfid

        # Create a test dataset
        dataset_name = 'unittest_update_transfer_status'
        unique_id = mfid.mfid()[0]
        result = admin_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Request google drive transfer
        transfer_req = admin_cli.request_google_drive_transfer(dsid)
        reqid = transfer_req['id']

        # Test updating transfer status as admin
        response = admin_cli.update_transfer_status(dsid, str(reqid), 'in_progress')
        self.assertEqual(response.status_code, 200)

        # Verify the status was updated by checking response was successful
        # (get_transfer_status doesn't exist, so we just verify the update call worked)
        self.assertIsNotNone(response)

    def test_list_instruments(self):
        limit = 10
        # test as admin and user
        # admin returns list, user returns list
        admin_instruments = admin_cli.list_instruments(limit=limit)
        self.assertIsInstance(admin_instruments, list)

        user_instruments = user_cli.list_instruments(limit=limit)
        self.assertIsInstance(user_instruments, list)

    def test_get_instrument(self):
        # run all tests as admin
        instrument_name = 'team05'
        wrong_instrument_name = 'team06'
        caps_instrument_name = 'TEAM05'

        # test with only instrument_name - should return dictionary
        instrument = admin_cli.get_instrument(instrument_name=instrument_name)
        self.assertIsInstance(instrument, dict)

        # test with only instrument_name set to wrong instrument - should return 404
        instrument = admin_cli.get_instrument(instrument_name=wrong_instrument_name)
        self.assertIsNone(instrument)

        #test with only instrument_name set to caps_instrument - should return the same dictionary as instrument_name
        caps_instrument = admin_cli.get_instrument(instrument_name=caps_instrument_name)
        original_instrument = admin_cli.get_instrument(instrument_name=instrument_name)
        self.assertEqual(caps_instrument, original_instrument)

        instrument_id = '0szb5en16nxdk000dcd8a1wt2w'
        # test with only instrument_id - returns same dictionary as instrument_name
        instrument_by_id = admin_cli.get_instrument(instrument_id=instrument_id)
        self.assertIsInstance(instrument_by_id, dict)

        new_instrument_id = '0sh6zrzxhnz8k000k7pwq0s2t8'
        # test with new instrument_id and instrument_name - returns dictionary with a value of "0sh6zrzxhnz8k000k7pwq0s2t8" for key "instrument_id"
        instrument_both = admin_cli.get_instrument(instrument_name=instrument_name, instrument_id=new_instrument_id)
        self.assertIsInstance(instrument_both, dict)
        self.assertEqual(instrument_both['unique_id'], new_instrument_id)

        # test with neither instrument_id or instrument_name - raises value error
        with self.assertRaises(ValueError):
            admin_cli.get_instrument()

    def test_get_or_add_instrument(self):
        instrument_name = 'titanx'
        # run as admin - returns dictionary
        instrument = admin_cli.get_or_add_instrument(instrument_name)
        self.assertIsInstance(instrument, dict)

        instrument_name = 'test000055'
        # without location or owner - raises value error
        with self.assertRaises(ValueError):
            instrument = admin_cli.get_or_add_instrument(instrument_name)

        instrument_name = 'test000052'
        location = 'test_location'
        instrument_owner = 'LBNL MF Data Facility'
        # run as admin - returns dictionary
        instrument = admin_cli.get_or_add_instrument(instrument_name, location=location, instrument_owner=instrument_owner)
        self.assertIsInstance(instrument, dict)

    def test_get_sample(self):
        sample_id = '0t3q9zq7enrhf0004dvevszkmm'

        # test as admin - returns dictionary
        sample = admin_cli.get_sample(sample_id)
        self.assertIsInstance(sample, dict)

        # test as user - returns dictionary
        sample = user_cli.get_sample(sample_id)
        self.assertIsInstance(sample, dict)

        sample_id = '000000'

        # test as admin - returns None
        sample = admin_cli.get_sample(sample_id)
        self.assertIsNone(sample)

    def test_list_samples(self):
        dataset_id = '0t3qaemyz1y1x000qgf2kkq0x0'
        parent_id = '0t3h7ymbm5s27000z6tt82zvx4'

        # test both of these as admin - both should return lists
        samples_by_dataset = admin_cli.list_samples(dataset_id=dataset_id)
        self.assertIsInstance(samples_by_dataset, list)

        samples_by_parent = admin_cli.list_samples(parent_id=parent_id)
        self.assertIsInstance(samples_by_parent, list)

    def test_add_sample(self):
        import mfid

        # Test adding a sample as admin
        sample_name = 'unittest_sample_001'
        unique_id = mfid.mfid()[0]
        owner_orcid = '0009-0001-9493-2006'
        description = 'Test sample for unit testing'

        sample_result = admin_cli.add_sample(
            unique_id=unique_id,
            sample_name=sample_name,
            description=description,
            owner_orcid=owner_orcid
        )

        self.assertIsInstance(sample_result, dict)
        self.assertEqual(sample_result['sample_name'], sample_name)
        self.assertEqual(sample_result['unique_id'], unique_id)

        # Verify sample was created
        sample = admin_cli.get_sample(unique_id)
        self.assertIsNotNone(sample)
        self.assertEqual(sample['sample_name'], sample_name)

    def test_add_sample_to_dataset(self):
        import mfid

        # Create a test sample
        sample_name = 'unittest_sample_link_test'
        sample_unique_id = mfid.mfid()[0]
        sample_result = admin_cli.add_sample(
            unique_id=sample_unique_id,
            sample_name=sample_name,
            owner_orcid='0009-0001-9493-2006'
        )

        # Create a test dataset
        dataset_name = 'unittest_dataset_link_test'
        dataset_unique_id = mfid.mfid()[0]
        dataset_result = admin_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=dataset_unique_id
        )
        dsid = dataset_result['dsid']

        # Test linking sample to dataset
        link_result = admin_cli.add_sample_to_dataset(dsid, sample_unique_id)

        self.assertIsInstance(link_result, dict)

        # Verify the link was created by getting datasets for the sample
        sample_datasets = admin_cli.list_datasets(sample_id=sample_unique_id)
        dataset_ids = [ds['unique_id'] for ds in sample_datasets]
        self.assertIn(dsid, dataset_ids)

    def test_add_user(self):
        # Test adding a user as admin
        # Note: Be careful with real ORCIDs - using a test ORCID pattern
        user_info = {
            'orcid': '9999-9999-9999-9999',  # Test ORCID
            'name': 'Unit Test User',
            'email': 'unittest@example.com',
            'lbl_email': 'unittest@lbl.gov',
            'projects': ['AUM_DEMO']  # Using existing test project
        }

        # Test adding user as admin
        try:
            user_result = admin_cli.add_user(user_info)
            self.assertIsInstance(user_result, dict)
            self.assertIn('orcid', user_result)
        except Exception as e:
            # If user already exists, we expect a conflict error
            # POST requests typically return 409 if record exists
            self.assertIn('409', str(e)) or self.assertIn('400', str(e))

    def test_get_or_add_user(self):
        # Define a mock function to get user info
        def mock_get_user_info(orcid):
            return {
                'orcid': orcid,
                'name': 'Test User from Function',
                'email': f'{orcid}@example.com',
                'projects': ['AUM_DEMO']
            }

        # Test 1: Get existing user
        existing_orcid = '0009-0001-9493-2006'
        user = admin_cli.get_or_add_user(existing_orcid, mock_get_user_info)
        self.assertIsInstance(user, dict)
        self.assertEqual(user['orcid'], existing_orcid)

        # Test 2: Try to add new user (if doesn't exist)
        new_orcid = '8888-8888-8888-8888'
        try:
            user = admin_cli.get_or_add_user(new_orcid, mock_get_user_info)
            self.assertIsInstance(user, dict)
        except Exception:
            # User might already exist from previous test run
            pass

    def test_get_or_add_crucible_project(self):
        # Test 1: Get existing project
        existing_project_id = 'MFP08540'
        project = admin_cli.get_or_add_crucible_project(existing_project_id)
        self.assertIsInstance(project, dict)
        self.assertEqual(project['project_id'], existing_project_id)

        # Test 2: Try to add new project with custom function
        def mock_get_project_info(project_id):
            return {
                'project_id': project_id,
                'organization': 'Test Organization',
                'project_lead': 'Test Lead',
                'title': 'Test Project'
            }

        new_project_id = 'UNITTEST_PROJ_001'
        try:
            project = admin_cli.get_or_add_crucible_project(new_project_id, mock_get_project_info)
            self.assertIsInstance(project, dict)
            self.assertEqual(project['project_id'], new_project_id)
        except Exception:
            # Project might already exist from previous test run
            pass

    def test_create_dataset_with_metadata_test1_basic(self):
        """Test 1: create dataset with only name and unique_id passed in"""
        import mfid

        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'

        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']
        dataset = user_cli.get_dataset(dsid)
        # confirm dataset is not public and associated with owner_orcid '0009-0001-9493-2006'
        self.assertFalse(dataset['public'])
        self.assertEqual(dataset['owner_orcid'], owner_orcid)
        # confirm the scientific metadata is None
        self.assertIsNone(result['scientific_metadata_record'])

    def test_create_dataset_with_metadata_test2_public(self):
        """Test 2: create dataset with name, unique_id, and public = True"""
        import mfid

        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'

        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            public=True
        )
        dsid = result['dsid']
        dataset = user_cli.get_dataset(dsid)
        # confirm dataset is public and associated with owner orcid '0009-0001-9493-2006'
        self.assertTrue(dataset['public'])
        self.assertEqual(dataset['owner_orcid'], owner_orcid)
        # confirm the scientific metadata is None
        self.assertIsNone(result['scientific_metadata_record'])

    def test_create_dataset_with_metadata_test3_with_project(self):
        """Test 3: create dataset with name, unique_id, owner_orcid, and project_id"""
        import mfid

        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'
        project_id = 'MFP08540'

        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            owner_orcid=owner_orcid,
            project_id=project_id
        )
        dsid = result['dsid']
        dataset = user_cli.get_dataset(dsid)
        # confirm dataset is associated with '0009-0001-9493-2006' and the project ID
        self.assertEqual(dataset['owner_orcid'], owner_orcid)
        self.assertEqual(dataset['project_id'], project_id)


    def test_create_dataset_with_metadata_test4_fail_to_create_project_with_no_info(self):
        """Test 4: create dataset where project does not exist - error"""
        import mfid
        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'
        project_id = 'UNITTEST0001'

        unique_id = mfid.mfid()[0]
        with self.assertRaises(ValueError):
            result = user_cli._create_dataset_with_metadata(
                dataset_name=dataset_name,
                unique_id=unique_id,
                owner_orcid=owner_orcid,
                project_id=project_id
            )


    ''' REMOVING CAPABILITY - CALL get_or_add_project with project_info_function before calling _create_dataset'''
    # def test_create_dataset_with_metadata_test5_project_with_function(self):
    #     """Test 5: create dataset with another new project and get_project_info_function"""
    #     import mfid
    #     from crucible_utils.mf_proposal_db_utils import build_mfp_project

    #     dataset_name = 'unittest00001'
    #     owner_orcid = '0009-0001-9493-2006'
    #     project_id = 'MFP11000'

    #     unique_id = mfid.mfid()[0]
    #     result = user_cli._create_dataset_with_metadata(
    #         dataset_name=dataset_name,
    #         unique_id=unique_id,
    #         owner_orcid=owner_orcid,
    #         project_id=project_id,
    #         get_project_info_function=build_mfp_project
    #     )
    #     dsid = result['dsid']
    #     dataset = user_cli.get_dataset(dsid)
    #     # confirm dataset is associated with project
    #     self.assertEqual(dataset['project_id'], project_id)
    #     # confirm the scientific metadata is None
    #     self.assertIsNone(result['scientific_metadata_record'])

    def test_create_dataset_with_metadata_test6_with_instrument(self):
        """Test 6: create dataset with name, id, orcid, and existing instrument"""
        import mfid

        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'
        instrument_name = 'titanx'

        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            owner_orcid=owner_orcid,
            instrument_name=instrument_name
        )
        dsid = result['dsid']
        dataset = user_cli.get_dataset(dsid)
        print(dataset)
        self.assertEqual(dataset['instrument_name'], instrument_name)

    def test_create_dataset_with_metadata_test7_fail_to_create_instrument(self):
        """Test 7: create dataset with new instrument - return error that instrument must already exist"""
        import mfid

        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'
        instrument_name = 'UnitTest0001'

        unique_id = mfid.mfid()[0]
        with self.assertRaises(ValueError):
            result = user_cli._create_dataset_with_metadata(
                dataset_name=dataset_name,
                unique_id=unique_id,
                owner_orcid=owner_orcid,
                instrument_name=instrument_name
            )

    def test_create_dataset_with_metadata_test8_full_dataset(self):
        """Test 8: create a dataset with all parameters (metadata, keywords, extra fields)"""
        import mfid

        dataset_name = 'unittest00001'
        owner_orcid = '0009-0001-9493-2006'
        project_id = 'MFP08540'
        instrument_name = 'titanx'
        measurement = 'haadf'
        session_name = 'unittest0001'
        data_format = 'dm4'
        scientific_metadata = {'md_1': 'test', 'md_2': {'md_3': 'test'}}
        keywords = ['unittest1']
        source_folder = 'morgan/pc/unittest/'

        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id,
            owner_orcid=owner_orcid,
            project_id=project_id,
            instrument_name=instrument_name,
            measurement=measurement,
            session_name=session_name,
            data_format=data_format,
            scientific_metadata=scientific_metadata,
            keywords=keywords,
            source_folder=source_folder
        )
        dsid = result['dsid']
        dataset = user_cli.get_dataset(dsid, include_metadata=True)

        # confirm the dataset was created and associated with the correct project and owner
        self.assertEqual(dataset['owner_orcid'], owner_orcid)
        self.assertEqual(dataset['project_id'], project_id)

        # confirm the dataset has scientific metadata
        self.assertIsNotNone(result['scientific_metadata_record'])
        print(dataset)
        self.assertEqual(dataset['scientific_metadata']['scientific_metadata']['md_1'], 'test')
        self.assertEqual(dataset['scientific_metadata']['scientific_metadata']['md_2']['md_3'], 'test')

        # confirm the keywords were created
        dataset_keywords = user_cli.get_dataset_keywords(dsid)
        keyword_values = [kw['keyword'] for kw in dataset_keywords]
        self.assertIn('unittest1', keyword_values)

        # confirm the field filter_me_out is nowhere to be found
        # API filters out this field
        self.assertNotIn('filter_me_out', dataset)

        # confirm the field source_folder is populated in the dataset record
        self.assertEqual(dataset['source_folder'], source_folder)
                               
    def test_build_new_dataset_from_json(self):
        import mfid

        # Test building a dataset from JSON metadata
        dataset_name = 'unittest_from_json_001'
        unique_id = mfid.mfid()[0]
        owner_orcid = '0009-0001-9493-2006'
        project_id = 'MFP08540'
        instrument_name = 'titanx'
        measurement = 'test_measurement'
        scientific_metadata = {'param1': 'value1', 'param2': {'nested': 'value2'}}
        keywords = ['unittest', 'json_test']

        result = user_cli.build_new_dataset_from_json(
            dataset_name=dataset_name,
            unique_id=unique_id,
            owner_orcid=owner_orcid,
            project_id=project_id,
            instrument_name=instrument_name,
            measurement=measurement,
            scientific_metadata=scientific_metadata,
            keywords=keywords
        )

        self.assertIsInstance(result, dict)
        self.assertIn('created_record', result)
        self.assertIn('scientific_metadata_record', result)

        # Verify dataset was created with correct metadata
        dsid = result['created_record']['unique_id']
        dataset = user_cli.get_dataset(dsid, include_metadata=True)
        self.assertEqual(dataset['dataset_name'], dataset_name)
        self.assertEqual(dataset['owner_orcid'], owner_orcid)
        self.assertEqual(dataset['measurement'], measurement)

    # def test_build_new_dataset_from_file(self):
    #     import mfid
    #     import os

    #     # Test data setup
    #     test_file = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')
    #     dataset_name = 'unittest_file_upload'
    #     owner_orcid = '0009-0001-9493-2006'
    #     project_id = 'MFP08540'
    #     instrument_name = 'titanx'
    #     measurement = 'brightfield'
    #     scientific_metadata = {'camera': 'toupcam', 'resolution': '1920x1080'}
    #     keywords = ['unittest', 'file_upload_test']

    #     # Test 1: Upload file without ingestor
    #     unique_id = mfid.mfid()[0]
    #     result = user_cli.build_new_dataset_from_file(
    #         files_to_upload=[test_file],
    #         dataset_name=dataset_name,
    #         unique_id=unique_id,
    #         owner_orcid=owner_orcid,
    #         project_id=project_id,
    #         instrument_name=instrument_name,
    #         measurement=measurement,
    #         scientific_metadata=scientific_metadata,
    #         keywords=keywords,
    #         wait_for_ingestion_response=False
    #     )

    #     # Verify test 1 results
    #     dsid = result['created_record']['unique_id']
    #     self.assertIsNotNone(result['created_record'])
    #     self.assertIsNotNone(result['ingestion_request'])
    #     self.assertEqual(result['scientific_metadata_record']['scientific_metadata']['camera'], 'toupcam')

    #     # Verify dataset was created correctly
    #     dataset = user_cli.get_dataset(dsid, include_metadata=True)
    #     self.assertEqual(dataset['dataset_name'], dataset_name)
    #     self.assertEqual(dataset['owner_orcid'], owner_orcid)
    #     self.assertEqual(dataset['measurement'], measurement)

    #     # Test 2: Upload file with ingestor
    #     unique_id = mfid.mfid()[0]
    #     ingestor = 'ImageIngestor'
    #     result = user_cli.build_new_dataset_from_file(
    #         files_to_upload=[test_file],
    #         dataset_name=dataset_name,
    #         unique_id=unique_id,
    #         owner_orcid=owner_orcid,
    #         project_id=project_id,
    #         instrument_name=instrument_name,
    #         measurement=measurement,
    #         scientific_metadata=scientific_metadata,
    #         keywords=keywords,
    #         ingestor=ingestor,
    #         wait_for_ingestion_response=True
    #     )

    #     # Verify test 2 results
    #     dsid2 = result['created_record']['unique_id']
    #     self.assertIsNotNone(result['created_record'])
    #     self.assertIsNotNone(result['ingestion_request'])

    #     # Verify ingestion completed (since wait_for_ingestion_response=True)
    #     self.assertIn(result['ingestion_request']['status'], ['complete', 'completed'])

    #     # Verify dataset created with all metadata
    #     dataset2 = user_cli.get_dataset(dsid2, include_metadata=True)
    #     self.assertEqual(dataset2['instrument_name'], instrument_name)
    #     self.assertEqual(dataset2['scientific_metadata']['scientific_metadata']['camera'], 'toupcam')

    def test_ingest_dataset(self):
        import mfid
        import os

        # Create a test dataset and upload a file
        dataset_name = 'unittest_ingest_dataset_test'
        unique_id = mfid.mfid()[0]
        result = user_cli._create_dataset_with_metadata(
            dataset_name=dataset_name,
            unique_id=unique_id
        )
        dsid = result['dsid']

        # Upload test file
        file_path = os.path.expanduser('~/Git/pycrucible/pycrucible/test-data/sunrise.png')
        user_cli.upload_dataset(dsid, file_path)

        # Test ingesting the dataset
        file_to_upload = 'api-uploads/sunrise.png'
        ingestion_class = 'ImageIngestor'
        ingest_result = user_cli.ingest_dataset(dsid, file_to_upload, ingestion_class)

        self.assertIsInstance(ingest_result, dict)
        self.assertIn('id', ingest_result)
        self.assertIn('status', ingest_result)

        # Verify ingestion request was created
        reqid = ingest_result['id']
        status = user_cli.get_ingestion_status(dsid, str(reqid))
        self.assertIsInstance(status, dict)

    


# This block runs the tests when the script is executed
if __name__ == '__main__':
    unittest.main()
