# should be able to access all objects
# should be able to delete, update, create records in sfdc
# should be able to identify current members of a campaign

import SQLForce
from SQLForce import AttachmentReader
from utility.gen_helpers import convert_unicode_to_date, create_dir_move_file


class SFPlatform:
    def __init__(self, user, pw, token):
        self.session = self._auth(user, pw, token)
        self._save_dir = 'T:/Shared/FS2 Business Operations/Python Search Program/New Lists/'

    def _auth(self, user, pw, token, instance='Production'):
        return SQLForce.Session(instance, user, pw, token)

    def close_session(self):
        self.session.logout()
        SQLForce.SQLForceServer.killServer()

    def download_attachments(self, id, obj, obj_url):
        attachment = AttachmentReader.exportByAttachmentIds(self.session, id, self._save_dir, createSubDirs=False)

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
