from check_Email import checkForLists
from trainHeadersModelv1 import training
from SearchSFDC import searchone, searchtwo, searchsec
from FINRA_search import fin_search
from parse_Files import parseList
from upload_Prep import sourceChannel
from cmpUpload import extract_pdValues
from bulkProcessing import copy_toBulkProcessing
from dictExtraction import valuesForEmail
from recordStats import recordStats

if __name__=="__main__":
    var_list=[]
    
    var_list=checkForLists()
    
    if var_list['Object']!='Account':
        var_list.update(training(var_list['File Path'],var_list['CmpAccountName']))
    else:
        var_list.update(training(var_list['File Path'],var_list['Record Name']))
        
    var_list.update(searchone(var_list['File Path'],var_list['Object']))
    
    if var_list['SFDC_Found']<var_list['Total Records'] and var_list['FINRA?'] == True:
        var_list.update(fin_search(var_list['File Path'],var_list['Found Path']))
        if var_list['SFDC_Found']+var_list['FINRA_Found']<var_list['Total Records']:
            var_list.update(searchsec(var_list['No CRD'],var_list['FINRA_SEC Found']))
        else:
            print '\nSkipping step 6, because all contacts were found.'
        var_list.update(searchtwo(var_list['FINRA_SEC Found'],var_list['Found Path'],var_list['Object'])) 
    else:
        print '\nSkipping email, LkupName, FINRA and SEC searches.'
        
    var_list.update(parseList(var_list['Found Path'],var_list['Object'],var_list['Pre_or_Post'], var_list['ObjectId'], var_list['CmpAccountID']))

    if var_list['Object']=='Campaign':
        var_list.update(sourceChannel(var_list['Campaign Upload'],var_list['Record Name'],var_list['ObjectId'],var_list['Object']))
        var_list.update(sourceChannel(var_list['toCreate'],var_list['Record Name'],var_list['CmpAccountID'],var_list['Object']))
        var_list.update(extract_pdValues(var_list['Campaign Upload']))##,var_list['Object']))
        if var_list['Move To Bulk']==True:
            copy_toBulkProcessing(var_list['toCreate'])

        else:
            print '\nContacts will not be created. Not enough information provided.'
    elif var_list['Object']=='Account':
        var_list.update(sourceChannel(var_list['Update Path'],var_list['Record Name'],var_list['ObjectId'],var_list['Object']))
        if var_list['Move To Bulk']==True:
            copy_toBulkProcessing(var_list['Update Path'])
        else:
            print '\nContacts will not be created. Not enough information provided.'

    elif var_list['Object']=='BizDev Group':
        var_list.update(sourceChannel(var_list['Update Path'],var_list['Record Name'],var_list['ObjectId'],var_list['Object'], var_list['CmpAccountID']))
        var_list.update(sourceChannel(var_list['toCreate'],var_list['Record Name'],var_list['ObjectId'],var_list['Object'], var_list['CmpAccountID']))
        var_list.update(sourceChannel(var_list['BDG Update'],var_list['Record Name'],var_list['ObjectId'],var_list['Object'], var_list['CmpAccountID']))
        if var_list['Move To Bulk']==True:
            print 'Would move to bulk processing..'
##            copy_toBulkProcessing(var_list['toCreate'])
##            copy_toBulkProcessing(var_list['Update Path'])
        else:
            print '\nContacts will not be created. Not enough information provided.'
    
    var_list.update(valuesForEmail(var_list))

    var_list.update(recordStats(var_list['Stats Data']))


