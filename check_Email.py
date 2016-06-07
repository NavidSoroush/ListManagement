import smtplib
import imaplib
from cred import username, password, sfuser, sfpw, outlook_userEmail
from testing_DL_script import list_download
from pyEmailComplete import newListReceived_notifyOriginator, newListReceived_notifyListMGMT
import getpass
import email
import base64
import datetime
import sys
import time

EMAIL_ACCOUNT=outlook_userEmail+'/Lists'
EMAIL_FOLDER='INBOX/Auto Lists From SFDC/'
listUploadStr=['An upload list has been added'
               ,'An upload list has been added to'
               ,'by','Account Link: '
               , 'Attachment Link: ']
Object_Check = ['Campaign', 'BizDev Group']


payload = {
    'action': 'login',
    'username': sfuser,
    'pw': sfpw
}

class returnDict(object):
    def __init__(self, item, emailVar):
        self.item = item
        self.emailVar = emailVar

def getMsgPart(mPart,array):
    msg = email.message_from_string(array[1])
    decode =email.Header.decode_header(msg[mPart])[0]
    tmp = unicode(decode[0], 'utf-8')
    return tmp

def emailParser(senderName,look1,look2=None):
    finder = senderName.find(look1)
    if look2 is not None:
        finder2 = senderName.find(look2)
        tmpStr = senderName[finder+1:finder2]
    else:
        tmpStr = senderName[:finder]

    return tmpStr

def listInfoParser(bodyStr,lookingFor,lookingFor2=None,n=None):
    if n is None:
        n = 2
        
    if lookingFor=='Campaign Link: ' or lookingFor =='Attachment Link: ':
        incr = 27
    else:
        incr = 1
        
    lfStart=bodyStr.find(lookingFor)
    tmpStr=bodyStr[len(lookingFor)+incr+lfStart:]   
    if lookingFor2 is not None:
        lf2Start=bodyStr.find(lookingFor2)
        tmpStr=tmpStr[:lf2Start-len(lookingFor)-n]
    return tmpStr
    
def bodyParse(message,s_string):
    tmpObj=str(message)
    start1=tmpObj.find(s_string)
    tmpObj=tmpObj[start1+29:]
    start2=tmpObj.find(s_string)
    mailBody=tmpObj[start2:]
    return mailBody

def process_mailbox(M):
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
            subject = getMsgPart('Subject',data[0])
            if listUploadStr[0] in subject:
                print 'List found, attempting to download.'
                msg = email.message_from_string(data[0][1])
                encodedBody=bodyParse(msg,listUploadStr[0])
                body = msg.get_payload()
                decodedBody = base64.b64decode(body)
                recDate = getMsgPart('date',data[0])
                if Object_Check[0] in decodedBody:
                    obj = Object_Check[0]
                elif Object_Check[1] in decodedBody:
                    obj = Object_Check[1]
                else:
                    obj = 'Account'
                obj_rec_Name=listInfoParser(decodedBody,listUploadStr[1],listUploadStr[2])
                obj_rec_Link=listInfoParser(decodedBody,listUploadStr[3],listUploadStr[4])
                attLink=listInfoParser(decodedBody,listUploadStr[4])
                sentFrom = getMsgPart('From',data[0])
                senderName = emailParser(sentFrom,' <')
                sentFrom = emailParser(sentFrom,'<','>')
                #comment here for spacing
                if obj=='Campaign':
                    obj_rec_Link=obj_rec_Link[-18:]
                else:
                    obj_rec_Link=obj_rec_Link[26:44]
                filePath,startDate,pre_orPost,aName, aID = list_download([attLink[:18]], obj, obj_rec_Link)
                try:
                    newListReceived_notifyOriginator(sentFrom,senderName,obj_rec_Name,obj)
                    #newListReceived_notifyListMGMT(senderName, cmpgnName, cmpLink, obj)
                except:
                    pass
                M.copy(num,'INBOX/Auto Processed Lists')
                M.store(num,'+FLAGS', r'(\Deleted)')
                M.expunge()
                ts=time.time()
                pstart=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')               
                Items = [returnDict('Object',obj), returnDict('Record Name',obj_rec_Name),
                 returnDict('Sender Email', sentFrom), returnDict('Sender Name', senderName),
                 returnDict('Received Date', recDate),returnDict('File Path', filePath),
                 returnDict('Campaign Start Date', startDate), returnDict('Next Step','Pre-processing'),
                 returnDict('Found Path', None), returnDict('ObjectId',obj_rec_Link),
                 returnDict('Pre_or_Post',pre_orPost), returnDict('processStart',pstart),
                 returnDict('CmpAccountName',aName), returnDict('CmpAccountID',aID),
                 returnDict('Found in SFDC Search #2',0)]
                retItems = dict([(i.item, i.emailVar) for i in Items])
                return retItems
            else:
                print 'No new lists found. Next search will occur in 1 hour.'

        
        


def checkForLists():        
    M= imaplib.IMAP4_SSL('outlook.office365.com')
    try:
        rv, data = M.login(EMAIL_ACCOUNT, password)
    except imaplib.IMAP4.error:
        print "LOGIN FAILED!!! "
        sys.exit(1)

    print 'Mailbox: ',rv, data

    rv, mailboxes = M.list()

    var_list = []
    rv, data = M.select(EMAIL_FOLDER)
    if rv == 'OK':
        print "\nStep 1:\nLooking for list uploads."
        var_list = process_mailbox(M)
        print 'Closing email connection.'
        M.close()
##
##        for k,v in var_list.iteritems():
##            print '%s: %s' % (k,v)
        return var_list
    else:
        print "ERROR: Unable to open mailbox ", rv

    
    M.logout()

##for testing
##checkForLists()
