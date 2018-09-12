import traceback

from PythonUtilities.LoggingUtility import Logging
from PythonUtilities.EmailHandling import EmailHandler as Email

from ListManagement.config import Config as con
from ListManagement.search import Finra, Search
from ListManagement.utility import MailBoxReader
from ListManagement.utility import general as _ghelp
from ListManagement.utility.email_helper import lists_in_queue
from ListManagement.search.ml.header_predictions import predict_headers_and_pre_processing
from ListManagement.utility.processes import parse_list_based_on_type, source_channel, extract_dictionary_values, \
    sfdc_upload

_steps = [
    '\nSkipping step 6, because all contacts were found.',
    '\nSkipping email, LkupName, FINRA, and SEC searches.',
    '\nContacts will not be created. Not enough information provided.']
_dict_keys_to_keep = ['Num_Processed', 'Lists_In_Queue', 'Lists_Data', 'Mailbox', 'SFDC Session']


# ensure_requirements_met()


class ListProcessing:
    def __init__(self, mode='manual'):
        """
        declare and set global objects that are leveraged through the
        actually processing of lists.
        """
        self.mode = mode
        self._log = Logging(name=con.AppName, abbr=con.NameAbbr, dir_=con.LogDrive, level='debug').logger
        self._search_api = Search(log=self._log)
        self._finra_api = Finra(log=self._log)
        self._mailbox = MailBoxReader(log=self._log)
        self.vars = self._mailbox.extract_pending_lists(self._mailbox.mailbox, self._mailbox.email_folder)
        self.main_contact_based_processing()

    def main_contact_based_processing(self):
        """
        this method manages all potential contact based nodes of FS 
        processing. each node has it's own method to help clearly 
        define the processing path.
        
        1. determine if there are lists pending in the queue
        (in the lists at fsinvestments mailbox)
        2. if lists are pending, loop through each list request
        and grab necessary metadata to process
        3. if the file is a 'good' extension, process the 
        request based upon the SFDC object where request originated.
        4. record stats for each list
        5. when all lists are processed, close all mailbox and SalesForce connections
        
        :return: 
        """

        if lists_in_queue(var_list=self.vars):
            while self.vars['Num_Processed'] < self.vars['Lists_In_Queue']:
                np = self.vars['Num_Processed']
                n = np + 1

                self.vars.update(self._mailbox.iterative_processing(self.vars['Lists_Data'][np]))
                if not self.is_bad_extension():
                    try:
                        if self.vars['Object'] == 'Campaign':
                            self.campaign_processing()

                        elif self.vars['Object'] == 'Account':
                            self.account_processing()

                        elif self.vars['Object'] == 'BizDev Group':
                            self.bizdev_processing()

                        self.vars.update(_ghelp.record_processing_stats(self.vars['Stats Data']))

                    except:
                        self.create_log_record_of_current_list_data(msg=str(traceback.format_exc()))

                    finally:
                        np += 1
                        self.vars.update({'Num_Processed': n})
                        self._log.info('List #%s processed.' % self.vars['Num_Processed'])
                        for k, v in self.vars.items():
                            if k not in _dict_keys_to_keep:
                                self.vars[k] = None

            self._mailbox.close_mailbox()

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
            self._log.warning(msg)
            Email(con.SMTPUser, con.SMTPPass, self._log).send_new_email(
                subject=sub, to=[self.vars['Sender Email']], body=msg, attachments=None
                , name=con.FullName
            )
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
                                                            self.vars['CmpAccountName'], self._log, self.mode))
        self.vars.update(self._search_api.perform_search_one(self.vars['File Path'], self.vars['Object']))
        try:
            self.finra_search_and_search_two()
        except:
            self._log.info('An error occurred during FINRA or SearchTwo processing. Skipping.')
            pass
        self.vars.update(parse_list_based_on_type(path=self.vars['Found Path'], l_type=self.vars['Object'],
                                                  pre_or_post=self.vars['Pre_or_Post'], log=self._log,
                                                  to_create_path=self.vars['to_create_path']))
        self.vars.update(source_channel(self.vars['cmp_upload_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'], log=self._log))
        self.vars.update(source_channel(self.vars['to_create_path'], self.vars['Record Name'],
                                        self.vars['CmpAccountID'], self.vars['Object'], log=self._log))
        self.vars.update(sfdc_upload(path=self.vars['cmp_upload_path'], obj=self.vars['Object'],
                                     obj_id=self.vars['ObjectId'], session=self.vars['SFDC Session'],
                                     log=self._log))
        self.vars.update(extract_dictionary_values(dict_data=self.vars, log=self._log))
        if self.vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(self.vars['to_create_path'], self._log)
        else:
            self._log.info(_steps[2])

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
                                               log=self._log, mode=self.mode))
        self.vars.update(self._search_api.perform_search_one(self.vars['File Path'], self.vars['Object']))
        try:
            self.finra_search_and_search_two()
        except:
            self._log.info('An error occurred during FINRA or SearchTwo processing, Skipping.')
            pass
        self.vars.update(self._finra_api.scrape(self.vars['Found Path'], scrape_type='all'))
        self.vars.update(parse_list_based_on_type(path=self.vars['Found Path'], l_type=self.vars['Object'],
                                                  pre_or_post=self.vars['Pre_or_Post'], log=self._log,
                                                  to_create_path=self.vars['to_create_path']))
        try:
            llu_data = _ghelp.last_list_uploaded_data(self.vars['ObjectId'])
            self.vars['SFDC Session'].update_records(obj=self.vars['Object'], fields=['Id', 'Last_Rep_List_Upload__c'],
                                                     upload_data=[llu_data])
        except:
            self._log.warn('A non-fatal error occurred during the Last List Upload'
                           'of the %s object for Id %s. The values were %s.' % (self.vars['Object'],
                                                                                self.vars['ObjectId'],
                                                                                llu_data))

        self.vars.update(source_channel(self.vars['update_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'], log=self._log))

        self.vars.update(extract_dictionary_values(dict_data=self.vars, log=self._log))

        if self.vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(self.vars['update_path'], self._log)
            if _ghelp.is_path(self.vars['to_create_path']):
                self.vars.update(source_channel(self.vars['to_create_path'], self.vars['Record Name'],
                                                self.vars['ObjectId'], self.vars['Object'],
                                                self.vars['ObjectId'], log=self._log))
                _ghelp.drop_in_bulk_processing(self.vars['to_create_path'], self._log)

        else:
            self._log.info(_steps[2])

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
                                                            self.vars['CmpAccountName'], log=self._log, mode=self.mode))
        self.vars.update(self._search_api.perform_search_one(self.vars['File Path'], self.vars['Object']))
        try:
            self.finra_search_and_search_two()
        except:
            self._log.info('An error occured during FINRA or SearchTwo processing.')
            pass
        self.vars.update(self._finra_api.scrape(self.vars['Found Path'], scrape_type='all', save=True))
        self.vars.update(parse_list_based_on_type(path=self.vars['Found Path'], l_type=self.vars['Object'],
                                                  pre_or_post=self.vars['Pre_or_Post'], log=self._log,
                                                  to_create_path=self.vars['to_create_path']))
        self.vars.update(sfdc_upload(path=self.vars['bdg_update_path'], obj=self.vars['Object'],
                                     obj_id=self.vars['ObjectId'], session=self.vars['SFDC Session'],
                                     log=self._log))

        try:
            llu_data = _ghelp.last_list_uploaded_data(self.vars['ObjectId'])
            self.vars['SFDC Session'].update_records(obj=self.vars['Object'], fields=['Id', 'Last_Upload_Date__c'],
                                                     upload_data=[llu_data])
        except:
            self._log.warn('A non-fatal error occurred during the Last List Upload'
                           'of the %s object for Id %s. The values were %s.' % (self.vars['Object'],
                                                                                self.vars['ObjectId'],
                                                                                llu_data))

        self.vars.update(source_channel(self.vars['update_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'],
                                        self.vars['CmpAccountID'], log=self._log))
        self.vars.update(source_channel(self.vars['to_create_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'],
                                        self.vars['CmpAccountID'], log=self._log))
        self.vars.update(source_channel(self.vars['bdg_update_path'], self.vars['Record Name'],
                                        self.vars['ObjectId'], self.vars['Object'],
                                        self.vars['CmpAccountID'], log=self._log))
        self.vars.update(extract_dictionary_values(dict_data=self.vars, log=self._log))

        if self.vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(self.vars['to_create_path'], self._log)
            _ghelp.drop_in_bulk_processing(self.vars['update_path'], self._log)
        else:
            self._log.info(_steps[2])

    def finra_search_and_search_two(self):
        """
        this method handles helps to decide if FINRA scraping or searching SalesForce a 2nd time
        is necessary.
        
        1) if all advisors are not found and are missing CRDNumbers, scrape FINRA
        2) if FINRA is scraped, search our SalesForce database to increase our likely match-rate.
        
        :return: n/a
        """
        if self.vars['SFDC_Found'] < self.vars['Total Records'] \
                and self.vars['FINRA?']:

            self.vars.update(self._finra_api.scrape(path=self.vars['File Path'],
                                                    scrape_type='crd',
                                                    parse_list=True))
            if (self.vars['SFDC_Found'] + self.vars['FINRA_Found']) < self.vars['Total Records']:
                self.vars.update(
                    self._search_api.perform_sec_search(self.vars['No CRD'], self.vars['FINRA_SEC Found']))

            else:
                self._log.info(_steps[0])

            self.vars.update(self._search_api.perform_search_two(self.vars['FINRA_SEC Found'],
                                                                 self.vars['Found Path'],
                                                                 self.vars['Object']))
        else:
            self._log.info(_steps[1])

    def create_log_record_of_current_list_data(self, msg):
        self._log.warning('A fatal error has occured. Printing out necessary data to restart the program and'
                          'complete it manually.')
        self._log.info(self.vars)
        self._log.error(msg)
        raise RuntimeError(msg)


if __name__ == '__main__':
    lp = ListProcessing()
