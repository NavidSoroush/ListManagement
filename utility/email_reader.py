from __future__ import absolute_import

import re
import imaplib
from email.utils import parseaddr
import time
import datetime

from cred import outlook_userEmail, password  # , sfuser, sfpw, sf_token

from PythonUtilities.salesforcipy import SFPy

try:
    from utility.sf_helper import get_user_id
    from utility.gen_helper import determine_ext, date_parsing
    from utility.email_helper import *
    from config import Config as con
except ModuleNotFoundError:
    from ListManagement.utility.sf_helper import get_user_id
    from ListManagement.utility.gen_helper import determine_ext, date_parsing
    from ListManagement.utility.email_helper import *
    from ListManagement.config import Config as con


class ReturnDict(object):
    def __init__(self, item, email_var):
        self.item = item
        self.email_var = email_var


class MailBoxReader:
    def __init__(self, log):
        self.log = log
        self._email_account = outlook_userEmail + '/Lists'
        self.new_requests_folder = '"INBOX/"'
        self.email_folder = '"INBOX/Auto Lists From SFDC/"'
        self.mailbox = imaplib.IMAP4_SSL('outlook.office365.com')
        self.mailbox.login(self._email_account, password)

    def extract_pending_lists(self, mailbox, folder):
        list_queue = list()
        mailbox.select("%s" % folder)
        s_resp, s_data = mailbox.search(None, 'ALL')
        if s_resp != "OK":
            self.log.info('No new lists were found in the email queue.')
            return

        for num in s_data[0].split():
            f_resp, f_data = mailbox.fetch(num, '(RFC822)')
            if f_resp != 'OK':
                self.log.info('Experienced an issue getting message %s' % num)
                return
            else:
                if folder == self.new_requests_folder:
                    self.handle_new_email_requests(num, email.message_from_string(f_data[0][1].decode('utf-8')))
                else:
                    list_queue = handle_list_queue_requests(num, f_data, list_queue)

        if folder == self.new_requests_folder:
            return
        else:
            self.log.info('Found %s lists pending in the queue.' % len(list_queue))
            item = {'Lists_In_Queue': len(list_queue),
                    'Num_Processed': 0,
                    'Lists_Data': list_queue}
            return item

    def handle_new_email_requests(self, num, raw_email):
        attmts = list()
        tmp_dict = dict()
        tmp_dict.update({'has_link': 'not set', 'link': None, 'object': None,
                         'search_link': "https://fsinvestments.my.salesforce.com"})
        tmp_dict['name'], tmp_dict['email'] = parseaddr(raw_email['From'])[0], parseaddr(raw_email['From'])[1]
        tmp_dict['sub'] = raw_email['subject']

        try:
            tmp_dict['date'] = datetime.datetime.strftime(
                date_parsing(raw_email['date']), '%m/%d/%Y %H:%M:%S')
        except ValueError:
            test_date = ' '.join(raw_email['date'].split(' ')[:-1])
            tmp_dict['date'] = datetime.datetime.strftime(
                datetime.datetime.strptime(test_date, '%a, %d %b %Y %H:%M:%S %z'), '%m/%d/%Y %H:%M:%S')

        msg_body = "Sent by: %s\nReceived on: %s\nSubject: %s\n" % (tmp_dict['name'], tmp_dict['date'], tmp_dict['sub'])
        for part in raw_email.walk():
            if part.get_content_type().lower() == "text/html" and tmp_dict['has_link'] == 'not set':
                e_body = fromstring(part.get_payload(decode=True)).text_content()
                e_body = e_body[e_body.find("-->") + 3:]
                tmp_dict['has_link'] = e_body.find(tmp_dict['search_link'])
                if tmp_dict['has_link'] not in ['not set', -1]:
                    tmp_dict = determine_id_and_object_from_link(tmp=tmp_dict, email_text=e_body, log=self.log)
                msg_body += re.sub(r'[^\x00-\x7F]+', ' ', e_body)

            if part.get_content_maintype() == "mulipart": continue
            if part.get("Content-Disposition") is None: continue
            if part.get_filename() is not None:
                attmts.append(attachment_reader(raw=part, att=part.get_filename()))
        self.determine_path_and_complete_processing(num=num, dict_data=tmp_dict, att=attmts, msg_body=msg_body,
                                                    sender_addr=tmp_dict['email'])
        attachment_reader(remove=True)

    def iterative_processing(self, msg_list):
        msg = msg_list[0]
        msg_body = msg_list[1]
        msg_id = msg_list[2]

        if objects[0] in msg_body:
            obj = objects[0]
        elif objects[1] in msg_body:
            obj = objects[1]
        else:
            obj = 'Account'

        rec_date = datetime.datetime.strftime(
            date_parsing(msg['Date']), '%m/%d/%Y %H:%M:%S')

        sender_name = parseaddr(msg['From'])[0]
        sent_from = parseaddr(msg['From'])[1]

        obj_rec_name = info_parser(msg_body, list_notification_elements[1],
                                   list_notification_elements[2])

        self.log.info(
            "Processing begins on %s's list attached to %s on the %s object" % (sender_name, obj_rec_name, obj))

        obj_rec_link = info_parser(msg_body, list_notification_elements[3],
                                   list_notification_elements[4])

        att_link = info_parser(msg_body, list_notification_elements[4],
                               list_notification_elements[-2])[39:57]

        list_obj = info_parser(msg_body, list_notification_elements[-1])[40:58]

        self.log.info('Attachment Id: %s' % att_link)
        self.log.info('List Object Id: %s' % list_obj)

        if obj == 'Campaign':
            obj_rec_link = obj_rec_link[-18:]
        elif obj == 'BizDev Group':
            obj_rec_link = info_parser(msg_body, list_notification_elements[5],
                                       list_notification_elements[4])
            obj_rec_link = obj_rec_link[39:57]
        else:
            obj_rec_link = obj_rec_link[39:57]
        self.log.info('Object Id: %s' % obj_rec_link)

        self.log.info('Downloading attachment from SFDC.')
        sfdc = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken, log=self.log, domain=con.SFDomain)
        file_path, start_date, pre_or_post, a_name, a_id = sfdc.download_attachments(att_id=att_link, obj=obj,
                                                                                     obj_url=obj_rec_link)
        ext_len, ext = determine_ext(f_name=file_path)

        self._move_received_list_to_processed_folder(num=msg_id, folder='"INBOX/Auto Processed Lists"')

        # _subject = "LMA Notification: %s list received." % obj_rec_name
        # _body = '%s, \n \nThe list that you attached to the %s object, %s has been added to our list queue. ' \
        #         'You will receive a notification after your list has been processed. \n \n' % (sender_name, obj,
        #                                                                                        obj_rec_name)
        # Email(subject=_subject, to=[sent_from], body=_body, attachment_path=None)
        self.log.info('Combining all meta data from %s list for processing.' % obj)
        pstart = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        Items = [ReturnDict('Object', obj), ReturnDict('Record Name', obj_rec_name),
                 ReturnDict('Sender Email', sent_from), ReturnDict('Sender Name', sender_name),
                 ReturnDict('Received Date', rec_date), ReturnDict('File Path', file_path),
                 ReturnDict('Campaign Start Date', start_date), ReturnDict('Next Step', 'Pre-processing'),
                 ReturnDict('Found Path', None), ReturnDict('ObjectId', obj_rec_link),
                 ReturnDict('Pre_or_Post', pre_or_post), ReturnDict('process_start', pstart),
                 ReturnDict('CmpAccountName', a_name), ReturnDict('CmpAccountID', a_id),
                 ReturnDict('Found in SFDC Search #2', 0), ReturnDict('Num Adding', 0),
                 ReturnDict('Num Removing', 0), ReturnDict('Num Updating/Staying', 0),
                 ReturnDict('Review Path', None), ReturnDict('SFDC Session', sfdc),
                 ReturnDict('AttachmentId', att_link), ReturnDict('ListObjId', list_obj),
                 ReturnDict('ExtensionType', ext)]

        vars_list = dict([(i.item, i.email_var) for i in Items])
        self.log.info('Current vars list: \n%s' % vars_list)

        return vars_list

    def _move_received_list_to_processed_folder(self, num, folder):
        self.mailbox.copy(num, folder)
        self.mailbox.store(num, '+FLAGS', r'(\Deleted)')
        self.mailbox.expunge()
        self.log.info("Moved email to %s folder in outlook." % folder)

    def close_mailbox(self):
        self.mailbox.logout()

    def determine_path_and_complete_processing(self, num, dict_data, att, msg_body, sender_addr):
        _folders = ['"INBOX/FS Emails"', '"INBOX/Auto Lists From SFDC"',
                    '"INBOX/No Link or Attachments"', '"INBOX/New Lists"']
        if dict_data['name'] == 'FS Investments':
            self._move_received_list_to_processed_folder(num, _folders[0])
            self.log.info('Moved mail item to %s' % _folders[0])

        elif dict_data['sub'] == 'An upload list has been added':
            self._move_received_list_to_processed_folder(num, _folders[1])
            self.log.info('Moved mail item to %s' % _folders[1])

        elif len(att) == 0 or dict_data['has_link'] in [-1, 'not set']:
            if len(att) == 0 and dict_data['has_link'] in [-1, 'not set']:
                dyn_str = 'both an attachment and a SF link'
            elif len(att) == 0:
                dyn_str = 'an attachment'
            elif dict_data['has_link'] in [-1, 'not set']:
                dyn_str = 'a SF link'
            msg_body = "%s,\n\nThe list request sent is lacking %s.\n\n" \
                       "Please resend your request for the '%s' list again with the link to SF " \
                       "and at least one attachment." \
                       "\n\nAll the best," % (dict_data['name'].split(' ')[0], dyn_str, dict_data['sub'])
            sub = "LMA Notification: Missing Attachments or SFDC Links for '%s'" % dict_data['sub']
            list_team.append(dict_data['email'])
            Email(subject=sub, to=list_team, body=msg_body, attachment_path=None)
            self._move_received_list_to_processed_folder(num, _folders[2])
            self.log.info('Mail item has no attachments. Moved to %s' % _folders[2])
        else:
            list_team.append('rickyschools+v3lhm65etri76gwbn0sy@boards.trello.com')
            sub = 'New List Received. Check List Management Trello Board'
            msg_body = "https://trello.com/b/KhPmn9qK/sf-lists-leads\n\n" + msg_body
            Email(subject=sub, to=list_team, body=msg_body, attachment_path=att)
            self.associate_email_request_with_sf_object(dict_data=dict_data, att=att, sender_addr=sender_addr)
            self._move_received_list_to_processed_folder(num, _folders[3])
            self.log.info('Moved mail item to %s' % _folders[3])

    def associate_email_request_with_sf_object(self, dict_data, att, sender_addr):
        sfdc = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken, log=self.log, domain=con.SFDomain)
        data_pkg = [['Id', 'List_Upload__c'], [dict_data['link'], 'True']]
        try:
            self.log.info('Attempting to upload emailed list request to SFDC and attach links.')
            sfdc.update_records(dict_data['object'], data_pkg[0], [data_pkg[1]])
            sfdc.upload_attachments(dict_data['link'], att)
            att_owner_and_id = get_user_id(sfdc, dict_data['link'], att, sender_addr)
            sfdc.update_records('Attachment', ['Id', 'OwnerId'], att_owner_and_id)

        except:
            self.log.warn('There was an issue updating and uploading data to the %s record.' % dict_data['object'])
            pass

# m = MailBoxReader()
# m_vars = m.extract_pending_lists(m.mailbox, m.email_folder)
# for i in range(m_vars['Lists_In_Queue']):
#     print('List %s pre-processed data.' % (i + 1))
#     extracted_data = m.iterative_processing(m_vars['Lists_Data'][i])
#     for k, v in extracted_data.iteritems():
#         print('%s: %s' % (k, v))
