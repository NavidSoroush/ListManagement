import traceback
from utility.email_wrapper import Email
from finra.Finra import FinraScraping
from finra.finra_scraping import Finra
from ml.header_predictions import predict_headers_and_pre_processing
from search.Search import Search
from stats.record_stats import record_processing_stats
from utility.email_helper import lists_in_queue
from utility.email_reader import MailBoxReader
from utility.gen_helper import drop_in_bulk_processing
from utility.log_helper import ListManagementLogger
from utility.processes import parse_list_based_on_type, source_channel, extract_dictionary_values, sfdc_upload

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
        self.log = ListManagementLogger().logger
        self.s = Search(log=self.log)
        self.fin = FinraScraping(log=self.log)
        self.finra = Finra()
        self.mb = MailBoxReader(log=self.log)
        self.vars = self.mb.extract_pending_lists(self.mb.mailbox, self.mb.email_folder)
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

                self.vars.update(self.mb.iterative_processing(self.vars['Lists_Data'][np]))
                if not self.is_bad_extension():
                    try:
                        if self.vars['Object'] == 'Campaign':
                            self.campaign_processing()

                        elif self.vars['Object'] == 'Account':
                            self.account_processing()

                        elif self.vars['Object'] == 'BizDev Group':
                            self.bizdev_processing()

                        self.vars.update(record_processing_stats(self.vars['Stats Data']))

                    except:
                        self.create_log_record_of_current_list_data(msg=str(traceback.format_exc()))

                    finally:
                        np += 1
                        self.vars.update({'Num_Processed': n})
                        self.log.info('List #%s processed.' % self.vars['Num_Processed'])
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
            self.log.warning(msg)
            Email(subject=sub, to=[self.vars['Sender Email']], body=msg, attachment_path=None)
            self.vars['SFDC Session'].update_records(obj='List__c', fields=['Status__c'],
                                                     upload_data=[[self.vars['ListObjId'], 'Unable to Process']])
            return True
        else:
            return False

    def campaign_processing(self):
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
        
        :return: n/a
        """
        self.vars.update(predict_headers_and_pre_processing(self.vars['File Path'],
                                                            self.vars['CmpAccountName'], self.log))
        self.vars.update(self.s.perform_search_one(self.vars['File Path'], self.vars['Object']))
        self.finra_search_and_search_two()
        self.vars.update(parse_list_based_on_type(path=self.vars['Found Path'], l_type=self.vars['Object'],
                                                  pre_or_post=self.vars['Pre_or_Post'], log=self.log))
        self.vars.update(source_channel(self.vars['cmp_upload_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'], log=self.log))
        self.vars.update(source_channel(self.vars['to_create_path'], self.vars['Record Name'],
                                        self.vars['CmpAccountID'], self.vars['Object'], log=self.log))
        self.vars.update(sfdc_upload(path=self.vars['cmp_upload_path'], obj=self.vars['Object'],
                                     obj_id=self.vars['ObjectId'], session=self.vars['SFDC Session'],
                                     log=self.log))
        self.vars.update(extract_dictionary_values(dict_data=self.vars, log=self.log))
        if self.vars['Move To Bulk']:
            drop_in_bulk_processing(self.vars['to_create_path'])
        else:
            print(_steps[2])

    def account_processing(self):
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
        
        :return: n/a
        """
        self.vars.update(
            predict_headers_and_pre_processing(self.vars['File Path'], self.vars['Record Name'],
                                               log=self.log))
        self.vars.update(self.s.perform_search_one(self.vars['File Path'], self.vars['Object']))
        self.finra_search_and_search_two()
        self.vars.update(self.finra.scrape(self.vars['Found Path'], scrape_type='all'))
        self.vars.update(parse_list_based_on_type(path=self.vars['Found Path'], l_type=self.vars['Object'],
                                                  pre_or_post=self.vars['Pre_or_Post'], log=self.log))
        self.vars['SFDC Session'].last_list_uploaded(obj_id=self.vars['ObjectId'], obj=self.vars['Object'])
        self.vars.update(source_channel(self.vars['update_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'], log=self.log))
        # self.vars.update(source_channel(self.vars['to_create_path'], self.vars['Record Name'],
        # self.vars['ObjectId'], self.vars['Object'],
        # self.vars['ObjectId'], log=self.log))
        self.vars.update(extract_dictionary_values(dict_data=self.vars, log=self.log))

        if self.vars['Move To Bulk']:
            drop_in_bulk_processing(self.vars['update_path'])
            drop_in_bulk_processing(self.vars['to_create_path'])

        else:
            print(_steps[2])

    def bizdev_processing(self):
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
 
        :return: n/a
        """
        self.vars.update(predict_headers_and_pre_processing(self.vars['File Path'],
                                                            self.vars['CmpAccountName'], log=self.log))
        self.vars.update(self.s.perform_search_one(self.vars['File Path'], self.vars['Object']))
        self.finra_search_and_search_two()
        self.vars.update(self.finra.scrape(self.vars['Found Path'], scrape_type='all'))
        self.vars.update(parse_list_based_on_type(path=self.vars['Found Path'], l_type=self.vars['Object'],
                                                  pre_or_post=self.vars['Pre_or_Post'], log=self.log))
        self.vars.update(sfdc_upload(path=self.vars['bdg_update_path'], obj=self.vars['Object'],
                                     obj_id=self.vars['ObjectId'], session=self.vars['SFDC Session'],
                                     log=self.log))
        self.vars.update(source_channel(self.vars['update_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'],
                                        self.vars['CmpAccountID'], log=self.log))
        self.vars.update(source_channel(self.vars['to_create_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'],
                                        self.vars['CmpAccountID'], log=self.log))
        self.vars.update(source_channel(self.vars['bdg_update_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'],
                                        self.vars['CmpAccountID'], log=self.log))
        self.vars.update(extract_dictionary_values(dict_data=self.vars, log=self.log))

        if self.vars['Move To Bulk']:
            drop_in_bulk_processing(self.vars['to_create_path'])
            drop_in_bulk_processing(self.vars['update_path'])
        else:
            print _steps[2]

    def finra_search_and_search_two(self):
        """
        this method handles helps to decide if FINRA scraping or searching SalesForce a 2nd time
        is necessary.
        
        1) if all advisors are not found and are missing CRDNumbers, scrape FINRA
        2) if FINRA is scraped, search our SalesForce database to increase our likely match-rate.
        
        :return: n/a
        """
        if self.vars['SFDC_Found'] < self.vars['Total Records'] and self.vars['FINRA?']:

            self.vars.update(self.finra.scrape(path=self.vars['File Path'], scrape_type='crd', parse_list=True))
            if (self.vars['SFDC_Found'] + self.vars['FINRA_Found']) < self.vars['Total Records']:
                self.vars.update(
                    self.s.perform_sec_search(self.vars['No CRD'], self.vars['FINRA_SEC Found']))

            else:
                print(_steps[0])

            self.vars.update(self.s.perform_search_two(self.vars['FINRA_SEC Found'],
                                                       self.vars['Found Path'],
                                                       self.vars['Object']))
        else:
            print(_steps[1])

    def create_log_record_of_current_list_data(self, msg):
        self.log.warning('A fatal error has occured. Printing out necessary data to restart the program and'
                         'complete it manually.')
        self.log.info(self.vars)
        self.log.error(msg)
        raise RuntimeError(msg)


if __name__ == '__main__':
    lp = ListProcessing()
