import imaplib
from cred import password, sfuser, sfpw, outlook_userEmail
from functions import getMsgPart, decode_mailitem, lists_in_queue
import sys

# declaring global variables
EMAIL_ACCOUNT = outlook_userEmail + '/Lists'
EMAIL_FOLDER = 'INBOX/Auto Lists From SFDC/'
listUploadStr = ['An upload list has been added'
    , 'An upload list has been added to'
    , 'by', 'Account Link: '
    , 'Attachment Link: '
    , 'BizDev Group Link: ']
Object_Check = ['Campaign', 'BizDev Group']

payload = {
    'action': 'login',
    'username': sfuser,
    'pw': sfpw
}


# Creating new mailbox processes to create a list queue

def process_mailbox(M, list_queue=[]):
    '''
    Process mail identifies new list requests and returns
    the data to the main_module so all can be properly processed.

    :param M: Mailbox object
    :param list_queue: stores email data for all pending lists
    :return: dictionary of data used to guide list processing
    '''
    rv, data = M.search(None, "ALL")
    if rv != 'OK':
        print "No messages found!"
        return

    for num in data[0].split():
        rv, data = M.fetch(num, '(RFC822)')
        if rv != 'OK':
            print "ERROR getting message", num
            return
        else:
            subject = getMsgPart('Subject', data[0])
            if listUploadStr[0] in subject:
                decoded = decode_mailitem(data[0][1])
                list_queue.append([data[0], decoded, num])

    items = {'Lists_In_Queue': len(list_queue),
             'Num_Processed': 0,
             'Lists_Data': list_queue}

    return items


def checkForLists():
    '''
    Instantiates the Mailbox object. Receives the list data from
    process_mailbox and returns it to the main_module.

    :return: dictionary of data used to guide list processing
    '''

    M = imaplib.IMAP4_SSL('outlook.office365.com')
    try:
        rv, data = M.login(EMAIL_ACCOUNT, password)
    except imaplib.IMAP4.error:
        print "LOGIN FAILED!!! "
        sys.exit(1)

    print 'Mailbox: ', rv, data

    rv, mailboxes = M.list()
    var_list = []
    rv, data = M.select(EMAIL_FOLDER)
    if rv == 'OK':
        print "\nStep 1:\nLooking for list uploads."
        var_list = process_mailbox(M)

        if lists_in_queue(var_list) == False:
            var_list.update(close_mailbox_connection(M))

        else:
            print 'There are %s lists to process.' % var_list['Lists_In_Queue']
            var_list.update({'Mailbox': M})

        return var_list
    else:
        print "ERROR: Unable to open mailbox ", rv

##for testing
##checkForLists()
