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
from PythonUtilities.salesforcipy import SFPy

sys.path.append(os.path.abspath('.'))

from ListManagement.config import Config

from ListManagement.core.build_sf_source import build_current_fa_list
from ListManagement.core.build_queue import establish_queue
from ListManagement.core.ml import header_predictions as predicts
from ListManagement.core.ml.model import LM_Model as Model
from ListManagement.core.standardization import DataStandardization
from ListManagement.core.search import Search, Finra
from ListManagement.core.data_staging import Staging
from ListManagement.core.parsing import Parser
from ListManagement.core.pruning import Pruning
from ListManagement.core.uploads import Uploader
from ListManagement.core.stats import ProcessingStats
from ListManagement.core.notifications import Notify
from ListManagement.core.intel_hook import init_intel_processing

con = Config()

_steps = [
    '\nSkipping step 6, because all contacts were found.',
    '\nSkipping email, LkupName, FINRA, and SEC searches.',
    '\nContacts will not be created. Not enough information provided.']


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
        self._sfdc = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken,
                          domain=con.SFDomain, verbose=False, _dir=con.BaseDir)
        self._search_api = None
        self._finra_api = None
        self._standardizer = None
        self._stager = None
        self._parser = None
        self._pruner = None
        self._uploader = None
        self._stats = None
        self._notifier = None
        self._model = Model(self._log)
        self._sfdc_file_check()
        self.vars = establish_queue(sfdc=self._sfdc, log=self._log)
        self.main_contact_based_processing()

    def _sfdc_file_check(self):
        if not os.path.isfile(con.SFDCLoc):
            build_current_fa_list(self._sfdc)

    def main_contact_based_processing(self):
        """
        This method determines how to route a pending list request, based on the Salesforce object type.

        An abstracted path looks like the following:
            1) Check if there are pending lists.
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
        for item in self.vars:
            if item.processable:
                item.update_state()
                self._search_api = Search(log=self._log)
                self._finra_api = Finra(log=self._log)
                self._standardizer = DataStandardization(self._log)
                self._stager = Staging(self._log)
                self._parser = Parser(self._log)
                self._pruner = Pruning(self._log)
                self._uploader = Uploader(self._log)
                self._stats = ProcessingStats(self._log)
                self._notifier = Notify(self._log)
                try:
                    intel_source = "{0}--{1}-{2}-{3}".format(item.process_start.date(), item.list_type,
                                                             item.object_name,
                                                             os.path.basename(item.list_source['path']))
                    init_intel_processing(item.list_source['path'], source=intel_source)
                    self._log.info('Beginning processing on {}.'.format(item.object_name))
                    item, self._model = predicts.predict_headers_and_pre_processing(item, self._log, self.mode,
                                                                                    self._model)
                    item = self._standardizer.standardize_all(item)

                    item = self._search_api.perform_search_one(item)

                    if item.search_finra:
                        item = self._finra_api.scrape(_vars=item, scrape_type='crd', parse_list=True)
                        item = self._search_api.perform_search_two(item)

                    if item.list_type == 'BizDev Group':
                        item = self._finra_api.scrape(item, scrape_type='all', save=True)

                    item = self._stager.fill_gaps(item)
                    item = self._parser.split_found_into_actions(item, self._sfdc)
                    item = self._pruner.upload_preparation(item)
                    item.save_frames(lead_hook=True, dba=self._model.dba, conn=self._model.conn)
                    item.gather_attachments()
                    item = self._uploader.upload(item, self._sfdc)
                    self._stats.record(item, self._sfdc)
                    self._notifier.send_completion_message(item)


                except:
                    self.create_log_record_of_current_list_data(msg=str(traceback.format_exc()))

                finally:
                    self._log.info('List #%s processed.\n\n' % item.id)
            else:
                self._notifier.send_unable_to_process_message(item)

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
