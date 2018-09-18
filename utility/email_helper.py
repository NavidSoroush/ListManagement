from __future__ import absolute_import

import os
import shutil
import email
from lxml.html import fromstring

try:
    from . import general as _ghelp
except ModuleNotFoundError:
    from ListManagement.utility import general as _ghelp

objects = ['Campaign', 'BizDev Group', 'Account']
list_notification_elements = [
    'An upload list has been added'
    , 'An upload list has been added to'
    , 'by', 'Account Link: '
    , 'Attachment Link: '
    , 'BizDev Group Link: '
    , 'List Link:']

looking_for_elements = ['Campaign Link: ', 'Attachment Link: ']
acceptable_types = ['.xlsx', '.pdf', '.csv', '.xls', '.zip', '.docx', '.doc']
temp_save_attachments = 'C:/save_att/'
list_team = ["ricky.schools@fsinvestments.com"]  # , 'salesops@fsinvestments.com']


def lists_in_queue(var_list):
    """
    determines if there are any lists in the queue.

    :param var_list: dictionary of list variables.
    :return: boolean TRUE / FALSE
    """
    if var_list['Lists_In_Queue'] > 0:
        return True
    else:
        print('No lists to process. Will check back in 1 hour.')
        return False


def close_mailbox_connection(m):
    """
    closes the mailbox connection

    :param m: mailbox object
    :return: dictionary of mailbox information.
    """

    m.close()
    m.logout()
    return {'Mailbox': None}


def craft_notification_email(items):
    """
    creates the actual text values of the email.

    :param items: dictionary items for stats processing
    :return: body of email.
    """
    body = """
%s,

Your list attached to %s has been processed. Below are the results of 
the program. All files generated by the search program that require 
further research, or that were requested, have been attached.

If you have questions, please reach out to:
%s
%s

Search results:
Total Advisors: %s
Found in SF: %s
Updating Contact in SF or Adding to Campaign: %s
Contact Info Up-To-Date: %s
Creating: %s
Added to Campaign or BDG: %s
Updated in Campaign or Stayed in BDG: %s
Removed from Campaign or BDG: %s
Need Research: %s
Received: %s
Process Started: %s
Process Completed: %s
Processing Time: %s
\n%s
""" % (items[0], items[1],
       items[2], items[3],
       items[4], items[5],
       items[6], items[7],
       items[8], items[9],
       items[10], items[11],
       items[12], items[13],
       items[14], items[15],
       items[16], items[17])
    return body


def get_decoded_email_body(message_body):
    msg = email.message_from_bytes(message_body)
    if msg.is_multipart():
        for payload in msg.get_payload():
            pl = payload.get_payload(decode=True)
            return msg, fromstring(pl).text_content()
    else:
        return msg, msg.get_payload(decode=True)


def body_parse(message, s_string):
    tmp = str(message)
    start1 = tmp.find(s_string)
    tmp = tmp[start1 + 29:]
    start2 = tmp.find(s_string)
    mailBody = tmp[start2:]
    return mailBody


def info_parser(body, look, look2=None, n=None):
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

    if look in objects[:1]:
        incr = 40
    else:
        incr = 1

    lf_start = body.find(look)
    tmp = body[len(look) + incr + lf_start:]
    if look2 is not None:
        lf2_start = body.find(look2)
        tmp = tmp[:lf2_start - len(look) - n]
    return tmp


def email_parser(sender_name, look1, look2=None):
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
        tmp_str = sender_name[finder + 1:finder2]
    else:
        tmp_str = sender_name[:finder]

    return tmp_str


def get_msg_part(msg_part, array):
    """
    decodes the email_handler body from the email_handler data

    :param msg_part: coded message string (required)
    :param array: items to parse
    :return: decoded text of email_handler message
    """
    import email
    msg = email.message_from_string(array[1])
    if msg_part is not None:
        decode = email.Header.decode_header(msg[msg_part])[0]
    else:
        decode = email.Header.decode_header(msg)[0]
    tmp = unicode(decode[0], 'utf-8')
    return tmp


def determine_id_and_object_from_link(tmp, email_text, log):
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
        log.warn('Unable to determine object from Salesforce link. You will need to manually upload'
                 'the list Salesforce for the new list request.')
    return tmp


def handle_list_queue_requests(num, f_data, list_queue):
    raw = email.message_from_bytes(f_data[0][1])
    subject = raw['subject']
    if list_notification_elements[0] in subject:
        msg, msg_body = get_decoded_email_body(f_data[0][1])
        list_queue.append([msg, msg_body, num])
    return list_queue


def attachment_reader(remove=False, raw=None, att=None):
    if remove:
        if os.path.isdir(temp_save_attachments):
            shutil.rmtree(temp_save_attachments)
    else:
        if not os.path.isdir(temp_save_attachments):
            os.mkdir(temp_save_attachments)
        if att is not None:
            len_ext, ext = _ghelp.determine_ext(att)
            if ext in acceptable_types:
                new_f_name = temp_save_attachments + ''.join(e for e in att[:-5] if e.isalnum()) + ext
                with open(new_f_name, mode='wb') as f:
                    f.write(raw.get_payload(decode=True))
                return new_f_name
