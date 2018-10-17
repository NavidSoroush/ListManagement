"""
list_processing.py
====================================
The core module that orchestrates matching
for 3rd party documents (excel, csv, et al) and
updates the Salesforce CRM for FS Investments.

Handles Broker Dealer (Account) and Business Development
Group (BizDev Group) updated representative
lists (typically received monthly and quarterly, respectively).

Handles attendee lists for events and conferences (Campaigns)
where FS Investments has committed money.
"""

import os
import sys

import traceback

from PythonUtilities.LoggingUtility import Logging
from PythonUtilities.EmailHandling import EmailHandler as Email
from PythonUtilities.salesforcipy import SFPy

sys.path.append(os.path.abspath('.'))

from ListManagement.config import Config as con
from ListManagement.search import Search, Finra
from ListManagement.search.ml import header_predictions as predicts
from ListManagement.utility import build_queue
from ListManagement.utility import general as _ghelp
from ListManagement.utility import processes as _process

_steps = [
    '\nSkipping step 6, because all contacts were found.',
    '\nSkipping email, LkupName, FINRA, and SEC searches.',
    '\nContacts will not be created. Not enough information provided.']


# ensure_requirements_met()


class ListProcessing:
    """Orchestrates all matching and updates for pending list requests."""

    def __init__(self, mode='manual'):
        """
        Instantiates the ListProcessing class and other objects used
        during the matching and update process.

        Can be run in two modes:
            1) 'manual' - will require user interaction. (Likely for debugging.)
            2) 'auto' - allows for entire process to be scheduled/cron'd.

        Parameters
        ----------
        mode
            A string to define how the program is being run.
            Accepts 'manual' (default) and 'auto'.
        """
        self.mode = mode
        self._log = Logging(name=con.AppName, abbr=con.NameAbbr, dir_=con.LogDrive, level='debug').logger
        self._search_api = Search(log=self._log)
        self._finra_api = Finra(log=self._log)
        self._sfdc = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken,
                          domain=con.SFDomain, verbose=False, _dir=con.BaseDir)
        self.vars = build_queue.build_queue(sfdc=self._sfdc, log=self._log)
        self.main_contact_based_processing()

    def main_contact_based_processing(self):
        """
        This method determines how to route a pending list request, based on the Salesforce object type.

        An abstracted path looks like the following:
            1) Check if there are pending lists.  # TODO: Add check before looping through each list.
            2) If lists are pending, begin looping through all available lists.
            3) Check that each pending list is of a workable extension.
                See Also: ListProcessing().is_bad_extension() method for extensions that
                            will stop the processing.
            4) If the list has an acceptable extension, enter a
                routing statement to determine which rules to process the list request
                through.
            5) After completing processing, notify the requester, record stats, and
                begin processing any additional lists.
        Returns
        -------
            Nothing
        """
        for _vars in self.vars:
            if not self.is_bad_extension(_vars):
                _vars.state = _vars.States(_vars.state + 1).value
                try:
                    _vars.state = _vars.States(_vars.state + 1).value
                    if _vars.list_type == 'Campaign':
                        _vars = self.campaign_processing(_vars)

                    elif _vars.list_type == 'Account':
                        _vars = self.account_processing(_vars)

                    elif _vars.list_type == 'BizDev Group':
                        _vars = self.bizdev_processing(_vars)

                    _ghelp.record_processing_stats(_vars['Stats Data'])

                except:
                    self.create_log_record_of_current_list_data(msg=str(traceback.format_exc()))

                finally:
                    self._log.info('List #%s processed.' % _vars['ListIndex'])

    def is_bad_extension(self, _vars):
        """
        Checks if the a list request has an extension that can be processed. If a list is
        unable to be processed, notify the requester of the situation.

        Parameters
        ----------
        _vars
            Python dictionary containing metadata regarding a list request.

        Returns
        -------
            Boolean (True or False)
        """
        if _vars.extension in ['.pdf', '.gif', '.png', '.jpg', '.doc', '.docx']:
            obj_name = _vars.account_name if _vars.account_name is not None else _vars.object_name
            sub = 'LMA: Unable to Process List Attached to %s' % obj_name
            msg = 'The list attached to %s has a file extension, %s,  that cannot currently be processed by the ' \
                  'List Management App.' % (obj_name, _vars.extension)
            self._log.warning(msg)
            Email(con.SMTPUser, con.SMTPPass, self._log).send_new_email(
                subject=sub, to=[_vars.requested_by_email], body=msg, attachments=None
                , name=con.FullName
            )
            self._sfdc.update_records(obj='List__c', fields=['Status__c'],
                                      upload_data=[[_vars.list_id, 'Unable to Process']])
            return True
        else:
            return False

    def campaign_processing(self, _vars):
        """
        Handles all processing for lists that are sourced from the campaign object.

        Steps
        -----
        1) Predict headers and pre_process each file.
        2) Searches against SalesForce for matches on: a) CRDNumber b) AMPFId c) Email d) LookupName.
        3) If advisors are not found, scrape data from FINRA based on First, Last, and Account Name.
        4) If advisors are scraped, re-search those advisors against SalesForce contact list.
        5) Parse list into actionable pieces: a) upload to campaign b) create c) not found.
        6) Prepare data for upload into SalesForce (via source_channel function), do so for each file created above.
        7) Extract stats from search processing, send notification email, and update SalesForce list record.
        8) Ff applicable, drop file in the bulk_processing network drive to create or update SaleForce contacts.


        Parameters
        ----------
        _vars
            Python dictionary containing metadata regarding a list request.

        Returns
        -------
            Nothing
        """
        _vars = predicts.predict_headers_and_pre_processing(_vars, self._log, self.mode)
        _vars = self._search_api.perform_search_one(_vars)
        # try:
        _vars = self.finra_search_and_search_two(_vars)
        # except:
        #     self._log.info('An error occurred during FINRA or SearchTwo processing. Skipping.')
        #     pass

        _vars = _process.parse_list_based_on_type(_vars, log=self._log)
        _vars = _process.source_channel(_vars, log=self._log)

        _vars.update(_process.sfdc_upload(path=_vars['cmp_upload_path'], obj=_vars['Object'],
                                          obj_id=_vars['ObjectId'], session=self._sfdc,
                                          log=self._log))
        _vars.update(_process.extract_dictionary_values(dict_data=_vars, log=self._log))
        if _vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(_vars['to_create_path'], self._log)
        else:
            self._log.info(_steps[2])
        return _vars

    def account_processing(self, _vars):
        """
        Handles all processing for lists that are sourced from the account object.

        Steps
        -----
        1) Predicts headers and pre_process each file.
        2) Searches against SalesForce for matches on: a) CRDNumber b) AMPFId c) Email d) LookupName.
        3) If advisors are not found, scrape data from FINRA based on First, Last, and Account Name.
        4) If advisors are scraped, re-search those advisors against SalesForce.
        5) For all found advisors, scrape their licenses (and other metadata) from FINRA
        6) Parse list into actionable pieces: a) upload to campaign b) create c) not found.
        7) Update the 'Last List Upload' field on the account record.
        8) Prepare data for upload into SalesForce (via source_channel function), do so for each file created above.
        9) Extract stats from search processing, send notification email, and update SalesForce list record.
        10) If applicable, drop files in the bulk_processing network drive to create or update SaleForce contacts.

        Parameters
        ----------
        _vars
            Python dictionary containing metadata regarding a list request.

        Returns
        -------
            Nothing
        """
        _vars = predicts.predict_headers_and_pre_processing(_vars, self._log, self.mode)
        _vars = self._search_api.perform_search_one(_vars)
        try:
            _vars = self.finra_search_and_search_two(_vars)
        except:
            self._log.info('An error occurred during FINRA or SearchTwo processing, Skipping.')
            pass
        _vars.update(self._finra_api.scrape(_vars['Found Path'], scrape_type='all'))
        _vars.update(_process.parse_list_based_on_type(path=_vars['Found Path'], l_type=_vars['Object'],
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

        _vars.update(_process.source_channel(_vars['update_path'], _vars['Record Name'],
                                             _vars['ObjectId'], _vars['Object'], log=self._log))

        _vars.update(_process.extract_dictionary_values(dict_data=_vars, log=self._log))

        if _vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(_vars['update_path'], self._log)
            if _ghelp.is_path(_vars['to_create_path']):
                _vars.update(_process.source_channel(_vars['to_create_path'], _vars['Record Name'],
                                                     _vars['ObjectId'], _vars['Object'],
                                                     _vars['ObjectId'], log=self._log))
                _ghelp.drop_in_bulk_processing(_vars['to_create_path'], self._log)

        else:
            self._log.info(_steps[2])
        return _vars

    def bizdev_processing(self, _vars):
        """
        Handles all processing for lists that are sourced from the BizDev Group object.

        Steps
        -----
        1) Predicts headers and pre_process each file.
        2) Searches against SalesForce for matches on: a) CRDNumber b) AMPFId c) Email d) LookupName.
        3) If advisors are not found, scrape data from FINRA based on First, Last, and Account Name.
        4) If advisors are scraped, re-search those advisors against SalesForce.
        5) For all found advisors, scrape their licenses (and other metadata) from FINRA
        6) Parse list into actionable pieces: a) upload to campaign b) create c) not found.
        7) Update the 'Last List Upload' field on the bizdev group record.
        8) Prepare data for upload into SalesForce (via source_channel function), do so for each file created above.
        9) Extract stats from search processing, send notification email, and update SalesForce list record.
        10) If applicable, drop files in the bulk_processing network drive to create or update SaleForce contacts.

        Parameters
        ----------
        _vars
            Python dictionary containing metadata regarding a list request.

        Returns
        -------
            Nothing
        """
        _vars = predicts.predict_headers_and_pre_processing(_vars, self._log, self.mode)
        _vars = self._search_api.perform_search_one(_vars)
        try:
            _vars = self.finra_search_and_search_two(_vars)
        except:
            self._log.info('An error occurred during FINRA or SearchTwo processing.')
            pass
        _vars.update(self._finra_api.scrape(_vars['Found Path'], scrape_type='all', save=True))
        _vars.update(_process.parse_list_based_on_type(path=_vars['Found Path'], l_type=_vars['Object'],
                                                       pre_or_post=_vars['Pre_or_Post'], log=self._log,
                                                       to_create_path=_vars['to_create_path']))
        _vars.update(_process.sfdc_upload(path=_vars['bdg_update_path'], obj=_vars['Object'],
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

        _vars.update(_process.source_channel(_vars['update_path'], _vars['Record Name'],
                                             _vars['ObjectId'], _vars['Object'],
                                             _vars['CmpAccountID'], log=self._log))
        _vars.update(_process.source_channel(_vars['to_create_path'], _vars['Record Name'],
                                             _vars['ObjectId'], _vars['Object'],
                                             _vars['CmpAccountID'], log=self._log))
        _vars.update(_process.source_channel(_vars['bdg_update_path'], _vars['Record Name'],
                                             _vars['ObjectId'], _vars['Object'],
                                             _vars['CmpAccountID'], log=self._log))
        _vars.update(_process.extract_dictionary_values(dict_data=_vars, log=self._log))

        if _vars['Move To Bulk']:
            _ghelp.drop_in_bulk_processing(_vars['to_create_path'], self._log)
            _ghelp.drop_in_bulk_processing(_vars['update_path'], self._log)

        else:
            self._log.info(_steps[2])
        return _vars

    def finra_search_and_search_two(self, _vars):
        """
        Handles all Finra and secondary searching (if necessary).

        Steps
        -----
        1) If advisors are not found and are missing CRDNumbers, scrape FINRA
        2) If FINRA is scraped, search our SalesForce database to increase our likely match-rate.

        Parameters
        ----------
        _vars
            Python dictionary containing metadata regarding a list request.

        Returns
        -------
            Updated python dictionary containing metadata regarding a list request.
        """
        if len(_vars.list_df.index) > 0 and _vars.search_finra:

            _vars = self._finra_api.scrape(_vars=_vars, scrape_type='crd', parse_list=True)
            # if (_vars['SFDC_Found'] + _vars['FINRA_Found']) < _vars['Total Records']:
            #     _vars.update(
            #         self._search_api.perform_sec_search(_vars['No CRD'], _vars['FINRA_SEC Found']))
            #
            # else:
            #     self._log.info(_steps[0])

            _vars = self._search_api.perform_search_two(_vars)
        else:
            self._log.info(_steps[1])
        return _vars

    def create_log_record_of_current_list_data(self, msg):
        """
        Catches a 'fatal error' incurred by the list program. Halts all processing if called.

        Parameters
        ----------
        msg
            Error message.

        Returns
        -------
            Nothing
        """
        self._log.warning('A fatal error has occurred. Refer to message traceback for insight into '
                          'the issue.')
        self._log.error(msg)
        raise RuntimeError(msg)


if __name__ == '__main__':
    lp = ListProcessing()
