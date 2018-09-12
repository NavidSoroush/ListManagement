import traceback

from PythonUtilities.LoggingUtility import Logging
from PythonUtilities.EmailHandling import EmailHandler as Email
from PythonUtilities.salesforcipy import SFPy

from ListManagement.config import Config as con
from ListManagement.search import Search, Finra
from ListManagement.search.ml import header_predictions as predicts
from ListManagement.utility import queue
from ListManagement.utility import general as _ghelp
from ListManagement.utility.processes import parse_list_based_on_type, source_channel, extract_dictionary_values, \
    sfdc_upload

_steps = [
    '\nSkipping step 6, because all contacts were found.',
    '\nSkipping email, LkupName, FINRA, and SEC searches.',
    '\nContacts will not be created. Not enough information provided.']


# ensure_requirements_met()


class ListProcessing:
    def __init__(self):
        """
        declare and set global objects that are leveraged through the
        actually processing of lists.
        """
        self._log = Logging(name=con.AppName, abbr=con.NameAbbr, dir_=con.LogDrive, level='debug').logger
        self._search_api = Search(log=self._log)
        self._finra_api = Finra(log=self._log)
        tmp_sfdc = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken, domain=con.SFDomain, verbose=False,
                        _dir=con.BaseDir)
        self.vars = queue.build_queue(tmp_sfdc, self._log)
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
        for _vars in self.vars:
            if not self.is_bad_extension(_vars):
                try:
                    if _vars['Object'] == 'Campaign':
                        _vars = self.campaign_processing(_vars)

                    elif _vars['Object'] == 'Account':
                        _vars = self.account_processing(_vars)

                    elif _vars['Object'] == 'BizDev Group':
                        _vars = self.bizdev_processing(_vars)

                    _ghelp.record_processing_stats(_vars['Stats Data'])

                except:
                    self.create_log_record_of_current_list_data(msg=str(traceback.format_exc()))

                finally:
                    self._log.info('List #%s processed.' % _vars['ListIndex'])

    def is_bad_extension(self, _vars):
        """
        used to determine if the file type (based on the file extension) can be processed by the program.
        
        1) check if the file extension is 'bad'
        2) if it is bad, notify the team member that the list cannot be processed, and update list object record
        
        :return: boolean
        """
        if _vars['ExtensionType'] in ['.pdf', '.gif', '.png', '.jpg', '.doc', '.docx']:
            if _vars['CmpAccountName'] is None:
                obj_name = _vars['Record Name']
            else:
                obj_name = _vars['CmpAccountName']
            sub = 'LMA: Unable to Process List Attached to %s' % obj_name
            msg = 'The list attached to %s has a file extension, %s,  that cannot currently be processed by the ' \
                  'List Management App.' % (obj_name, _vars['ExtensionType'])
            self._log.warning(msg)
            Email(con.SMTPUser, con.SMTPPass, self._log).send_new_email(
                subject=sub, to=[_vars['Sender Email']], body=msg, attachments=None
                , name=con.FullName
            )
            _vars['SFDC Session'].update_records(obj='List__c', fields=['Status__c'],
                                                 upload_data=[[_vars['ListObjId'], 'Unable to Process']])
            return True
        else:
            return False

    def campaign_processing(self, _vars):
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
        _vars.update(predicts.predict_headers_and_pre_processing(_vars['File Path'],
                                                        _vars['CmpAccountName'], self._log))
        _vars.update(self._search_api.perform_search_one(_vars['File Path'], _vars['Object']))
        try:
            self.finra_search_and_search_two(_vars)
        except:
            self._log.info('An error occurred during FINRA or SearchTwo processing. Skipping.')
            pass

        _vars.update(parse_list_based_on_type(path=_vars['Found Path'], l_type=_vars['Object'],
                                              pre_or_post=_vars['Pre_or_Post'], log=self._log,
                                              to_create_path=_vars['to_create_path']))
        _vars.update(source_channel(_vars['cmp_upload_path'], _vars['Record Name'],
                                    _vars['ObjectId'], _vars['Object'], log=self._log))
        _vars.update(source_channel(_vars['to_create_path'], _vars['Record Name'],
                                    _vars['CmpAccountID'], _vars['Object'], log=self._log))
        _vars.update(sfdc_upload(path=_vars['cmp_upload_path'], obj=_vars['Object'],
                                 obj_id=_vars['ObjectId'], session=_vars['SFDC Session'],
                                 log=self._log))
        _vars.update(extract_dictionary_values(dict_data=_vars, log=self._log))
        if _vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(_vars['to_create_path'], self._log)
        else:
            self._log.info(_steps[2])
        return _vars

    def account_processing(self, _vars):
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
        _vars.update(
            predicts.predict_headers_and_pre_processing(_vars['File Path'], _vars['Record Name'],
                                               log=self._log))
        _vars.update(self._search_api.perform_search_one(_vars['File Path'], _vars['Object']))
        try:
            self.finra_search_and_search_two(_vars)
        except:
            self._log.info('An error occurred during FINRA or SearchTwo processing, Skipping.')
            pass
        _vars.update(self._finra_api.scrape(_vars['Found Path'], scrape_type='all'))
        _vars.update(parse_list_based_on_type(path=_vars['Found Path'], l_type=_vars['Object'],
                                              pre_or_post=_vars['Pre_or_Post'], log=self._log,
                                              to_create_path=_vars['to_create_path']))
        try:
            llu_data = _ghelp.last_list_uploaded_data(_vars['ObjectId'])
            _vars['SFDC Session'].update_records(obj=_vars['Object'], fields=['Id', 'Last_Rep_List_Upload__c'],
                                                 upload_data=[llu_data])
        except:
            self._log.warn('A non-fatal error occurred during the Last List Upload'
                           'of the %s object for Id %s. The values were %s.' % (_vars['Object'],
                                                                                _vars['ObjectId'],
                                                                                llu_data))

        _vars.update(source_channel(_vars['update_path'], _vars['Record Name'],
                                    _vars['ObjectId'], _vars['Object'], log=self._log))

        _vars.update(extract_dictionary_values(dict_data=_vars, log=self._log))

        if _vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(_vars['update_path'], self._log)
            if _ghelp.is_path(_vars['to_create_path']):
                _vars.update(source_channel(_vars['to_create_path'], _vars['Record Name'],
                                            _vars['ObjectId'], _vars['Object'],
                                            _vars['ObjectId'], log=self._log))
                _ghelp.drop_in_bulk_processing(_vars['to_create_path'], self._log)

        else:
            self._log.info(_steps[2])
        return _vars

    def bizdev_processing(self, _vars):
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
        _vars.update(predicts.predict_headers_and_pre_processing(_vars['File Path'],
                                                        _vars['CmpAccountName'], log=self._log))
        _vars.update(self._search_api.perform_search_one(_vars['File Path'], _vars['Object']))
        try:
            self.finra_search_and_search_two(_vars)
        except:
            self._log.info('An error occured during FINRA or SearchTwo processing.')
            pass
        _vars.update(self._finra_api.scrape(_vars['Found Path'], scrape_type='all', save=True))
        _vars.update(parse_list_based_on_type(path=_vars['Found Path'], l_type=_vars['Object'],
                                              pre_or_post=_vars['Pre_or_Post'], log=self._log,
                                              to_create_path=_vars['to_create_path']))
        _vars.update(sfdc_upload(path=_vars['bdg_update_path'], obj=_vars['Object'],
                                 obj_id=_vars['ObjectId'], session=_vars['SFDC Session'],
                                 log=self._log))

        try:
            llu_data = _ghelp.last_list_uploaded_data(_vars['ObjectId'])
            _vars['SFDC Session'].update_records(obj=_vars['Object'], fields=['Id', 'Last_Upload_Date__c'],
                                                 upload_data=[llu_data])
        except:
            self._log.warn('A non-fatal error occurred during the Last List Upload'
                           'of the %s object for Id %s. The values were %s.' % (_vars['Object'],
                                                                                _vars['ObjectId'],
                                                                                llu_data))

        _vars.update(source_channel(_vars['update_path'], _vars['Record Name'],
                                    _vars['ObjectId'], _vars['Object'],
                                    _vars['CmpAccountID'], log=self._log))
        _vars.update(source_channel(_vars['to_create_path'], _vars['Record Name'],
                                    _vars['ObjectId'], _vars['Object'],
                                    _vars['CmpAccountID'], log=self._log))
        _vars.update(source_channel(_vars['bdg_update_path'], _vars['Record Name'],
                                    _vars['ObjectId'], _vars['Object'],
                                    _vars['CmpAccountID'], log=self._log))
        _vars.update(extract_dictionary_values(dict_data=_vars, log=self._log))

        if _vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(_vars['to_create_path'], self._log)
            _ghelp.drop_in_bulk_processing(_vars['update_path'], self._log)

        else:
            self._log.info(_steps[2])
        return _vars

    def finra_search_and_search_two(self, _vars):
        """
        this method handles helps to decide if FINRA scraping or searching SalesForce a 2nd time
        is necessary.
        
        1) if all advisors are not found and are missing CRDNumbers, scrape FINRA
        2) if FINRA is scraped, search our SalesForce database to increase our likely match-rate.
        
        :return: n/a
        """
        if _vars['SFDC_Found'] < _vars['Total Records'] \
                and _vars['FINRA?']:

            _vars.update(self._finra_api.scrape(path=_vars['File Path'],
                                                scrape_type='crd',
                                                parse_list=True))
            if (_vars['SFDC_Found'] + _vars['FINRA_Found']) < _vars['Total Records']:
                _vars.update(
                    self._search_api.perform_sec_search(_vars['No CRD'], _vars['FINRA_SEC Found']))

            else:
                self._log.info(_steps[0])

            _vars.update(self._search_api.perform_search_two(_vars['FINRA_SEC Found'],
                                                             _vars['Found Path'],
                                                             _vars['Object']))
        else:
            self._log.info(_steps[1])
        return _vars

    def create_log_record_of_current_list_data(self, msg):
        self._log.warning('A fatal error has occurred. Refer to message traceback for insight into '
                          'the issue.')
        self._log.error(msg)
        raise RuntimeError(msg)


if __name__ == '__main__':
    lp = ListProcessing()
