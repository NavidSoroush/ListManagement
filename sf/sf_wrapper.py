import SQLForce
from SQLForce import AttachmentReader, AttachmentWriter
from utility.gen_helper import convert_unicode_to_date, create_dir_move_file, split_name
import traceback
import os
import shutil


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
        self.__att_drive__ = 'C:/SFDC_Uploads/'

    def _auth(self, user, pw, token, instance='Production'):
        """
        helper method to authenticate a user when the SFPlatform object is instantiated.
        
        :param user: sf_username
        :param pw: sf_password 
        :param token: sf_secret_token
        :param instance: 'Production' or 'Sandbox'
        :return: authenticated SFDC session 
        """
        return SQLForce.Session(instance, user, pw, token)

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
        except Exception, e:
            print(Exception, e)

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
            if len(att) >= 120:
                att = self.__manage_attachements__(att=att)
            self.log.info('Attaching %s to %s list record.' % (att, obj_id))
            try:
                AttachmentWriter.attachFile(session=self.session, parentId=obj_id, filename=att)
            except:
                self.log.warn('Unable to attach the %s file. I suggest it gets uploaded manually.' % att)
                self.log.warn(str(traceback.format_exc()))
        self.__clean_up_attachments__()

    def last_list_uploaded(self, obj_id, obj, success=False):
        """
        used to determine the last time a record was updated on a given object (given the field is exists on said obj)
        
        :param obj_id: SFDC obj id
        :param obj: SFDC API object name
        :param success: boolean
        :return: boolean
        """
        from datetime import datetime
        print(obj_id)
        today = datetime.utcnow().isoformat()
        items = [obj_id, today]
        try:
            if obj == 'Account':
                self.session.update('Account', ['Last_Rep_List_Upload__c'], [items])
            elif obj == 'BizDev Group':
                self.session.update('BizDev__c', ['Last_Upload_Date__c'], [items])
            success = True
            print("Successfully updated the last list uploaded field on the %s's page." % obj)
        except Exception, e:
            print Exception, e
            success = False

        finally:
            return success

    def get_current_members(self, obj_id, obj):
        """
        used to get the current members of an object (given it exists)
        
        :param obj_id: SFDC obj id
        :param obj: SFDC API object name
        :return: list, members of object [a, b, c, d, e, f, g, ...]
        """
        print('Getting current members from %s object.' % obj)
        members = []
        try:
            if obj == 'Campaign':
                sql = 'SELECT ContactId, Status, Id FROM CampaignMember WHERE CampaignId="' \
                      '' + obj_id + '" AND Contact.Territory_Manager__c!="Max Prown"'
                print sql
                for rec in self.session.selectRecords(sql):
                    members.append(rec.ContactId)
                    members.append(rec.Status)
                    members.append(rec.Id)
            elif obj == 'BizDev Group':
                sql = 'SELECT Id, BizDev_Group__c FROM Contact WHERE BizDev_Group__c="' + obj_id + '"'
                for rec in self.session.selectRecords(sql):
                    members.append(rec.Id)
                    members.append(rec.BizDev_Group__c)
        except:
            print 'No advisors in %s object.' % obj
        return members

    def __manage_attachements__(self, att):
        """
        used as a helper method to create a temp drive, and move files from a source to the temp drive.
        
        :param att: source file name  
        :return: new temp file name
        """
        if not os.path.isdir(self.__att_drive__):
            os.mkdir(self.__att_drive__)
        file_name_list = split_name(att).replace('-', ' ').replace('_', ' ').split(' ')
        new_name = self.__att_drive__ + ' '.join(file_name_list[:2]) + ' ' + ' '.join(file_name_list[-2:])
        shutil.copy(att, new_name)
        return new_name

    def __clean_up_attachments__(self):
        """
        used to delete a temporary drive, if it exists
        
        :return: n/a
        """
        if os.path.isdir(self.__att_drive__):
            shutil.rmtree(self.__att_drive__)
