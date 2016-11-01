import time
from cred import sfuser, sfpw, sf_token
import SQLForce
from SQLForce import AttachmentReader
import os
import errno
import shutil
from dateutil import parser
import datetime

yot = time.strftime("%Y")
sPath = ['T:/Shared/FS2 Business Operations/Python Search Program/New Lists/']

sfuser2 = "fsinvestments.my.salesforce.com:" + sfuser


##for testing
##sPath=['C:/Users/rschools/Downloads/ListDownloadTesting/']

def splitname(pathtosplit):
    '''
    splits the directory name into folder location and file name.

    :param pathtosplit: directory to a file
    :return: filename of path
    '''
    import os
    name = os.path.split(os.path.abspath(pathtosplit))
    return name[1]


def drivepresent(fname, paths):
    '''
    attempts to identify if a directory is available and create a copy of
    a file in 'destination' location. if not, it attempts to create the
    directory and then moves the file.

    :param fname: original file name
    :param paths: list of paths 0) original path, 1) destination
    :return: N/A
    '''
    if not os.path.isdir(paths):
        try:
            os.makedirs(paths)
        except OSError:
            if OSError.errno == errno.EEXIST and os.path.isdir(paths):
                pass
            else:
                raise

    shutil.copy(fname[0], paths)


def detExt(fname):
    '''
    identifies the extension of a file.

    :param fname: path or file name
    :return: len of the extension
    '''
    filename, file_ext = os.path.splitext(fname)
    if file_ext.lower() == '.csv' or file_ext.lower() == '.pdf' or file_ext.lower() == '.xls':
        shortLen = 4
    if file_ext.lower() == '.xlsx':
        shortLen = 5

    del filename
    return shortLen


def convert_uniToDate(date_string):
    '''
    transforms a date-string to a date. based on the date
    determines if a campaign has happened or if it is upcoming.

    :param date_string: string of a date value.
    :return: variable, is the list pre or post.
    '''
    date_string = parser.parse(date_string)
    today = datetime.datetime.now()
    diff = today - date_string
    if diff.days > 0:
        list_prePost = 'Post'
    else:
        list_prePost = 'Pre'
    return (date_string, list_prePost)


def create_moveNewFile(attPath):
    '''
    takes a file path, and from the file's name, it creates
    a new folder for the file.

    :param attPath: file path
    :return: the new path of the file passed to the function.
    '''
    startPath = attPath[0]
    fname = splitname(attPath[0])
    shortenLen = detExt(fname)
    newPath = startPath[:-int(shortenLen)]
    if not os.path.isdir(newPath):
        try:
            os.makedirs(newPath)
        except OSError:
            if OSError.errno == errno.EEXIST and os.path.isdir(newPath):
                pass
            else:
                raise

    shutil.copy(startPath, newPath)
    newPath = newPath + '/' + fname
    os.remove(startPath)
    return newPath


def list_download(att_id, sfObj, objLink):
    '''
    downloads the new list from SFDC for processing.

    :param att_id: SFDC attachment id
    :param sfObj: Object of the attachment
    :param objLink: Link to the SFDC object
    :return: tuple of variables used by main_module for list processing.
    '''
    session = SQLForce.Session('Production', sfuser, sfpw, sf_token)

    print '\nStep 2:\nSFDC session established.'
    attachment = AttachmentReader.exportByAttachmentIds(session,
                                                        attachmentIds=att_id,
                                                        outputDir=sPath[0],
                                                        createSubDirs=False)

    ##    drivepresent(attachment, sPath[1])
    eventDate = None
    preORpost = None
    accountName = None
    aID = None
    if sfObj == 'Campaign':
        sql = 'SELECT StartDate,Account__c FROM Campaign Where id=' + '"{}"'.format('" "'.join([objLink[-18:]]))
        for rec in session.selectRecords(sql):
            eventDate, preORpost = convert_uniToDate(rec.StartDate)
            aID = rec.Account__c
        if aID != None:
            sql2 = 'SELECT Name FROM Account Where id=' + '"{}"'.format('" "'.join([aID]))
            for rec in session.selectRecords(sql2):
                accountName = rec.Name
    elif sfObj == 'BizDev Group':
        sql = 'SELECT Name,Account__c FROM BizDev__c Where id=' + '"{}"'.format('" "'.join([objLink[:18]]))
        for rec in session.selectRecords(sql):
            aID = rec.Account__c
        if aID is not None:
            sql2 = 'SELECT Name FROM Account Where id=' + '"{}"'.format('" "'.join([aID]))
            for rec in session.selectRecords(sql2):
                accountName = rec.Name

    session.logout()
    SQLForce.SQLForceServer.killServer()
    print 'Download successful.'
    print(attachment)
    attachment = create_moveNewFile(attachment)
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
