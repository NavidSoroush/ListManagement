import time
from cred import sfuser, sfpw, sf_token
import SQLForce
from SQLForce import AttachmentReader
import errno
import os
import errno
import shutil
from dateutil import parser
import datetime


yot = time.strftime("%Y")
sPath= ['T:/Shared/FS2 Business Operations/Python Search Program/New Lists/']
##        'Y:/Business_Intelligence_Analytics/Lists - Archives/'+yot+'OrigListArch/']

##for testing
##sPath=['C:/Users/rschools/Downloads/ListDownloadTesting/']

def splitname(pathtosplit):
    import os
    name = os.path.split(os.path.abspath(pathtosplit))
    return name[1]

def drivepresent(fname, paths):
    if not os.path.isdir(paths):
        try:
            os.makedirs(paths)
        except OSError:
            if OSError.errno == errno.EEXIST and os.path.isdir(paths):
                pass
            else: raise
            
    shutil.copy(fname[0],paths)

def detExt(fname):
    filename, file_ext=os.path.splitext(fname)
    if file_ext.lower()=='.csv' or file_ext.lower()=='.pdf' or file_ext.lower()=='.xls':
        shortLen=4
    if file_ext.lower()=='.xlsx':
        shortLen=5

    del filename   
    return shortLen

def convert_uniToDate(date_string):
    date_string=parser.parse(date_string)
    today=datetime.datetime.now()
    diff=today-date_string
    if diff.days > 0:
        list_prePost='Post'
    else:
        list_prePost='Pre'
    return (date_string,list_prePost)

def create_moveNewFile(attPath):
    startPath=attPath[0]
    fname=splitname(attPath[0])
    shortenLen=detExt(fname)
    newPath=startPath[:-int(shortenLen)]
    if not os.path.isdir(newPath):
        try:
            os.makedirs(newPath)
        except OSError:
            if OSError.errno == errno.EEXIST and os.path.isdir(newPath):
                pass
            else: raise
            
    shutil.copy(startPath,newPath)
    newPath=newPath+'/'+fname
    os.remove(startPath)
    return newPath
    
    
    

def list_download(att_id, sfObj, objLink):
    session = SQLForce.Session('Production',sfuser,sfpw,sf_token)
    print '\nStep 2:\nSFDC session established.'
    attachment = AttachmentReader.exportByAttachmentIds(session,att_id,
                                                        sPath[0],
                                                       createSubDirs=False)                               

##    drivepresent(attachment, sPath[1])
    eventDate = None
    preORpost = None
    accountName=None
    aID=None
    if sfObj == 'Campaign':
        sql = 'SELECT StartDate,Account__c FROM Campaign Where id='+'"{}"'.format('" "'.join([objLink[-18:]]))
        for rec in session.selectRecords(sql): 
            eventDate, preORpost=convert_uniToDate(rec.StartDate)
            aID=rec.Account__c
        if aID != None:
            sql2='SELECT Name FROM Account Where id='+'"{}"'.format('" "'.join([aID]))
            for rec in session.selectRecords(sql2):
                accountName=rec.Name
    elif sfObj == 'BizDev Group':
        sql = 'SELECT Name,Account__c FROM BizDev__c Where id='+'"{}"'.format('" "'.join([objLink[-18:]]))
        for rec in session.selectRecords(sql): 
            aID=rec.Account__c
        if aID != None:
            sql2='SELECT Name FROM Account Where id='+'"{}"'.format('" "'.join([aID]))
            for rec in session.selectRecords(sql2):
                accountName=rec.Name
                
    session.logout()
    SQLForce.SQLForceServer.killServer()
    print 'Download successful.'
    attachment=create_moveNewFile(attachment)
    return (attachment, eventDate, preORpost, accountName, aID)


##for testing
##att = ['00PE000000SqO9GMAV']
##obj = 'BizDev Group'
##obj_link = 'a0vE00000069dt3IAA'
##link, eD, pop,aName, aID=list_download(att,obj,obj_link)
##
##print link
##print eD
##print pop
##print aName
##print aID
