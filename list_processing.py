from search.search import Search
from finra.finra import FinraScraping
from stats.record_stats import record_processing_stats
from utility.gen_helper import drop_in_bulk_processing
from ml.header_predictions import predict_headers_and_pre_processing
from utility.processes import parse_list_based_on_type, source_channel, extract_dictionary_values, sfdc_upload
from utility.email_helper import lists_in_queue
from utility.email_reader import MailBoxReader
from utility.log_helper import ListManagementLogger
from email_handler.email_wrapper import Email

_steps = [
    '\nSkipping step 6, because all contacts were found.',
    '\nSkipping email, LkupName, FINRA, and SEC searches.',
    '\nContacts will not be created. Not enough information provided.']
_dict_keys_to_keep = ['Num_Processed', 'Lists_In_Queue', 'Lists_Data', 'Mailbox', 'SFDC Session']


class ListProcessing:
    def __init__(self):
        """
        declare and set global objects that are leveraged through the
        actually processing of lists.
        """
        self.log = ListManagementLogger()
        self.s = Search(log=self.log)
        self.fin = FinraScraping(log=self.log)
        self.mb = MailBoxReader(log=self.log)
        self.vars = self.mb.pending_lists
        self.main_contact_based_processing()

    def main_contact_based_processing(self):
        """
        this method manages all potential contact based nodes of FS processing. each node has it's own method 
        to help clearly define the processing path.
        
        1) determine if there are lists pending in the queue (in the lists at fsinvestments mailbox)
        2) if lists are pending, loop through each list - grabbing necessary metadata
        3) if the file is a 'good' extension, process the list based on the list source object
        4) record stats for each list
        5) when all lists are processed, close all mailbox and SalesForce connections
        
        :return: 
        """
        if lists_in_queue(var_list=self.vars):
            while self.vars['Num_Processed'] < self.vars['Lists_In_Queue']:
                np = self.vars['Num_Processed']
                n = np + 1

                self.vars.update(self.mb.iterative_processing(self.mb.pending_lists['Lists_Data'][np]))
                if not self.is_bad_extension():
                    if self.vars['Object'] == 'Campaign':
                        self.campaign_processing(self.vars)

                    elif self.vars['Object'] == 'Account':
                        self.account_processing(self.vars)

                    elif self.vars['Object'] == 'BizDev Group':
                        self.bizdev_processing(self.vars)

                    self.vars.update(record_processing_stats(self.vars['Stats Data']))

                np += 1
                self.vars.update({'Num_Processed': n})
                print('List #%s processed.' % self.vars['Num_Processed'])
                for k, v in self.vars.iteritems():
                    if k not in _dict_keys_to_keep:
                        self.vars[k] = None

            self.vars['SFDC Session'].close_session()
            self.mb.close_mailbox()

    def is_bad_extension(self):
        """
        used to determine if the file type (based on the file extension) can be processed by the program.
        
        1) check if the file extension is 'bad'
        2) if it is bad, notify the team member that the list cannot be processed, and update list object record
        
        :return: boolean
        """
        if self.vars['ExtensionType'] in ['.pdf', '.gif', '.png', '.jpg', '.doc', '.docx']:
            if self.vars['CmpAccountName'] is None:
                obj_name = self.vars['Record Name']
            else:
                obj_name = self.vars['CmpAccountName']
            sub = 'LMA: Unable to Process List Attached to %s' % obj_name
            msg = 'The list attached to %s has a file extension, %s,  that cannot currently be processed by the ' \
                  'List Management App.' % (obj_name, self.vars['ExtensionType'])
            print(msg)
            Email(subject=sub, to=[self.vars['Sender Email']], body=msg, attachment_path=None)
            self.vars['SFDC Session'].update_records(obj='List__c', fields=['Status__c'],
                                                     upload_data=[[self.vars['ListObjId'], 'Unable to Process']])
            return True
        else:
            return False

    def campaign_processing(self, var_list):
        """
        handles list processing for the campaign object. processing steps below.
        
        1) predicts headers and pre_processes each file.
        2) searches against SalesForce for matches on: a) CRDNumber b) AMPFId c) Email d) LookupName
        3) if all advisors are not found, scrape data from FINRA based on First, Last, and Account Name
        4) if advisors are scraped, research those advisors against SalesForce
        5) parse list into actionable pieces: a) upload to campaign b) create c) not found d) etc.
        6) prepare data for upload into SalesForce (via source_channel function), do so for each file created above.
        7) extract stats from search processing, send notification email, and update SalesForce list record
        8) if applicable, drop file in the bulk_processing network drive to create or update SaleForce contacts
        
        :param var_list: list processing metadata 
        :return: n/a
        """
        var_list.update(predict_headers_and_pre_processing(var_list['File Path'],
                                                           var_list['CmpAccountName'], self.log))
        var_list.update(self.s.perform_search_one(var_list['File Path'], var_list['Object']))
        self.finra_search_and_search_two(var_list)
        var_list.update(self.fin.license_check(var_list['Found Path']))
        var_list.update(parse_list_based_on_type(path=var_list['Found Path'], l_type=var_list['Object'],
                                                 pre_or_post=var_list['Pre_or_Post'], log=self.log))
        var_list.update(source_channel(var_list['cmp_upload_path'], var_list['Record Name'],
                                       var_list['ObjectId'], var_list['Object'], log=self.log))
        var_list.update(source_channel(var_list['to_create_path'], var_list['Record Name'],
                                       var_list['CmpAccountID'], var_list['Object'], log=self.log))
        var_list.update(sfdc_upload(path=var_list['cmp_upload_path'], obj=var_list['Object'],
                                    obj_id=var_list['ObjectId'], session=var_list['SFDC Session'], log=self.log))
        var_list.update(extract_dictionary_values(dict_data=var_list, log=self.log))
        if var_list['Move To Bulk']:
            drop_in_bulk_processing(var_list['to_create_path'])
        else:
            print(_steps[2])

    def account_processing(self, var_list):
        """
        handles list processing for the account object. processing steps below.
        
        1) predicts headers and pre_processes each file.
        2) searches against SalesForce for matches on: a) CRDNumber b) AMPFId c) Email d) LookupName
        3) if all advisors are not found, scrape data from FINRA based on First, Last, and Account Name
        4) if advisors are scraped, research those advisors against SalesForce
        5) for all found advisors, scrape their licenses (and other metadata) from FINRA
        6) parse list into actionable pieces: a) upload to campaign b) create c) not found d) etc.
        7) update the 'Last List Upload' field on the account record.
        8) prepare data for upload into SalesForce (via source_channel function), do so for each file created above.
        9) extract stats from search processing, send notification email, and update SalesForce list record
        10) if applicable, drop files in the bulk_processing network drive to create or update SaleForce contacts
        
        :param var_list: list processing metadata 
        :return: n/a
        """
        var_list.update(predict_headers_and_pre_processing(var_list['File Path'], var_list['Record Name'],
                                                           log=self.log))
        var_list.update(self.s.perform_search_one(var_list['File Path'], var_list['Object']))
        self.finra_search_and_search_two(var_list)
        var_list.update(self.fin.license_check(var_list['Found Path']))
        var_list.update(parse_list_based_on_type(path=var_list['Found Path'], l_type=var_list['Object'],
                                                 pre_or_post=var_list['Pre_or_Post'], log=self.log))
        var_list['SFDC Session'].last_list_uploaded(obj_id=var_list['ObjectId'], obj=var_list['Object'])
        var_list.update(source_channel(var_list['update_path'], var_list['Record Name'],
                                       var_list['ObjectId'], var_list['Object'],log=self.log))
        var_list.update(extract_dictionary_values(dict_data=var_list, log=self.log))

        if var_list['Move To Bulk']:
            drop_in_bulk_processing(var_list['update_path'])
            drop_in_bulk_processing(var_list['to_create_path'])

        else:
            print(_steps[2])

    def bizdev_processing(self, var_list):
        """
        handles list processing for the bizdev object. processing steps below.

        1) predicts headers and pre_processes each file.
        2) searches against SalesForce for matches on: a) CRDNumber b) AMPFId c) Email d) LookupName
        3) if all advisors are not found, scrape data from FINRA based on First, Last, and Account Name
        4) if advisors are scraped, research those advisors against SalesForce
        5) for all found advisors, scrape their licenses (and other metadata) from FINRA
        6) parse list into actionable pieces: a) upload to campaign b) create c) not found d) etc.
        7) update the 'Last List Upload' field on the bizdev record and associate new contacts to the record.
        8) prepare data for upload into SalesForce (via source_channel function), do so for each file created above.
        9) extract stats from search processing, send notification email, and update SalesForce list record
        10) if applicable, drop files in the bulk_processing network drive to create or update SaleForce contacts

        :param var_list: list processing metadata 
        :return: n/a
        """
        var_list.update(predict_headers_and_pre_processing(var_list['File Path'],
                                                           var_list['CmpAccountName'], log=self.log))
        var_list.update(self.s.perform_search_one(var_list['File Path'], var_list['Object']))
        self.finra_search_and_search_two(var_list)
        var_list.update(self.fin.license_check(var_list['Found Path']))
        var_list.update(parse_list_based_on_type(path=var_list['Found Path'], l_type=var_list['Object'],
                                                 pre_or_post=var_list['Pre_or_Post'], log=self.log))
        var_list.update(sfdc_upload(path=var_list['bdg_update_path'], obj=var_list['Object'],
                                    obj_id=var_list['ObjectId'], session=var_list['SFDC Session'],log=self.log))
        var_list.update(source_channel(var_list['update_path'], var_list['Record Name'],
                                       var_list['ObjectId'], var_list['Object'],
                                       var_list['CmpAccountID'], log=self.log))
        var_list.update(source_channel(var_list['to_create_path'], var_list['Record Name'],
                                       var_list['ObjectId'], var_list['Object'],
                                       var_list['CmpAccountID'], log=self.log))
        var_list.update(source_channel(var_list['bdg_update_path'], var_list['Record Name'],
                                       var_list['ObjectId'], var_list['Object'],
                                       var_list['CmpAccountID'], log=self.log))
        var_list.update(extract_dictionary_values(dict_data=var_list, log=self.log))

        if var_list['Move To Bulk']:
            drop_in_bulk_processing(var_list['to_create_path'])
            drop_in_bulk_processing(var_list['update_path'])
        else:
            print _steps[2]

    def finra_search_and_search_two(self, var_list):
        """
        this method handles helps to decide if FINRA scraping or searching SalesForce a 2nd time
        is necessary.
        
        1) if all advisors are not found and are missing CRDNumbers, scrape FINRA
        2) if FINRA is scraped, search our SalesForce database to increase our likely match-rate.
        
        :param var_list: list processing metadata
        :return: n/a
        """
        if var_list['SFDC_Found'] < var_list['Total Records'] and var_list['FINRA?']:

            var_list.update(self.fin.crd_check(path=var_list['File Path']))
            if (var_list['SFDC_Found'] + var_list['FINRA_Found']) < var_list['Total Records']:
                var_list.update(self.s.perform_sec_search(var_list['No CRD'], var_list['FINRA_SEC Found']))

            else:
                print(_steps[0])

            var_list.update(self.s.perform_search_two(var_list['FINRA_SEC Found'], var_list['Found Path'],
                                                      var_list['Object']))
        else:
            print(_steps[1])


if __name__ == '__main__':
    lp = ListProcessing()
