import datetime
from dateutil import parser
from cred import userPhone, userEmail, userName
from pyEmailComplete import emailComplete
from functions import splitname
import time
import pandas as pd


def cleanDate(received):
    '''
    parses time value and returns date

    :param received: timestamp
    :return: transformed timestamp value
    '''
    received = parser.parse(received)
    received = received.replace(tzinfo=None)
    return received


def stringDate(value):
    '''
    take timestamp and return string version of value.

    :param value: timestamp
    :return: str value of timestamp
    '''
    value = datetime.datetime.strftime(value, '%d/%m/%Y %H:%M:%S')
    return value


def determine_num_records(path):
    df = pd.read_excel(path)
    if 'found' in path:
        num = len(df[df['ContactID'] != ''])
    del df
    return num


def convert_timedelta(duration):
    '''
    returns the elapsed time for list processing

    :param duration: end time - start time
    :return: string of elapsed time
    '''
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = (seconds % 60)
    processingString = '{} days {} hours {} minutes {} seconds'.format(days,
                                                                       hours,
                                                                       minutes,
                                                                       seconds)
    return processingString


def valuesForEmail(dictValues):
    '''
    from all values created by list processing, creates email
    to send by to list requester.

    :param dictValues: dictionary of values created by list program processing.
    :return: stats for record keeping
    '''
    ts = time.time()
    timeNow = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    if dictValues['Object'] == 'Campaign':
        toUpdate = dictValues['Num Campaign Upload']
        toCreate = dictValues['Num to Create Cmp']
        objToAdd = dictValues['Num Adding']
        objToRemove = dictValues['Num Removing']
        objToUpdate = dictValues['Num Updating/Staying']

    else:
        toUpdate = dictValues['Num To Update']
        toCreate = dictValues['Create']
        objToAdd = dictValues['Num Adding']
        objToRemove = dictValues['Num Removing']
        objToUpdate = dictValues['Num Updating/Staying']

    if not dictValues['Move To Bulk']:
        createAdvisorsNote = 'Contacts will not be created. Not enough information provided.'
    else:
        createAdvisorsNote = ''

    obj = dictValues['Object']
    if obj == 'BizDev Group':
        if not dictValues['FINRA?']:
            att_paths = [dictValues['File Path'], dictValues['Review Path'], dictValues['BDG Remove'],
                         dictValues['BDG Add'], dictValues['BDG Stay']]
        else:
            att_paths = [dictValues['No CRD'], dictValues['FINRA Ambiguous'],
                         dictValues['Review Path'], dictValues['BDG Remove'],
                         dictValues['BDG Add'], dictValues['BDG Stay']]
    elif not dictValues['FINRA?']:
        att_paths = [dictValues['File Path'], dictValues['No CRD'], dictValues['FINRA Ambiguous'],
                     dictValues['Review Path']]
    else:
        att_paths = [dictValues['Review Path']]

    total = dictValues['Total Records']
    fileName = splitname(dictValues['File Path'])
    # num_foundInSFDC = dictValues['Found in SFDC Search #2'] + dictValues['SFDC_Found'] - toCreate
    num_foundInSFDC = determine_num_records(dictValues['Found Path']) - toCreate
    need_Research = total - num_foundInSFDC - toCreate
    received = cleanDate(dictValues['Received Date'])
    ts_received = stringDate(received)
    processStart = dictValues['processStart']
    completed = timeNow
    processingTime = cleanDate(completed) - cleanDate(processStart)
    processingString = convert_timedelta(processingTime)
    objName = dictValues['Record Name']
    obj = dictValues['Object']
    num_notUpdating = dictValues['Num Not Updating']
    senderName = dictValues['Sender Name']
    senderEmail = dictValues['Sender Email']
    matchRate = (num_foundInSFDC + toCreate) / float(total)
    itemsToEmail = [senderName, objName, userName, userPhone,
                    userEmail, total, num_foundInSFDC, toUpdate,
                    num_notUpdating, toCreate, objToAdd, objToUpdate,
                    objToRemove, need_Research, received, processStart,
                    completed, processingString, createAdvisorsNote]
    bodyString = craftEmail(itemsToEmail)

    items_forStats = {'File Name': fileName, 'Received Date': ts_received, 'Received From': senderName
        , 'Created By': userName, 'File Type': obj, 'Advisors on List': total
        , 'Advisors w/CID': num_foundInSFDC, 'Advisors w/CID old Contact Info': num_notUpdating
        , 'CRD Found Not in SFDC': toCreate, 'Creating': toCreate
        , 'Unable to Find': need_Research, 'Last Search Date': completed
        , 'Match Rate': matchRate, 'Processing Time': processingString}

    emailComplete(senderEmail, objName, bodyString, att_paths)
    return {'Next Step': 'Record Stats',
            'Stats Data': items_forStats}


def craftEmail(items):
    '''
    creates the actual text values of the email.

    :param items: dictionary items for stats processing
    :return: body of email.
    '''
    BODY = '''%s,

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
    return (BODY)

##for testing
##i=['Ricky','CMP_TEST','MC','##','email',10,8,6,4,1,'1/1/2015','1/2/2015','1Day']
##print craftEmail(i)
