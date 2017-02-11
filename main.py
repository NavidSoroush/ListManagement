from search.Search import Search
from finra.Finra import FinraScraping
from ml.header_predictions import HeaderPredictions
from stats.record_stats import record_processing_stats
from utility.gen_helpers import drop_in_bulk_processing
from utility.processes import parse_list_based_on_type, source_channel, extract_dictionary_values
from utility.email_helpers import check_for_new_lists, lists_in_queue, process_list_email, close_mailbox_connection

_steps = [
    '\nSkipping step 6, because all contacts were found.',
    '\nSkipping email, LkupName, FINRA, and SEC searches.',
    '\nContacts will not be created. Not enough information provided.']
_dict_keys_to_keep = ['Num_Processed', 'Lists_In_Queue', 'Lists_Data', 'Mailbox']
s = Search()
fin = FinraScraping()


var_list = check_for_new_lists()

if lists_in_queue(var_list=var_list):
    while var_list['Num_Processed'] < var_list['Lists_In_Queue']:
        num_processed = var_list['Num_Processed']

        if lists_in_queue(var_list):
            while var_list['Num_Processed'] < (var_list['Lists_In_Queue']):

                num = var_list['Num_Processed']
                var_list.update(process_list_email(var_list['Lists_Data'][num], var_list['Mailbox']))

                if var_list['Object'] != 'Account':

                    var_list.update(HeaderPredictions(var_list['File Path'], var_list['CmpAccountName']))

                else:
                    var_list.update(HeaderPredictions(var_list['File Path'], var_list['Record Name']))

                var_list.update(s.perform_search_one(var_list['File Path'], var_list['Object']))

                if var_list['SFDC_Found'] < var_list['Total Records'] and \
                        var_list['FINRA?']:

                    var_list.update(fin.crd_check(var_list['File Path'], var_list['Found Path']))
                    if (var_list['SFDC_Found'] + var_list['FINRA_Found']) < var_list['Total Records']:
                        var_list.update(s.perform_sec_search(var_list['No CRD'], var_list['FINRA_SEC Found']))

                    else:
                        print _steps[0]

                    var_list.update(s.perform_search_two(var_list['FINRA_SEC Found'], var_list['Found Path'],
                                                                var_list['Object']))
                else:
                    print _steps[1]

                if var_list['Object'] == 'BizDev Group':

                    var_list.update(fin.license_check(var_list['Found Path']))

                var_list.update(parse_list_based_on_type(var_list['Found Path'], var_list['Object'],
                                                         var_list['Pre_or_Post'],var_list['ObjectId'],
                                                         var_list['CmpAccountID']))

                if var_list['Object'] == 'Campaign':
                    var_list.update(source_channel(var_list['Campaign Upload'], var_list['Record Name'],
                                                   var_list['ObjectId'], var_list['Object']))

                    var_list.update(source_channel(var_list['toCreate'], var_list['Record Name'],
                                                   var_list['CmpAccountID'], var_list['Object']))

                    var_list.update(extract_dictionary_values(var_list['Campaign Upload'], var_list['Object']))

                    if var_list['Move To Bulk']:
                        drop_in_bulk_processing(var_list['toCreate'])

                    else:
                        print _steps[2]

                elif var_list['Object'] == 'Account':
                    var_list['SFDC Session'].last_list_uploaded(var_list['ObjectId'], var_list['Object'])
                    var_list.update(source_channel(var_list['Update Path'],
                                                  var_list['Record Name'],
                                                  var_list['ObjectId'],
                                                  var_list['Object']))
                    if var_list['Move To Bulk']:
                        drop_in_bulk_processing(var_list['Update Path'])

                    else:
                        print _steps[2]

                elif var_list['Object'] == 'BizDev Group':
                    var_list['SFDC Session'].last_list_uploaded(var_list['ObjectId'], var_list['Object'])
                    var_list.update(source_channel(var_list['Update Path'], var_list['Record Name'],
                                                   var_list['ObjectId'], var_list['Object'],
                                                   var_list['CmpAccountID']))

                    var_list.update(source_channel(var_list['toCreate'], var_list['Record Name'],
                                                   var_list['ObjectId'], var_list['Object'],
                                                   var_list['CmpAccountID']))

                    var_list.update(source_channel(var_list['BDG Update'], var_list['Record Name'],
                                                   var_list['ObjectId'], var_list['Object'],
                                                   var_list['CmpAccountID']))

                    var_list.update(extract_dictionary_values(var_list['BDG Update'], var_list['Object']))

                    if var_list['Move To Bulk']:
                        drop_in_bulk_processing(var_list['toCreate'])
                        drop_in_bulk_processing(var_list['Update Path'])
                    else:
                        print _steps[2]

                var_list.update(extract_dictionary_values(var_list))

                var_list.update(record_processing_stats(var_list['Stats Data']))

                num_processed += 1
                var_list.update({'Num_Processed': num})
                print 'List #%s processed.' % var_list['Num_Processed']
                for k, v in var_list.iteritems():
                    if k not in _dict_keys_to_keep:
                        var_list[k] = None
            var_list['SFDC Session'].close_session()
            var_list.update(close_mailbox_connection(var_list['Mailbox']))