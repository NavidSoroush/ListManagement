import email
import time
import datetime
import base64
import imaplib
import sys
from cred import outlook_userEmail, password, sfuser, sfpw, sf_token
from sf.sf_wrapper import SFPlatform
from email_handler.email_wrapper import Email

sfdc = SFPlatform(user=sfuser, pw=sfpw, token=sf_token)
_objects = ['Campaign', 'BizDev Group', 'Account']
_list_notification_elements = [
    'An upload list has been added'
    , 'An upload list has been added to'
    , 'by', 'Account Link: '
    , 'Attachment Link: '
    , 'BizDev Group Link: ']
_looking_for_elements = ['Campaign Link: ', 'Attachment Link: ']


class ReturnDict(object):
    def __init__(self, item, emailVar):
        self.item = item
        self.emailVar = emailVar


def get_msg_part(msg_part, array):
    """
    decodes the email_handler body from the email_handler data

    :param msg_part: coded message string (required)
    :param array: items to parse
    :return: decoded text of email_handler message
    """
    msg = email.message_from_string(array[1])
    decode = email.Header.decode_header(msg[msg_part])[0]
    tmp = unicode(decode[0], 'utf-8')
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
        tmpStr = sender_name[finder + 1:finder2]
    else:
        tmpStr = sender_name[:finder]

    return tmpStr


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


def decode_mailitem(mail_data):
    """
    decode mail item (remove all base64 bits)

    :param mail_data: coded mail body text (required)
    :return: decoded body text
    """
    msg = email.message_from_string(mail_data)
    encodedBody = body_parse(msg, _list_notification_elements[0])
    body = msg.get_payload()
    decodedBody = base64.b64decode(body)
    return decodedBody


def body_parse(message, s_string):
    tmp = str(message)
    start1 = tmp.find(s_string)
    tmp = tmp[start1 + 29:]
    start2 = tmp.find(s_string)
    mailBody = tmp[start2:]
    return mailBody


def check_for_new_lists():
    '''
    Instantiates the Mailbox object. Receives the list data from
    process_mailbox and returns it to the main_module.

    :return: dictionary of data used to guide list processing
    '''
    _email_account = outlook_userEmail + '/Lists'
    _email_folder = 'INBOX/Auto Lists From SFDC/'

    m = imaplib.IMAP4_SSL('outlook.office365.com')
    try:
        rv, data = m.login(_email_account, password)
    except imaplib.IMAP4.error:
        print "LOGIN FAILED!!! "
        sys.exit(1)

    print 'Mailbox: ', rv, data

    rv, data = m.select(_email_folder)
    if rv == 'OK':
        print "\nStep 1:\nLooking for list uploads."
        var_list = process_mailbox(m)

        if not lists_in_queue(var_list):
            var_list.update(close_mailbox_connection(m))

        else:
            print 'There are %s lists to process.' % var_list['Lists_In_Queue']
            var_list.update({'Mailbox': m})

        return var_list
    else:
        print "ERROR: Unable to open mailbox ", rv


def process_mailbox(m, list_queue=[]):
    '''
    Process mail identifies new list requests and returns
    the data to the main_module so all can be properly processed.

    :param m: Mailbox object
    :param list_queue: stores email data for all pending lists
    :return: dictionary of data used to guide list processing
    '''
    rv, data = m.search(None, "ALL")
    if rv != 'OK':
        print "No messages found!"
        return

    for num in data[0].split():
        rv, data = m.fetch(num, '(RFC822)')
        if rv != 'OK':
            print "ERROR getting message", num
            return
        else:
            subject = get_msg_part('Subject', data[0])
            if _list_notification_elements[0] in subject:
                decoded = decode_mailitem(data[0][1])
                list_queue.append([data[0], decoded, num])

    items = {'Lists_In_Queue': len(list_queue),
             'Num_Processed': 0,
             'Lists_Data': list_queue}

    return items


