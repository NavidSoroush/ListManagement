from check_Email import checkForLists
from trainHeadersModelv1 import training
from SearchSFDC import searchone, searchtwo, searchsec
from FINRA_search import fin_search
from parse_Files import parseList
from upload_Prep import sourceChannel
from cmpUpload import extract_pdValues, last_list_uploaded
from bulkProcessing import copy_toBulkProcessing
from dictExtraction import valuesForEmail
from recordStats import recordStats
from finra_licenses import licenseSearch
from functions import lists_in_queue, close_mailbox_connection, process_list_email

strings_to_print = ['\nSkipping step 6, because all contacts were found.',
                    '\nSkipping email, LkupName, FINRA, and SEC searches.',
                    '\nContacts will not be created. Not enough information provided.']

dict_keys_to_keep = ['Num_Processed', 'Lists_In_Queue', 'Lists_Data', 'Mailbox']

if __name__ == "__main__":
    var_list = []

    var_list = checkForLists()
    if lists_in_queue(var_list):
        while var_list['Num_Processed'] < (var_list['Lists_In_Queue']):
            num = var_list['Num_Processed']
            var_list.update(process_list_email(var_list['Lists_Data'][num],
                                               var_list['Mailbox']))

            if var_list['Object'] != 'Account':

                var_list.update(training(var_list['File Path'],
                                         var_list['CmpAccountName']))

            else:
                var_list.update(training(var_list['File Path'],
                                         var_list['Record Name']))

            var_list.update(searchone(var_list['File Path'],
                                      var_list['Object']))

            if var_list['SFDC_Found'] < var_list['Total Records'] and \
                    var_list['FINRA?']:

                var_list.update(fin_search(var_list['File Path'],
                                           var_list['Found Path']))
                if var_list['SFDC_Found'] + \
                        var_list['FINRA_Found'] < var_list['Total Records']:
                    var_list.update(searchsec(var_list['No CRD'], var_list['FINRA_SEC Found']))

                else:
                    print strings_to_print[0]

                var_list.update(searchtwo(var_list['FINRA_SEC Found'],
                                          var_list['Found Path'],
                                          var_list['Object']))
            else:
                print strings_to_print[1]

            if var_list['Object'] == 'BizDev Group':
                var_list.update(licenseSearch(var_list['Found Path']))

            var_list.update(parseList(var_list['Found Path'],
                                      var_list['Object'],
                                      var_list['Pre_or_Post'],
                                      var_list['ObjectId'],
                                      var_list['CmpAccountID']))

            if var_list['Object'] == 'Campaign':
                var_list.update(sourceChannel(var_list['Campaign Upload'],
                                              var_list['Record Name'],
                                              var_list['ObjectId'],
                                              var_list['Object']))

                var_list.update(sourceChannel(var_list['toCreate'],
                                              var_list['Record Name'],
                                              var_list['CmpAccountID'],
                                              var_list['Object']))

                var_list.update(extract_pdValues(var_list['Campaign Upload'],
                                                 var_list['Object']))

                if var_list['Move To Bulk']:
                    copy_toBulkProcessing(var_list['toCreate'])

                else:
                    print strings_to_print[2]

            elif var_list['Object'] == 'Account':
                last_list_uploaded(var_list['ObjectId'], var_list['Object'])
                var_list.update(sourceChannel(var_list['Update Path'],
                                              var_list['Record Name'],
                                              var_list['ObjectId'],
                                              var_list['Object']))
                if var_list['Move To Bulk']:
                    # copy_toBulkProcessing(var_list['Update Path'])
                    print 'Would move to bulk processing.'
                else:
                    print strings_to_print[2]

            elif var_list['Object'] == 'BizDev Group':
                var_list.update(sourceChannel(var_list['Update Path'],
                                              var_list['Record Name'],
                                              var_list['ObjectId'],
                                              var_list['Object'],
                                              var_list['CmpAccountID']))

                var_list.update(sourceChannel(var_list['toCreate'],
                                              var_list['Record Name'],
                                              var_list['ObjectId'],
                                              var_list['Object'],
                                              var_list['CmpAccountID']))

                var_list.update(sourceChannel(var_list['BDG Update'],
                                              var_list['Record Name'],
                                              var_list['ObjectId'],
                                              var_list['Object'],
                                              var_list['CmpAccountID']))

                var_list.update(extract_pdValues(var_list['BDG Update'],
                                                 var_list['Object']))

                if var_list['Move To Bulk'] == True:
                    copy_toBulkProcessing(var_list['toCreate'])
                    copy_toBulkProcessing(var_list['Update Path'])
                else:
                    print strings_to_print[2]

            var_list.update(valuesForEmail(var_list))

            var_list.update(recordStats(var_list['Stats Data']))

            num += 1
            var_list.update({'Num_Processed': num})
            print 'List #%s processed.' % var_list['Num_Processed']
            for k, v in var_list.iteritems():
                if k not in dict_keys_to_keep:
                    var_list[k] = None
        var_list.update(close_mailbox_connection(var_list['Mailbox']))
