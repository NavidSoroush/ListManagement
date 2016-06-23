import smtplib
import string
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders
from cred import username, password, userPhone, outlook_userEmail, userName


def attachments(att_paths, msg):
    for att in att_paths:
        if att!=None:
            with open(str(att), 'rb') as f:
                part = MIMEBase('application','vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                part.set_payload(f.read())
                part.add_header('Content-Disposition',
                    'attachment; filename="%s"' % os.path.basename(str(att)))
                Encoders.encode_base64(part)
                msg.attach(part)
    return msg

def sfdcBatchComplete():
    SUBJECT = "Python SFDC SQL Query Batch Complete"
    TO = "ricky.schools@franklinsquare.com;max.charles@franklinsquare.com"
    FROM = "lists@franklinsquare.com"
    text = "The SFDC search file has been added to the Search Program Dropbox. \n \n - List Management App"
    BODY = string.join(("From: %s" % FROM,
                        "To: %s" % TO,
                        "Subject: %s" % SUBJECT,
                        "",
                        text),"\r\n")
    sendEmail(FROM, TO, BODY)
    return 'success.'

def newListReceived_notifyOriginator(emailTO, emailName, evnt_campaign,sfObj):
    SUBJECT = "ALM Notification: List attached to %s received." % evnt_campaign
    TO = emailTO
    FROM = "lists@franklinsquare.com"
    TEXT = '%s, \n \nThe list that you attached to the %s object, %s has been added to our list queue. You will receive a notification after your list has been processed. \n \n- Automated List Management App (ALM)' % (emailName, sfObj ,evnt_campaign)
    BODY = string.join(("From: %s" % FROM,
                        "To: %s" % TO,
                        "Subject: %s" % SUBJECT,
                        "",
                        TEXT),"\r\n")
    sendEmail(FROM, TO, BODY)
    print 'Success email sent to originator.'

def newListReceived_notifyListMGMT(emailName, evnt_campaign, obj_link,sfObj):
    SUBJECT = "New list received from %s attached to %s has been received." % (emailName,evnt_campaign)
    TO = "ricky.schools@franklinsquare.com;max.charles@franklinsquare.com"
    FROM = "lists@franklinsquare.com"
    TEXT = "New list received from %s. \nIt's been attached to the %s object, %s and it's link is: %s. \n \n- Automated List Management App (ALM)" %(emailName, sfObj, evnt_campaign, obj_link)
    BODY = string.join(("From: %s" % FROM,
                        "To: %s" % TO,
                        "Subject: %s" % SUBJECT,
                        "",
                        TEXT),"\r\n")
    sendEmail(FROM, TO, BODY)
    print 'Team notificaiton email sent.'


def emailComplete(emailTo, recName, bodyString, att_paths=[],msg = MIMEMultipart()):
    TEXT=bodyString
    FROM ='lists@franklinsquare.com'
    TO=emailTo
    SUBJECT="ALM Notification: %s list processed." % recName
    msg['From']=FROM
    msg['To']=TO
    msg['Subject']=SUBJECT
    msg.attach(MIMEText(''.join(TEXT)))
    
    if len(att_paths)>0:
        msg=attachments(att_paths, msg)


    BODY = string.join(("From: %s" % FROM,
                        "To: %s" % TO,
                        "Subject: %s" % SUBJECT,
                        "",
                        TEXT),"\r\n")
    sendEmail(FROM, TO, BODY, msg)
    print '\nCompletion email sent to originator with stats.'
    
def sendEmail(FROM, TO, BODY, mess=None):
    server = smtplib.SMTP("smtp.office365.com",587)
    server.ehlo()
    server.starttls()
    server.login(outlook_userEmail,password)
    if mess==None:
        server.sendmail(FROM,[TO],BODY)
    else:
        server.sendmail(FROM, [TO], mess.as_string())
    server.quit()


##for testing
##if __name__=='__main__': 
##    d={'total':10,'sfFound':6,'up_toDate':5,'update':1
##       ,'create':3,'needResearch':1,'received':'1/1/2016 00:00:00'
##       ,'complete':'1/1/2016 00:02:25','processingTime':'2 min, 25 sec'}
##    path=['T:/Shared/FS2 Business Operations/Python Search Program/New Lists/PAG All Advisors 6.3.16 New May 16/PAG All Advisors 6.3.16 New May 16_bdgUpdate.xlsx',
##          'T:/Shared/FS2 Business Operations/Python Search Program/New Lists/PAG All Advisors 6.3.16 New May 16/PAG All Advisors 6.3.16 New May 16_nocrd.xlsx']
##    emailComplete('ricky.schools@franklinsquare.com','Test_CMP', 'Testing Body',path)
