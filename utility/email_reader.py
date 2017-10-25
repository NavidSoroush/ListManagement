import os
import shutil
import re
import imaplib
import email
from email.utils import parseaddr
import time
import datetime
from dateutil.parser import parse
from lxml.html import fromstring

from cred import outlook_userEmail, password, sfuser, sfpw, sf_token

from ListManagement.sf.sf_wrapper import SFPlatform
from ListManagement.utility.email_wrapper import Email
from ListManagement.utility.gen_helper import determine_ext

_objects = ['Campaign', 'BizDev Group', 'Account']
_list_notification_elements = [
    'An upload list has been added'
    , 'An upload list has been added to'
    , 'by', 'Account Link: '
    , 'Attachment Link: '
    , 'BizDev Group Link: '
    , 'List Link:']
_looking_for_elements = ['Campaign Link: ', 'Attachment Link: ']
_acceptable_types = ['.xlsx', '.pdf', '.csv', '.xls', '.zip', '.docx', '.doc']
_temp_save_attachments = 'C:/save_att/'
_list_team = ["ricky.schools@fsinvestments.com", "max.charles@fsinvestments.com"]


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
                    self.handle_new_email_requests(num, email.message_from_string(f_data[0][1]))
                else:
                    list_queue = self.handle_list_queue_requests(num, f_data, list_queue)

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
        tmp_dict['sub'], tmp_dict['date'] = raw_email['subject'], datetime.datetime.strftime(parse(raw_email['date']),
                                                                                             '%m/%d/%Y %H:%M:%S')
        msg_body = "Sent by: %s\nReceived on: %s\nSubject: %s\n" % (tmp_dict['name'], tmp_dict['date'], tmp_dict['sub'])
        for part in raw_email.walk():
            if part.get_content_type().lower() == "text/html" and tmp_dict['has_link'] == 'not set':
                e_body = fromstring(part.get_payload(decode=True)).text_content()
                e_body = e_body[e_body.find("-->") + 3:]
                tmp_dict['has_link'] = e_body.find(tmp_dict['search_link'])
                if tmp_dict['has_link'] not in ['not set', -1]:
                    tmp_dict = self.determine_id_and_object_from_link(tmp=tmp_dict, email_text=e_body)
                msg_body += re.sub(r'[^\x00-\x7F]+', ' ', e_body)

            if part.get_content_maintype() == "mulipart": continue
            if part.get("Content-Disposition") is None: continue
            if part.get_filename() is not None:
                attmts.append(self.attachment_reader(raw=part, att=part.get_filename()))
        self.determine_path_and_complete_processing(num=num, dict_data=tmp_dict, att=attmts, msg_body=msg_body)
        self.attachment_reader(remove=True)

    def handle_list_queue_requests(self, num, f_data, list_queue):
        raw = email.message_from_bytes(f_data[0][1])
        subject = raw['subject']
        if _list_notification_elements[0] in subject:
            msg, msg_body = self.get_decoded_email_body(f_data[0][1])
            list_queue.append([msg, msg_body, num])
        return list_queue

    def determine_id_and_object_from_link(self, tmp, email_text):
        end_point = tmp['has_link'] + len(tmp['search_link']) + 16
        tmp['link'] = email_text[tmp['has_link'] + len(tmp['search_link']) + 1: end_point]
        if tmp['link'][:3] == '001':
            tmp['object'] = 'Account'
        elif tmp['link'][:3] == 'a0v':
            tmp['object'] = 'BizDev__c'
        elif tmp['link'][:3] == '701':
            tmp['object'] = 'Campaign'
        else:
            tmp['object'] = None
            self.log.warn('Unable to determine object from Salesforce link. You will need to manually upload'
                          'the list Salesforce for the new list request.')
        return tmp

    def iterative_processing(self, msg_list):
        msg = msg_list[0]
        msg_body = msg_list[1]
        msg_id = msg_list[2]

        if _objects[0] in msg_body:
            obj = _objects[0]
        elif _objects[1] in msg_body:
            obj = _objects[1]
        else:
            obj = 'Account'

        rec_date = datetime.datetime.strftime(parse(msg['Date']), '%m/%d/%Y %H:%M:%S')
        sender_name = parseaddr(msg['From'])[0]
        sent_from = parseaddr(msg['From'])[1]

        obj_rec_name = self.info_parser(msg_body, _list_notification_elements[1],
                                        _list_notification_elements[2])

        self.log.info(
            "Processing begins on %s's list attached to %s on the %s object" % (sender_name, obj_rec_name, obj))

        obj_rec_link = self.info_parser(msg_body, _list_notification_elements[3],
                                        _list_notification_elements[4])

        att_link = self.info_parser(msg_body, _list_notification_elements[4],
                                    _list_notification_elements[-2])[39:57]

        list_obj = self.info_parser(msg_body, _list_notification_elements[-2])[-18:]

        self.log.info('Attachment Id: %s' % att_link)
        self.log.info('List Object Id: %s' % list_obj)

        if obj == 'Campaign':
            obj_rec_link = obj_rec_link[-18:]
        elif obj == 'BizDev Group':
            obj_rec_link = self.info_parser(msg_body, _list_notification_elements[5],
                                            _list_notification_elements[4])
            obj_rec_link = obj_rec_link[39:57]
        else:
            obj_rec_link = obj_rec_link[39:57]
        self.log.info('Object Id: %s' % obj_rec_link)

        self.log.info('Downloading attachment from SFDC.')
        sfdc = SFPlatform(user=sfuser, pw=sfpw, token=sf_token, log=self.log)
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
        # self.mailbox.copy(num, 'INBOX/Auto Processed Lists')
        self.mailbox.copy(num, folder)
        self.mailbox.store(num, '+FLAGS', r'(\Deleted)')
        self.mailbox.expunge()
        self.log.info("Moved email to %s folder in outlook." % folder)

    def get_decoded_email_body(self, message_body):
        msg = email.message_from_bytes(message_body)
        if msg.is_multipart():
            for payload in msg.get_payload():
                pl = payload.get_payload(decode=True)
                return msg, fromstring(pl).text_content()
        else:
            return msg, msg.get_payload(decode=True)

    def body_parse(self, message, s_string):
        tmp = str(message)
        start1 = tmp.find(s_string)
        tmp = tmp[start1 + 29:]
        start2 = tmp.find(s_string)
        mailBody = tmp[start2:]
        return mailBody

    def info_parser(self, body, look, look2=None, n=None):
        """
        parses the body text of an email_handler message

        :param body: text of an email_handler message (required)
        :param look: start / end location of the text to parse (required)
        :param look2: optional - takes a secondary substring if finding text
        :param n: length of where attachment link is
        :return: parsed substring
        """
        if n is None:
            n = 2

        if look in _objects[:1]:
            incr = 40
        else:
            incr = 1

        lf_start = body.find(look)
        tmp = body[len(look) + incr + lf_start:]
        if look2 is not None:
            lf2_start = body.find(look2)
            tmp = tmp[:lf2_start - len(look) - n]
        return tmp

    def email_parser(self, sender_name, look1, look2=None):
        """
        parses the body text of an email_handler message

        :param sender_name: text of an email_handler message (required)
        :param look1: start / end location of the text to parse (required)
        :param look2: optional - takes a secondary substring if finding text
        :return: parsed substring
        """
        finder = sender_name.find(look1)
        if look2 is not None:
            finder2 = sender_name.find(look2)
            tmpStr = sender_name[finder + 1:finder2]
        else:
            tmpStr = sender_name[:finder]

        return tmpStr

    def get_msg_part(self, msg_part, array):
        """
        decodes the email_handler body from the email_handler data

        :param msg_part: coded message string (required)
        :param array: items to parse
        :return: decoded text of email_handler message
        """
        msg = email.message_from_string(array[1])
        if msg_part is not None:
            decode = email.Header.decode_header(msg[msg_part])[0]
        else:
            decode = email.Header.decode_header(msg)[0]
        tmp = unicode(decode[0], 'utf-8')
        return tmp

    def close_mailbox(self):
        self.mailbox.logout()

    def attachment_reader(self, remove=False, raw=None, att=None):
        if remove:
            if os.path.isdir(_temp_save_attachments):
                shutil.rmtree(_temp_save_attachments)
        else:
            if not os.path.isdir(_temp_save_attachments):
                os.mkdir(_temp_save_attachments)
            if att is not None:
                len_ext, ext = determine_ext(att)
                if ext in _acceptable_types:
                    new_f_name = _temp_save_attachments + ''.join(e for e in att[:-5] if e.isalnum()) + ext
                    with file(new_f_name, mode='wb') as f:
                        f.write(raw.get_payload(decode=True))
                    return new_f_name

    def determine_path_and_complete_processing(self, num, dict_data, att, msg_body):
        if dict_data['name'] == 'FS Investments':
            self._move_received_list_to_processed_folder(num, 'INBOX/FS Emails')

        if dict_data['sub'] == 'An upload list has been added':
            self._move_received_list_to_processed_folder(num, 'INBOX/Auto Lists From SFDC')

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
            _list_team.append(dict_data['email'])
            Email(subject=sub, to=_list_team, body=msg_body, attachment_path=None)
            self._move_received_list_to_processed_folder(num, 'INBOX/No Link or Attachments')
        else:
            _list_team.append('rickyschools+v3lhm65etri76gwbn0sy@boards.trello.com')
            sub = 'New List Received. Check List Management Trello Board'
            msg_body = "https://trello.com/b/KhPmn9qK/sf-lists-leads\n\n" + msg_body
            Email(subject=sub, to=_list_team, body=msg_body, attachment_path=att)
            self.associate_email_request_with_sf_object(dict_data=dict_data, att=att)
            self._move_received_list_to_processed_folder(num=num, folder="INBOX/New Lists")

    def associate_email_request_with_sf_object(self, dict_data, att):
        sfdc = SFPlatform(user=sfuser, pw=sfpw, token=sf_token, log=self.log)
        data_pkg = [['List_Upload__c'], [dict_data['link'], 'True']]
        try:
            self.log.info('Attempting to upload emailed list request to SFDC and attach links.')
            sfdc.update_records(dict_data['object'], data_pkg[0], [data_pkg[1]])
            sfdc.upload_attachments(dict_data['link'], att)
        except:
            self.log.warn('There was an issue updating and uploading data to the %s record.' % dict_data['object'])
            sfdc.close_session()
            pass

# m = MailBoxReader()
# for i in range(m.pending_lists['Lists_In_Queue']):
#     print('List %s pre-processed data.' % (i + 1))
#     extracted_data = m.iterative_processing(m.pending_lists['Lists_Data'][i])
#     for k, v in extracted_data.iteritems():
#         print('%s: %s' % (k, v))
