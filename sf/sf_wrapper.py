# should be able to access all objects
# should be able to delete, update, create records in sfdc
# should be able to identify current members of a campaign
import SQLForce
from SQLForce import AttachmentReader
from utility.gen_helpers import convert_unicode_to_date, create_dir_move_file


class SFPlatform:
    def __init__(self, user, pw, token):
        self._save_dir = 'T:/Shared/FS2 Business Operations/Python Search Program/New Lists/'
        self._custom_domain = 'fsinvestments.my.salesforce.com:'
        self.session = self._auth(user, pw, token)

    def _auth(self, user, pw, token, instance='Production'):
        return SQLForce.Session(instance, user, pw, token)

    def close_session(self):
        self.session.logout()
        SQLForce.SQLForceServer.killServer()

    def download_attachments(self, att_id, obj, obj_url):
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

    def last_list_uploaded(self, obj_id, obj, success=False):
        from datetime import datetime
        today = datetime.utcnow().isoformat()
        items = [obj_id, today]
        for i in items:
            print '%s: %s' % (i, type(i))
        try:
            if obj == 'Account':
                self.session.update('Account', ['Last_Rep_List_Upload__c'], [items])
            elif obj == 'BizDev Group':
                self.session.update('BizDev_Group__c', ['Last_Upload_Date__c'], [items])
            success = True
            print "Successfully updated the last list uploaded field on the %s's page." % obj
        except Exception, e:
            print Exception, e
            success = False

        finally:
            return success
