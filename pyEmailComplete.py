import smtplib
import string
import os
from cred import username, password, userPhone, userEmail, userName


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


def emailComplete(emailTo, recName, bodyString):
    SUBJECT = "ALM Notification: %s list processed." % recName
    TO= emailTo
    FROM='lists@franklinsquare.com'
    TEXT=bodyString
    BODY = string.join(("From: %s" % FROM,
                        "To: %s" % TO,
                        "Subject: %s" % SUBJECT,
                        "",
                        TEXT),"\r\n")
    sendEmail(FROM, TO, BODY)
    print '\nCompletion email sent to originator with stats.'
    
def sendEmail(FROM, TO, BODY):
    server = smtplib.SMTP("smtp.office365.com",587)
    server.ehlo()
    server.starttls()
    server.login(userEmail,password)
    server.sendmail(FROM,[TO],BODY)
    server.quit()


##for testing
##if __name__=='__main__': 
##    d={'total':10,'sfFound':6,'up_toDate':5,'update':1
##       ,'create':3,'needResearch':1,'received':'1/1/2016 00:00:00'
##       ,'complete':'1/1/2016 00:02:25','processingTime':'2 min, 25 sec'}
##    emailComplete('ricky.schools@franklinsquare.com','Ricky Schools'
##                  , recName='Test_CMP', objName='Campaign',stats=d)
