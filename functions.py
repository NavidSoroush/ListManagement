# this is for random functions that the list program will use
import os
import email
import base64
import datetime
import time
from pyEmailComplete import newListReceived_notifyOriginator
from testing_DL_script import list_download


################################################################
##These functions should be used to process file names and paths

def splitname(pathtosplit):
    '''
    splits a path into directory and file name

    :param pathtosplit: path to file (required)
    :return: name of file
    '''

    import os
    name = os.path.split(os.path.abspath(pathtosplit))
    return name[1]


def shorten_filename_to95char(fname):
    '''
    evaulates if the file name is longer than 95 characters.
    if so, then it shortens it

    :param fname: original filename
    :return: formatted / shortened file name
    '''
    extensionLength, file_ext = determineExtensionType(fname)
    fname = fname[:-extensionLength]
    max_fname_chars = 95 - extensionLength

    if len(fname) > max_fname_chars:
        fname = fname[:max_fname_chars] + file_ext

    return fname


def determineExtensionType(fname):
    '''
    determines the extension type of the file.

    :param fname: original file name (required)
    :return: tuple of shorten file name and file extension
    '''
    filename, file_ext = os.path.splitext(fname)
    if file_ext == '.csv' or file_ext == '.pdf' or file_ext == '.xls':
        shortLen = 4
    if file_ext == '.xlsx':
        shortLen = 5

    del filename
    return shortLen, file_ext


################################################################
##These functions and variables will be used for email processing when a new
##list is received.
listUploadStr = ['An upload list has been added'
    , 'An upload list has been added to'
    , 'by', 'Account Link: '
    , 'Attachment Link: '
    , 'BizDev Group Link: ']

Object_Check = ['Campaign', 'BizDev Group']


class returnDict(object):
    def __init__(self, item, emailVar):
        self.item = item
        self.emailVar = emailVar


def getMsgPart(mPart, array):
    '''
    decodes the email body from the email data

    :param mPart: coded message string (required)
    :param array: items to parse
    :return: decoded text of email message
    '''
    msg = email.message_from_string(array[1])
    decode = email.Header.decode_header(msg[mPart])[0]
    tmp = unicode(decode[0], 'utf-8')
    return tmp


def emailParser(senderName, look1, look2=None):
    '''
    parses the body text of an email message

    :param senderName: text of an email message (required)
    :param look1: start / end location of the text to parse (required)
    :param look2: optional - takes a secondary substring if finding text
    :return: parsed substring
    '''
    finder = senderName.find(look1)
    if look2 is not None:
        finder2 = senderName.find(look2)
        tmpStr = senderName[finder + 1:finder2]
    else:
        tmpStr = senderName[:finder]

    return tmpStr


def listInfoParser(bodyStr, lookingFor, lookingFor2=None, n=None):
    '''
    parses the body text of an email message

    :param bodyStr: text of an email message (required)
    :param lookingFor: start / end location of the text to parse (required)
    :param lookingFor2: optional - takes a secondary substring if finding text
    :param n: length of where attachment link is
    :return: parsed substring
    '''
    if n is None:
        n = 2

    if lookingFor == 'Campaign Link: ' or lookingFor == 'Attachment Link: ':
        incr = 40
    else:
        incr = 1

    lfStart = bodyStr.find(lookingFor)
    tmpStr = bodyStr[len(lookingFor) + incr + lfStart:]
    if lookingFor2 is not None:
        lf2Start = bodyStr.find(lookingFor2)
        tmpStr = tmpStr[:lf2Start - len(lookingFor) - n]
    return tmpStr


def decode_mailitem(mail_data):
    '''
    decode mail item (remove all base64 bits)

    :param mail_data: coded mail body text (required)
    :return: decoded body text
    '''

    msg = email.message_from_string(mail_data)
    encodedBody = bodyParse(msg, listUploadStr[0])
    body = msg.get_payload()
    decodedBody = base64.b64decode(body)
    return decodedBody


def bodyParse(message, s_string):
    tmpObj = str(message)
    start1 = tmpObj.find(s_string)
    tmpObj = tmpObj[start1 + 29:]
    start2 = tmpObj.find(s_string)
    mailBody = tmpObj[start2:]
    return mailBody


def process_list_email(email_data, M):
    '''
    creates initial meta data required for list processing.

    :param email_data: email string
    :param M: mailbox object
    :return: dictionary of values needed for list processing.
    '''

    ## need to adjust all of the variables (decoded body, data[0]) to the
    ## variables that are passed to the process_list_email function
    data = email_data[0]
    decodedBody = email_data[1]
    num = email_data[2]

    if Object_Check[0] in decodedBody:
        obj = Object_Check[0]
    elif Object_Check[1] in decodedBody:
        obj = Object_Check[1]
    else:
        obj = 'Account'

    recDate = getMsgPart('date', data)
    sentFrom = getMsgPart('From', data)
    senderName = emailParser(sentFrom, ' <')
    sentFrom = emailParser(sentFrom, '<', '>')

    obj_rec_Name = listInfoParser(decodedBody, listUploadStr[1],
                                  listUploadStr[2])
    obj_rec_Link = listInfoParser(decodedBody, listUploadStr[3],
                                  listUploadStr[4])

    attLink = listInfoParser(decodedBody, listUploadStr[4])

    if obj == 'Campaign':
        obj_rec_Link = obj_rec_Link[-18:]
    elif obj == 'BizDev Group':
        obj_rec_Link = listInfoParser(decodedBody, listUploadStr[5],
                                      listUploadStr[4])
        obj_rec_Link = obj_rec_Link[26:44]
    else:
        obj_rec_Link = obj_rec_Link[26:44]
    filePath, startDate, pre_orPost, aName, aID = list_download([attLink[:18]],
                                                                obj,
                                                                obj_rec_Link)
    ##    print 'Would download file now.'
    ##    filePath='Test File Name'
    ##    startDate='Dummy Date'
    ##    pre_orPost='Does not matter.'
    ##    aName='Test Account Name'
    ##    aID='1234'
    try:
        newListReceived_notifyOriginator(sentFrom, senderName,
                                         obj_rec_Name, obj)
        # newListReceived_notifyListMGMT(senderName, cmpgnName, cmpLink, obj)
    except:
        pass
    M.copy(num, 'INBOX/Auto Processed Lists')
    M.store(num, '+FLAGS', r'(\Deleted)')
    M.expunge()
    ts = time.time()
    pstart = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    Items = [returnDict('Object', obj), returnDict('Record Name', obj_rec_Name),
             returnDict('Sender Email', sentFrom), returnDict('Sender Name', senderName),
             returnDict('Received Date', recDate), returnDict('File Path', filePath),
             returnDict('Campaign Start Date', startDate), returnDict('Next Step', 'Pre-processing'),
             returnDict('Found Path', None), returnDict('ObjectId', obj_rec_Link),
             returnDict('Pre_or_Post', pre_orPost), returnDict('processStart', pstart),
             returnDict('CmpAccountName', aName), returnDict('CmpAccountID', aID),
             returnDict('Found in SFDC Search #2', 0), returnDict('Num Adding', 0),
             returnDict('Num Removing', 0), returnDict('Num Updating/Staying', 0)]
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
    print 'Closing email connection.'
    M.close()
    M.logout()
    return {'Mailbox': None}