def process_list_email(email_data, m):
    """
    creates initial meta data required for list processing.
    :param email_data: email_handler string
    :param m: mailbox object
    :return: dictionary of values needed for list processing.
    """
    data = email_data[0]
    decoded_body = email_data[1]
    num = email_data[2]

    if _objects[0] in decoded_body:
        obj = _objects[0]
    elif _objects[1] in decoded_body:
        obj = _objects[1]
    else:
        obj = 'Account'

    rec_date = get_msg_part('date', data)
    sent_from = get_msg_part('From', data)
    sender_name = email_parser(sent_from, ' <')
    sent_from = email_parser(sent_from, '<', '>')

    obj_rec_name = info_parser(decoded_body, _list_notification_elements[1],
                               _list_notification_elements[2])
    obj_rec_link = info_parser(decoded_body, _list_notification_elements[3],
                               _list_notification_elements[4])

    att_link = info_parser(decoded_body, _list_notification_elements[4])[-20:-2]

    if obj == 'Campaign':
        obj_rec_link = obj_rec_link[-18:]
    elif obj == 'BizDev Group':
        obj_rec_link = info_parser(decoded_body, _list_notification_elements[5],
                                   _list_notification_elements[4])

        obj_rec_link = obj_rec_link[26:44]
    else:
        obj_rec_link = obj_rec_link[26:44]

    file_path, start_date, pre_or_post, a_name, a_id = sfdc.download_attachments(att_id=[att_link], obj=obj,
                                                                                 obj_url=obj_rec_link)

    _subject = "LMA Notification: %s list received." % obj_rec_name
    _body = '%s, \n \nThe list that you attached to the %s object, %s has been added to our list queue. ' \
            'You will receive a notification after your list has been processed. \n \n' % (sender_name, obj,
                                                                                           obj_rec_name)
    Email(subject=_subject, to=[sent_from], body=_body, attachment_path=None)

    m.copy(num, 'INBOX/Auto Processed Lists')
    m.store(num, '+FLAGS', r'(\Deleted)')
    m.expunge()
    ts = time.time()
    pstart = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    Items = [ReturnDict('Object', obj), ReturnDict('Record Name', obj_rec_name),
             ReturnDict('Sender Email', sent_from), ReturnDict('Sender Name', sender_name),
             ReturnDict('Received Date', rec_date), ReturnDict('File Path', file_path),
             ReturnDict('Campaign Start Date', start_date), ReturnDict('Next Step', 'Pre-processing'),
             ReturnDict('Found Path', None), ReturnDict('ObjectId', obj_rec_link),
             ReturnDict('Pre_or_Post', pre_or_post), ReturnDict('processStart', pstart),
             ReturnDict('CmpAccountName', a_name), ReturnDict('CmpAccountID', a_id),
             ReturnDict('Found in SFDC Search #2', 0), ReturnDict('Num Adding', 0),
             ReturnDict('Num Removing', 0), ReturnDict('Num Updating/Staying', 0),
             ReturnDict('SFDC Session', sfdc)]
    ret_items = dict([(i.item, i.emailVar) for i in Items])
    return ret_items


def lists_in_queue(var_list):
    '''
    determines if there are any lists in the queue.

    :param var_list: dictionary of list variables.
    :return: boolean TRUE / FALSE
    '''
    if var_list['Lists_In_Queue'] > 0:
        return True
    else:
        print 'No lists to process. Will check back in 1 hour.'
        return False


def close_mailbox_connection(M):
    '''
    closes the mailbox connection

    :param M: mailbox object
    :return: dictionary of mailbox information.
    '''
    print 'Closing email_handler connection.'
    M.close()
    M.logout()
    return {'Mailbox': None}


def craft_notification_email(items):
    """
    creates the actual text values of the email.

    :param items: dictionary items for stats processing
    :return: body of email.
    """
    body = '''%s,

    Your list attached to %s has been processed. Below are the results of
    the program. All files generated by the search program that require further research have been attached.

    If you have questions, please reach out to:
    %s
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
    - Automated List Management App (ALM)''' % (items[0], items[1],
                                                items[2], items[3],
                                                items[4], items[5],
                                                items[6], items[7],
                                                items[8], items[9],
                                                items[10], items[11],
                                                items[12], items[13],
                                                items[14], items[15],
                                                items[16], items[17],
                                                items[18])
    return body
