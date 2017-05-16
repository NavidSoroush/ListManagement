import email
import time
import datetime
import imaplib
from cred import outlook_userEmail, password, sfuser, sfpw, sf_token
from lxml.html import fromstring
from sf.sf_wrapper import SFPlatform
from email_handler.email_wrapper import Email
from utility.gen_helper import determine_ext

_objects = ['Campaign', 'BizDev Group', 'Account']
_list_notification_elements = [
    'An upload list has been added'
    , 'An upload list has been added to'
    , 'by', 'Account Link: '
    , 'Attachment Link: '
    , 'BizDev Group Link: '
    , 'List Link:']
_looking_for_elements = ['Campaign Link: ', 'Attachment Link: ']


class ReturnDict(object):
    def __init__(self, item, email_var):
        self.item = item
        self.email_var = email_var


class MailBoxReader:
    def __init__(self, log):
        self.log = log
        self._email_account = outlook_userEmail + '/Lists'
        self._email_folder = 'INBOX/Auto Lists From SFDC/'
        self.mailbox = imaplib.IMAP4_SSL('outlook.office365.com')
        self.mailbox.login(self._email_account, password)
        self.mailbox.select(self._email_folder)
        self.pending_lists = self.extract_pending_lists(mailbox=self.mailbox)

    def extract_pending_lists(self, mailbox, list_queue=[]):
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

                subject = self.get_msg_part('Subject', f_data[0])
                if _list_notification_elements[0] in subject:
                    msg, msg_body = self.get_decoded_email_body(f_data[0][1])
                    list_queue.append([msg, msg_body, num])
        self.log.info('Found %s lists pending in the queue.' % len(list_queue))
        item = {'Lists_In_Queue': len(list_queue),
                'Num_Processed': 0,
                'Lists_Data': list_queue}
        return item

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

        rec_date = msg['Date']
        sent_from = msg['From']
        sender_name = self.email_parser(sent_from, ' <')
        sent_from = self.email_parser(sent_from, '<', '>')

        obj_rec_name = self.info_parser(msg_body, _list_notification_elements[1],
                                        _list_notification_elements[2])
        obj_rec_name = obj_rec_name[:obj_rec_name.index(_list_notification_elements[2])]

        self.log.info(
            "Processing begins on %s's list attached to %s on the %s object" % (sender_name, obj_rec_name, obj))

        obj_rec_link = self.info_parser(msg_body, _list_notification_elements[3],
                                        _list_notification_elements[4])

        att_link = self.info_parser(msg_body, _list_notification_elements[4],
                                    _list_notification_elements[-2])[39:57]

        list_obj = self.info_parser(msg_body, _list_notification_elements[-2])[-20:-2]

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
        sfdc = SFPlatform(user=sfuser, pw=sfpw, token=sf_token)
        file_path, start_date, pre_or_post, a_name, a_id = sfdc.download_attachments(att_id=[att_link], obj=obj,
                                                                                     obj_url=obj_rec_link)
        ext_len, ext = determine_ext(f_name=file_path)

        self._move_received_list_to_processed_folder(num=msg_id)

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

    def _move_received_list_to_processed_folder(self, num):
        self.mailbox.copy(num, 'INBOX/Auto Processed Lists')
        self.mailbox.store(num, '+FLAGS', r'(\Deleted)')
        self.mailbox.expunge()
        self.log.info("Moved email to 'Auto Processed Lists' folder in outlook.")

    def get_decoded_email_body(self, message_body):
        msg = email.message_from_string(message_body)
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

# m = MailBoxReader()
# for i in range(m.pending_lists['Lists_In_Queue']):
#     print('List %s pre-processed data.' % (i + 1))
#     extracted_data = m.iterative_processing(m.pending_lists['Lists_Data'][i])
#     for k, v in extracted_data.iteritems():
#         print('%s: %s' % (k, v))
