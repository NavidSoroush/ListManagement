import os
import traceback
import shutil

import json
import base64
import requests

from simple_salesforce import Salesforce

try:
    from salesforce_bulkipy import SalesforceBulkipy as Bulk, CsvDictsAdapter
except ImportError:
    from salesforce_bulk import SalesforceBulk as Bulk, CsvDictsAdapter

try:
    from ListManagement.utility.gen_helper import convert_unicode_to_date, create_dir_move_file, split_name
    from ListManagement.utility.pandas_helper import make_df
except:
    from utility.gen_helper import convert_unicode_to_date, create_dir_move_file, split_name
    from utility.pandas_helper import make_df

_AttachmentColummns = ["Id", "ParentId", "Body", "ContentType", "Name"]
_AttachmentBaseSOL = "SELECT " + ",".join(_AttachmentColummns) + " FROM Attachment "


class SFPlatform:
    """
    a wrapper object for the SQLForce (SalesForce REST) API.
    
    """

    def __init__(self, user, pw, token, log=None, instance='Production'):
        """
        declare the objects attribute values and authenticate the user.
        
        :param user: sf_username
        :param pw: sf_password 
        :param token: sf_secret_token
        """
        self.log = log
        self._save_dir = 'T:/Shared/FS2 Business Operations/Python Search Program/New Lists/'
        if instance == 'Production':
            self._custom_domain = 'https://fsinvestments.my.salesforce.com:'
        else:
            self._custom_domain = 'https://test.salesforce.com'
        self.session, self.bulk_session = self._auth(user, pw, token, instance)
        self._accepted_job_types = ['insert', 'update']
        self._att_drive = 'C:/SFDC_Uploads/'

    def _auth(self, user, pw, token, instance):
        """
        helper method to authenticate a user when the SFPlatform object is instantiated.
        
        :param user: sf_username
        :param pw: sf_password 
        :param token: sf_secret_token
        :param instance: 'Production' or 'Sandbox'
        :return: authenticated SFDC session 
        """
        session = Salesforce(username=user, password=pw, security_token=token,
                             instance=instance, instance_url=self._custom_domain,
                             session=requests.Session())
        bulk_session = Bulk(sessionId=session.session_id, host=self._custom_domain)
        return session, bulk_session

    def update_records(self, obj, fields, upload_data):
        """
        used to update records on a given object
        
        :param obj: SFDC API object name
        :param fields: list, [col_a, col_n, ...]
        :param upload_data: list of lists, [[obj_id_a, col_a_val, col_n_val], [obj_id_b, col_a_val, col_n_val]]
        :return: number of records updated
        """
        self.log.info('Attempting to update %s records on the %s object.' % (len(upload_data), obj))
        self.request_job(job_type='update', sf_object=obj, fields=fields, data=upload_data)

    def create_records(self, obj, fields, upload_data):
        """
        used to create records on a given object
        
        :param obj: SFDC API object name
        :param fields: list, [col_a, col_n, ...]
        :param upload_data: list of lists, [[obj_id_a, col_a_val, col_n_val], [obj_id_b, col_a_val, col_n_val]]
        :return: number of records created
        """
        self.log.info('Attempting to associate %s records to the %s object.' % (len(upload_data), obj))
        self.request_job(job_type='insert', sf_object=obj, fields=fields, data=upload_data)

    def download_attachments(self, att_id, obj, obj_url):
        """
        used to download attachments from a given object
        
        :param att_id: SFDC attachment_id 
        :param obj: SFDC API object name
        :param obj_url: SFDC obj_id
        :return: tuple, (attachment_name, event_date, pre_or_post, account_name, account_id)
        """
        attachment = self._export_attachment(att_id=att_id, output=self._save_dir)

        e_date = None
        pre_or_post = None
        account_name = None
        account_id = None

        if obj == 'Campaign':
            df = self.query('Campaign', ['StartDate', 'Account__c'], where="Id='%s'" % obj_url[-18:])
            e_date, pre_or_post = convert_unicode_to_date(df['StartDate'][0])
            account_id = df['Account__c'][0]

        elif obj == 'BizDev Group':
            df = self.query('BizDev__c', ['Name', 'Account__c'], where="Id='%s'" % obj_url[:18])
            account_id = df['Account__c'][0]

        if account_id is not None:
            df = self.query('Account', ['Name'], where="Id='%s'" % account_id)
            account_name = df['Name'][0]

        attachment = create_dir_move_file(path=attachment)
        print('Successfully downloaded file from SF here:\n   - %s' % attachment)
        return attachment, e_date, pre_or_post, account_name, account_id

    def _export_attachment(self, att_id, output):
        exported_files = []
        df = self.query(sfdc_object='Attachment', fields=_AttachmentColummns, where="Id='%s'" % att_id)

        my_dir = os.path.join(output, df['ParentId'][0])
        if not os.path.exists(my_dir):
            os.makedirs(my_dir)

        out_file = os.path.join(my_dir, df['Name'][0])
        if df['Body'][0]:
            download_url = 'https://%s%s' % (self.session.sf_instance, df['Body'][0])
            headers = {'Content-Type': 'application/json',
                       'Authorization': 'Bearer %s' % self.session.session_id}
            response = requests.get(download_url, headers=headers, stream=True)
            if response.status_code == 200:
                with open(out_file, 'wb') as fh:
                    for chunk in response.iter_content(1024):
                        fh.write(chunk)
                exported_files.append(out_file)

        return exported_files

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
            try:
                att = self._manage_attachements(att=att)
                self.log.info('Attaching %s to %s list record.' % (att, obj_id))
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
        self.log.info('Querying for records from %s object.' % sfdc_object)
        query_result = {}

        sql = 'SELECT %s FROM %s' % (','.join(fields), sfdc_object)
        if where is not None and isinstance(where, str):
            sql += ' WHERE %s' % where
        else:
            raise (TypeError("'where' is of wrong type. must provide type str."))

        result = self.session.query(sql)

        for field in fields:
            query_result[field] = [v for res in result['records'] for k, v in res.items() if k == field]

        df = make_df(data=query_result)
        return df

    def request_job(self, job_type, sf_object, fields, data):
        assert job_type in self._accepted_job_types
        for chunk in self._chunker(data, 10000):
            chunk = self._prepare_data(chunk, fields)
            self._bulk_job(job_type, sf_object, chunk)

    def _bulk_job(self, bulk_type, sf_object, csv_data):
        csv_iter = CsvDictsAdapter(iter(csv_data))
        job = self._determine_job(bulk_type, sf_object)
        batch = self.bulk_session.post_batch(job, csv_iter)
        self.bulk_session.wait_for_batch(job, batch)
        self.bulk_session.close_job(job)

    def _determine_job(self, bulk_type, sf_object):
        if bulk_type == self._accepted_job_types[0]:
            job = self.bulk_session.create_insert_job(sf_object, contentType='CSV')
        elif bulk_type == self._accepted_job_types[1]:
            job = self.bulk_session.create_update_job(sf_object, contentType='CSV')
        else:
            raise (ValueError('%s job type is not supported.'))
        return job

    def _prepare_data(self, data, fields):
        if fields is None:
            df = make_df(data)
        else:
            df = make_df(data=data, columns=fields)
        return df.to_dict('rows')

    @staticmethod
    def _chunker(data, size):
        for i in range(0, len(data), size):
            yield data[i:i + size]
