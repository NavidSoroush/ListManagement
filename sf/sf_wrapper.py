import os
import traceback
import shutil

import json
import base64
import requests
import simple_salesforce

try:
    from salesforce_bulkipy import *
except ImportError:
    print('Salesforce Bulkipy import is not currently python 3 compatable.')

try:
    import SQLForce
    from SQLForce import AttachmentReader, AttachmentWriter
except ImportError:
    print('SQLForce is not currently installed in this environment.')

from ListManagement.utility.gen_helper import convert_unicode_to_date, create_dir_move_file, split_name, determine_ext
from ListManagement.utility.pandas_helper import make_df


class SFPlatform:
    """
    a wrapper object for the SQLForce (SalesForce REST) API.
    
    """

    def __init__(self, user, pw, token, log=None):
        """
        declare the objects attribute values and authenticate the user.
        
        :param user: sf_username
        :param pw: sf_password 
        :param token: sf_secret_token
        """
        self.log = log
        self._save_dir = 'T:/Shared/FS2 Business Operations/Python Search Program/New Lists/'
        self._custom_domain = 'https://fsinvestments.my.salesforce.com:'
        self.session = self._auth(user, pw, token)
        self._accepted_job_types = ['insert', 'update']
        self._att_drive = 'C:/SFDC_Uploads/'

    def _auth(self, user, pw, token, instance='Production'):
        """
        helper method to authenticate a user when the SFPlatform object is instantiated.
        
        :param user: sf_username
        :param pw: sf_password 
        :param token: sf_secret_token
        :param instance: 'Production' or 'Sandbox'
        :return: authenticated SFDC session 
        """
        try:
            session = SQLForce.Session(instance, user, pw, token)
        except:
            session = simple_salesforce.Salesforce(username=user, password=pw, security_token=token,
                                                   instance_url=self._custom_domain, session=requests.Session())
        return session

    def close_session(self):
        """
        used to close and logout of the SalesForce session
        :return: n/a
        """
        self.session.logout()
        SQLForce.SQLForceServer.killServer()

    def update_records(self, obj, fields, upload_data):
        """
        used to update records on a given object
        
        :param obj: SFDC API object name
        :param fields: list, [col_a, col_n, ...]
        :param upload_data: list of lists, [[obj_id_a, col_a_val, col_n_val], [obj_id_b, col_a_val, col_n_val]]
        :return: number of records updated
        """
        print('Attempting to update %s records on the %s object.' % (len(upload_data), obj))
        self.session.update(table=obj, columns=fields, data=upload_data)
        n_updated = self.session.getenv('ROW_COUNT')
        return n_updated

    def create_records(self, obj, fields, upload_data):
        """
        used to create records on a given object
        
        :param obj: SFDC API object name
        :param fields: list, [col_a, col_n, ...]
        :param upload_data: list of lists, [[obj_id_a, col_a_val, col_n_val], [obj_id_b, col_a_val, col_n_val]]
        :return: number of records created
        """
        print('Attempting to associate %s records to the %s object.' % (len(upload_data), obj))
        try:
            self.session.insert(table=obj, columns=fields, data=upload_data)
            n_inserted = self.session.getenv('ROW_COUNT')
            return n_inserted
        except Exception:
            print(Exception)

    def download_attachments(self, att_id, obj, obj_url):
        """
        used to download attachments from a given object
        
        :param att_id: SFDC attachment_id 
        :param obj: SFDC API object name
        :param obj_url: SFDC obj_id
        :return: tuple, (attachment_name, event_date, pre_or_post, account_name, account_id)
        """
        attachment = AttachmentReader.exportByAttachmentIds(session=self.session, attachmentIds=att_id,
                                                            outputDir=self._save_dir, createSubDirs=False)

        e_date = None
        pre_or_post = None
        account_name = None
        account_id = None

        if obj == 'Campaign':
            sql = 'SELECT StartDate,Account__c FROM Campaign Where id=' + '"{}"'.format('" "'.join([obj_url[-18:]]))
            for rec in self.session.selectRecords(sql):
                e_date, pre_or_post = convert_unicode_to_date(rec.StartDate)
                account_id = rec.Account__c
        elif obj == 'BizDev Group':
            sql = 'SELECT Name,Account__c FROM BizDev__c Where id=' + '"{}"'.format('" "'.join([obj_url[:18]]))
            for rec in self.session.selectRecords(sql):
                account_id = rec.Account__c

        if account_id is not None:
            sql = 'SELECT Name FROM Account Where id=' + '"{}"'.format('" "'.join([account_id]))
            for rec in self.session.selectRecords(sql):
                account_name = rec.Name

        attachment = create_dir_move_file(path=attachment)
        print('Successfully downloaded file from SF here:\n   - %s' % attachment)
        return attachment, e_date, pre_or_post, account_name, account_id

    def upload_attachments(self, obj_id, attachments):
        """
        used to upload attachments to a given record.
        
        1) loop through each attachments in the attachments list
        2) if the length of the attachment path > 120, create and move to a temporary drive
        3) upload attachment to SFDC
        4) after all attachments are associated with the object, delete the temporary drive (and all contents)
        
        :param obj_id: object_id
        :param attachments: list, ['attach_path_1, attach_path_2, attach_path_n, ...]
        :return: n/a
        """
        for att in attachments:
            att = self._manage_attachements(att=att)
            self.log.info('Attaching %s to %s list record.' % (att, obj_id))
            try:
                body = self._read_data(path=att)
                file_name = split_name(att)
                self._prepare_post(body, obj_id, file_name)
            except:
                self.log.warn('Unable to attach the %s file. Please manually upload.' % att)
                self.log.warn(str(traceback.format_exc()))
        self._clean_up_attachments()

    def _read_data(self, path):
        with open(path, 'rb') as f:
            body = base64.b64encode(f.read())
        return body

    def _prepare_post(self, body, obj_id, file_name):
        api_url = 'https://%s/services/data/v29.0/sobjects/Attachment' % self.session.sf_instance
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer %s' % self.session.session_id}
        data = json.dumps({'ParentId': obj_id, 'Name': file_name, 'body': body.decode('utf-8')})
        response = requests.post(api_url, data=data, headers=headers)
        return response.text

    def _manage_attachements(self, att):
        """
        used as a helper method to create a temp drive, and move files from a source to the temp drive.
        
        :param att: source file name  
        :return: new temp file name
        """
        if not os.path.isdir(self._att_drive):
            os.mkdir(self._att_drive)
        file_name_list = split_name(att).replace('-', ' ').replace('_', ' ').split(' ')
        if len(file_name_list) > 2:
            new_name = self._att_drive + ' '.join(file_name_list[:2]) + ' ' + ' '.join(file_name_list[-2:])
        else:
            new_name = self._att_drive + ' '.join(file_name_list)
        shutil.copy(att, new_name)
        return new_name

    def _clean_up_attachments(self):
        """
        used to delete a temporary drive, if it exists
        
        :return: n/a
        """
        if os.path.isdir(self._att_drive):
            shutil.rmtree(self._att_drive)

    def query(self, sfdc_object, fields, where=None):
        print('Querying for records from %s object.' % sfdc_object)
        query_result = {}

        sql = 'SELECT %s FROM %s' % (fields, sfdc_object)
        if where is not None and isinstance(where, str):
            sql += 'WHERE %s' % where
        else:
            raise (TypeError("'where' is of wrong type. must provide type str."))

        result = self.session.query(sql)

        for field in fields:
            query_result[field] = [v for res in result['records'] for k, v in res.items() if k == field]

        df = make_df(data=query_result)
        return df.values

    def request_job(self, job_type, sf_object, fields, data, isbulk=False):
        assert job_type in self._accepted_job_types
        data = self._prepare_data(data, fields)
        if not isbulk:
            self._simple_job(job_type, sf_object, data)
        else:
            self._bulk_job(job_type, sf_object, data)

    def _simple_job(self, job_type, sf_object, data):
        for rec in data:
            if job_type == self._accepted_job_types[0]:
                self.session.insert(sf_object, rec)
            elif job_type == self._accepted_job_types[1]:
                self.session.update(sf_object, rec)

    def _bulk_job(self, bulk_type, sf_object, csv_data):
        csv_iter = CsvDictsAdapter(iter(csv_data))
        job = self._determine_job(bulk_type, sf_object)
        batch = self._bulk.post_bulk_batch(job, csv_iter)
        self._bulk.wait_for_batch(job, batch)
        self._bulk.close_job()

    def _determine_job(self, bulk_type, sf_object):
        if bulk_type == self._accepted_job_types[0]:
            job = self._bulk.create_insert_job(sf_object, contentType='CSV')
        elif bulk_type == self._accepted_job_types[1]:
            job = self._bulk.create_update_job(sf_object, contentType='CSV')
        else:
            raise (ValueError('%s job type is not supported.'))
        return job

    def _prepare_data(self, data, fields):
        df = pd.DataFrame(data=data, columns=fields)
        return df.to_dict('rows')
