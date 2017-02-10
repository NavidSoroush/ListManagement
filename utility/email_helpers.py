import email_handler
import time
import datetime
import base64

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
    msg = email_handler.message_from_string(array[1])
    decode = email_handler.Header.decode_header(msg[msg_part])[0]
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
    msg = email_handler.message_from_string(mail_data)
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


def process_list_email(email_data, M):
    """
    creates initial meta data required for list processing.
    :param email_data: email_handler string
    :param M: mailbox object
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

    obj_rec__name = info_parser(decoded_body, _list_notification_elements[1],
                                _list_notification_elements[2])
    obj_rec__link = info_parser(decoded_body, _list_notification_elements[3],
                                _list_notification_elements[4])

    attLink = info_parser(decoded_body, _list_notification_elements[4])

    if obj == 'Campaign':
        obj_rec__link = obj_rec__link[-18:]
    elif obj == 'BizDev Group':
        obj_rec__link = info_parser(decoded_body, _list_notification_elements[5],
                                    _list_notification_elements[4])
        obj_rec__link = obj_rec__link[39:58]
    else:
        obj_rec__link = obj_rec__link[39:58]
    filePath, startDate, pre_orPost, aName, aID = list_download([attLink[:18]],
                                                                obj,
                                                                obj_rec__link)

    try:
        print('move this to somewhere else.')
        # newListReceived_notifyOriginator(sent_from, sender_name,
        #                                  obj_rec__name, obj)
        # newListReceived_notifyListMGMT(sender_name, cmpgnName, cmpLink, obj)
    except:
        pass
    M.copy(num, 'INBOX/Auto Processed Lists')
    M.store(num, '+FLAGS', r'(\Deleted)')
    M.expunge()
    ts = time.time()
    pstart = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    Items = [ReturnDict('Object', obj), ReturnDict('Record Name', obj_rec__name),
             ReturnDict('Sender Email', sent_from), ReturnDict('Sender Name', sender_name),
             ReturnDict('Received Date', rec_date), ReturnDict('File Path', filePath),
             ReturnDict('Campaign Start Date', startDate), ReturnDict('Next Step', 'Pre-processing'),
             ReturnDict('Found Path', None), ReturnDict('ObjectId', obj_rec__link),
             ReturnDict('Pre_or_Post', pre_orPost), ReturnDict('processStart', pstart),
             ReturnDict('CmpAccountName', aName), ReturnDict('CmpAccountID', aID),
             ReturnDict('Found in SFDC Search #2', 0), ReturnDict('Num Adding', 0),
             ReturnDict('Num Removing', 0), ReturnDict('Num Updating/Staying', 0)]
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

