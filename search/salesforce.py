"""
salesforce.py
======================================================
Provides a set of actions to compare the Contact object
of a Salesforce CRM to a 3rd party list (excel, csv).
"""

import os
import time

import numpy as np

try:
    from ListManagement.legacy.get_sf_adv_list import run
    from ListManagement.utility.general import create_path_name, today
    from ListManagement.utility.pandas_helper import read_df, save_df, make_df, is_null
except:
    from legacy.get_sf_adv_list import run
    from utility.gen_helper import create_path_name, today
    from utility.pandas_helper import read_df, save_df, make_df, is_null

_todays_sfdc_advisor_list = 'T:\\Shared\\FS2 Business Operations\\Python Search Program' \
                            '\\Salesforce Data Files\\SFDC Advisor List as of ' \
                            + time.strftime("%m-%d-%y") + '.csv'
_names_to_remove = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", 'aams', 'aif', 'aifa', 'bcm', 'caia',
                    'casl', 'ccps', 'cdfa', 'cea', 'cebs', 'ces', 'cfa', 'cfe', 'cfp', 'cfs', 'chfc',
                    'chfcicap', 'chfebc', 'cic', 'cima', 'cis', 'cltc', 'clu', 'cpa', 'cpwa', 'crpc',
                    'crps', 'csa', 'iar', 'jd', 'lutcf', 'mba', 'msa', 'msfp', 'pfs', 'phd', 'ppc']


class Search:
    """
    Search object that orchestrates comparisons and parsing between
    source (3rd party, Finra, et al) data sets and target
    (Salesforce contact object) data sets.
    """

    def __init__(self, log=None):
        """
        Instantiates a bare Search object.
        """
        self.log = log
        self._today = today
        self._sfdc_file_check()
        self._SFDC_advisor_list = read_df(_todays_sfdc_advisor_list)
        self.__preprocess_sfdc_list()
        self._search_fields = ['AMPFMBRID', 'Email', 'LkupName']
        self._return_fields = ['CRDNumber', 'AccountId', 'SourceChannel',
                               'ContactID', 'Needs Info Updated?', 'BizDev Group']
        self._keep_cols = []
        self._is_crd_check = False
        self._search_one_crd_additional = False
        self._save_to_review_df = False
        self._num_searches_performed = 0
        self._total_found = 0
        self._num_found_contacts = 0
        self._review_path = ''
        self._search_list = ''
        self._found_contact_path = ''
        self._to_create_path = ''
        self._list_type = ''
        self._sec_files = ''
        self._sec_path = 'T:\\Shared\\FS2 Business Operations\\Python Search Program\\SEC_Data\\' \
                         'Individuals\\processed_data\\' + self._today + '\\'

    def _sfdc_file_check(self):
        """
        Helper method to see the Salesforce advisor list has been extracted and kicks off
        the appropriate processing if it has not.

        Returns
        -------
            Nothing
        """
        if not os.path.exists(_todays_sfdc_advisor_list):
            self.log.info("Please wait. Downloading SFDC list, as today's file was not available.")

            run(path_name=_todays_sfdc_advisor_list, logger=self.log)

    def __init_list_metadata(self, _vars, search_two=False):
        """
        Helper method which stores the list file's column names and determines if it's known, or not.

        Returns
        -------
            Nothing
        """
        if search_two:
            self._headers = _vars.finra_found_df.columns.values
        else:
            self._headers = _vars.list_df.columns.values

        self._keep_cols = [c for c in self._headers if 'unknown' not in c.lower()]

    @staticmethod
    def _crd_formatter(_series):
        _series = _series.astype(str)
        _series = _series.fillna('').replace('nan', '').apply(lambda x: x.split('.')[0] if '.' in x else x)
        return _series

    def __preprocess_sfdc_list(self):
        """
        Helper method that pre-preprocesses our source SalesForce contact file.
            1) identify and keep only unique records (rows)
            2) convert the CRDNumber column to string type
        Returns
        -------
            Nothing
        """
        _, i = np.unique(self._SFDC_advisor_list.columns, return_index=True)
        self._SFDC_advisor_list = self._SFDC_advisor_list.iloc[:, i]
        self._SFDC_advisor_list['CRDNumber'] = self._crd_formatter(self._SFDC_advisor_list['CRDNumber'])

    def __data_preprocessing(self, _vars, additional=False, search_two=False):
        """
        Helper method that attempts to clean the 3rd party list file.

        Parameters
        ----------
        additional
            Boolean; default=False
        Returns
        -------
            Nothing
        """
        if search_two:
            frame = _vars.finra_found_df
        else:
            frame = _vars.list_df
        for col in frame.columns.tolist():
            if col in self._SFDC_advisor_list.columns.tolist():
                if col == 'CRDNumber':
                    frame[col] = self._crd_formatter(frame[col])
                else:
                    frame[col] = frame[col].astype(self._SFDC_advisor_list[col].dtypes.name)
        frame = frame[self._keep_cols]
        frame.fillna('', inplace=True)
        if len(frame.columns) > 3:
            frame.dropna(axis=0, thresh=3, inplace=True)
        if additional:
            frame = self._name_preprocessing(frame)
            frame = self._lkup_name_address_processing(frame)
            if 'FinraLookup' not in frame.columns.tolist():
                _vars.search_finra = False
        self._headers = frame.columns.values

        if search_two:
            _vars.finra_found_df = frame
        else:
            _vars.list_df = frame

        return _vars

    def __check_list_type(self, _vars):
        """
        Helper method to subset the fields returned upon merging 3rd party list with SF,
        based on the source object.

        Returns
        -------
            Nothing
        """
        if _vars.list_type != 'BizDev Group':
            del self._return_fields[-1]

    def _df_column_preprocessing(self, df):
        """
        Helper method to encode columns in a data frame to 'utf-8' based on the column's data type.

        Parameters
        ----------
        df
            A pandas data frame object
        Returns
        -------
            A transformed (and preprocessed) data frame object.
        """
        count = 0
        for col in df.columns:
            if df[col].dtype not in ('int64', 'float64', 'object'):
                for cell in range(0, len(df[col])):
                    df[cell][count] = df[cell][count].encode('utf-8', 'ignore')
            else:
                count += 1
        return df

    def __join_headers(self, header):
        """
        Helper method to combine merge key (header) and the metadata we want from SFDC to associate with
        an individual record (row) from a 3rd party list.

        Parameters
        ----------
        header
            A string; Merge key, i.e. a column we will merge on
        Returns
        -------
            List; Our key and the joined headers
            Examples
                (ex. [CRDNumber, ContactId, AccountId, SourceChannel, etc.])
        """
        joined_headers = [header]
        [joined_headers.append(rf) for rf in self._return_fields]
        return list(joined_headers)

    def __create_meta_data(self, _vars, headers=None, search_two=False):
        """
        Helper method to determine how a merged list (3rd party & FS SFDC data) get's handled.

        Steps:
        ------
        1) Determine if this is the first, or second, set of searches against SFDC.
        2) If this is the second set of searches, then 'found contacts' are only records that have a ContactID
        3) If this is the first set of searches then:
            a) If a CRD search is passed to the 'create_meta_data' method:
                1a. 'found contacts' are records that have a ContactID merged with the original data
                2a. If CRD's are provided for all records, set 'to_finra' to False and rename the CRDNumber column
                3a. If the length of the search list and found contact list are not the same, we need to
                    perform additional searches to attempt to identify additional matches & duplicate records.

        Parameters
        ----------
        headers
            List; Contains the headers in a given pandas data frame.
        search_two
            Boolean; defaults to False. Used to denote if this is the second search or not.
        Returns
        -------
            Nothing.
        """
        # TODO: may need to try and clean this method up, it's a bit confusing and messy.
        if search_two:
            # _vars.found_df = read_df(self._found_contact_path)
            finra_matched_to_sf = _vars.finra_found_df[_vars.finra_found_df['ContactID'] != '']
            self.log.info('\nMatched CRDs from FINRA to %s records in Salesforce' % len(finra_matched_to_sf))
            _vars.found_df = _vars.found_df.append(finra_matched_to_sf, ignore_index=True, sort=False)

        else:
            if self._is_crd_check and 'CRD Provided by List' not in self._headers:
                _vars.found_df = _vars.found_df.append(
                    _vars.list_df[_vars.list_df['ContactID'] != ''], ignore_index=True)

                if _vars.list_df['CRDNumber'].count() == len(_vars.list_df.index) and \
                        len(_vars.list_df['CRDNumber'].nonzero()[0]) == len(_vars.list_df.index):

                    _vars.list_df.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
                    _vars.search_finra = False
                    if len(_vars.list_df.index) != len(_vars.found_df.index):
                        self._search_one_crd_additional = True
                        self.log.info('CRD Info provided for all contacts. Will not search FINRA, but will '
                                      'perform remaining standard searches to maximize match rate.')
                        _vars.list_df = _vars.list_df[_vars.list_df['ContactID'] == '']
                        # self._contacts_to_review = self._contacts_to_review.append(
                        #     _vars.list_df[_vars.list_df['ContactID'] == ''], ignore_index=True)
                        # self.log.info('CRD Info provided for all contacts. Will not search FINRA.')

                else:
                    _vars.list_df = _vars.list_df[_vars.list_df['ContactID'] == '']
                    _vars.list_df.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
                self._headers = _vars.list_df.columns.values

            else:
                _vars.list_df.fillna('', inplace=True)
                if "CRD Provided by List" in self._headers:
                    _vars = self._identify_to_review_records(_vars)
                    _vars.list_df.rename(columns={'CRD Provided by List': 'CRDNumber'}, inplace=True)
                    _vars.found_df = _vars.found_df.append(
                        _vars.list_df[_vars.list_df['ContactID'] != ''],
                        ignore_index=True)
                    _vars.list_df = _vars.list_df[_vars.list_df['ContactID'] == '']
                    _vars.list_df.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)

                else:
                    _vars.found_df = _vars.found_df.append(
                        _vars.list_df[_vars.list_df['CRDNumber'] != ''],
                        ignore_index=True)
                    _vars.list_df = _vars.list_df[_vars.list_df['CRDNumber'] == '']

            for r_field in self._return_fields:
                try:
                    del _vars.list_df[r_field]
                except:
                    pass
        return _vars

    def _identify_to_review_records(self, _vars):
        """
        Helper method that's used to help identify records that need to be manually reviewed.

        Steps:
        ------
        1) flag a record as needing review if:
            a) a SFDC CRDNumber is not null doesn't equal the CRD Provided by List Number.

        Returns
        -------
            Nothing
        """
        _vars.list_df['ToReview'] = 0
        _vars.list_df['ToReview'] = _vars.list_df.apply(
            lambda x: 1 if x['CRDNumber'] != '' and x['CRDNumber'] != x["CRD Provided by List"] else x[
                'ToReview'], axis=1)
        _vars.review_df = _vars.review_df.append(
            _vars.list_df[_vars.list_df['ToReview'] == 1], ignore_index=True)
        _vars.list_df = _vars.list_df[_vars.list_df['ToReview'] == 0]
        del _vars.list_df['CRDNumber']
        del _vars.list_df['ToReview']
        self.log.info('Identified %s contacts that need to be reviewed.' % len(_vars.review_df.index))
        return _vars

    def __num_found(self, found_df):
        """
        Helper method to aggregate the number of found contacts throughout all iterations of the search process.

        Parameters
        ----------
        found_df
            A pandas data frame.

        Returns
        -------
            Nothing
        """

        self._num_found_contacts = len(found_df)
        self._total_found += self._num_found_contacts

    def __search_and_merge(self, _vars, search_fields, search_two=False):
        """
        Helper method that actually performs the merging of data from 3rd party and SF list files.

        Steps:
        ------
        1) for each search field, determine if it's present in the 3rd party file's column names
        2) create a sliced data frame of SF data to include only columns we need in 'n'th search (via join_headers)
        3) merge data from 3rd party and SF subsetted data frame, merging on the search header
        4) submit the merged 3rd party list to the create_metadata method to determine how the list
            should be further sliced for subsequent processing, or if all records were found.

        Parameters
        ----------
        search_fields
            list of columns to search (pandas merge) on
        search_two
            Boolean; defaults to False. Used to denote if this is the second search or not.

        Returns
        -------
            Nothing
        """
        if search_two:
            frame = _vars.finra_found_df
        else:
            frame = _vars.list_df

        if len(search_fields) > 1:
            self._return_fields = ['CRDNumber', 'AccountId', 'SourceChannel', 'ContactID', 'Needs Info Updated?',
                                   'BizDev Group']
        for header in search_fields:
            if header in self._headers:
                self._num_searches_performed += 1
                self.log.info('Performing search #%s on %s' % (self._num_searches_performed, header))
                self._joined_headers = self.__join_headers(header)

                self._headers_and_ids = make_df()
                self._headers_and_ids = self._SFDC_advisor_list[self._joined_headers]
                if header == 'CRDNumber':
                    self._headers_and_ids = self._headers_and_ids[self._headers_and_ids[header] != '']
                frame = frame.merge(self._headers_and_ids, how='left', on=header, sort=False)
                frame.fillna('', inplace=True)

                self._num_searched_on = len(frame.index)
                if search_two:
                    _vars.finra_found_df = frame
                else:
                    _vars.list_df = frame

                _vars = self.__create_meta_data(_vars, self._headers, search_two=search_two)
                self._num_remaining = len(frame.index)

                self.__num_found(_vars.found_df)
                _vars.search_found[header] = self._num_searched_on - self._num_remaining

                self.log.info('Found %s on %s search.\n' % (_vars.search_found[header], header))
                self._headers = frame.columns.values
        if search_two:
            _vars.finra_found_df = frame
        else:
            _vars.list_df = frame

        return _vars

    def _crd_search(self, _vars, search_field=['CRDNumber']):
        """
        Helper method to help properly guide the search process when matching on CRDNumbers.

        Steps:
        ------
        1) set the fields that will be returned to the 3rd party list from the SFDC file, and fill blank values
        2) merge the 3rd party list and SFDC file, leveraging the __search_and_merge method.

        Parameters
        ----------
        search_field
            List; The field to use as our 'join on'/'merge on' key during a search.

        Returns
        -------
            Updated Search object.
        """
        self._is_crd_check = True
        self._return_fields = ['AccountId', 'SourceChannel',
                               'Needs Info Updated?', 'ContactID', 'BizDev Group']
        _vars.list_df.fillna('', inplace=True)
        _vars = self.__search_and_merge(_vars, search_field)
        return _vars

    def _lkup_name_address_processing(self, frame):
        """
        Helper method to create the LkupName search field, if the necessary columns are present,
        and pre-process them.

        Steps:
        ------
        1) Check if PostalCode and State are available in the data frame, and convert the data types to strings
        2) Loop through each row, and attempt to clean the Postal code.
        3) Attempt to clean the State column, if the name (rather than abbr.) is provided. leverage us.states.lookup
        4) Check if FirstName and LastName are present
            a) If all columns are present combine first 3 chars of First Name, Last Name, Account, State, and Postal
            b) Ex. RicSchools FS Investm PA 19112

        Parameters
        ----------
        headers
            List; list of column headers of the data frame.
        search_list
            A pandas data frame.

        Returns
        -------
            An updated (enriched) pandas data frame object.
        """
        if set(['MailingPostalCode', 'MailingState']).issubset(frame.columns.tolist()):
            import us
            import uszipcode
            zs = uszipcode.ZipcodeSearchEngine()

            frame['MailingPostalCode'] = frame['MailingPostalCode'].astype(str)

            frame['MailingPostalCode'] = frame.apply(
                lambda x: x['MailingPostalCode'].split('-')[0] if '-' in x['MailingPostalCode'] else x[
                    'MailingPostalCode'], axis=1)

            frame['MailingPostalCode'] = frame.apply(
                lambda x: x['MailingPostalCode'][:5] if len(x['MailingPostalCode']) == 9 else x['MailingPostalCode'],
                axis=1)

            frame['MailingPostalCode'] = frame.apply(
                lambda x: str(0) + x['MailingPostalCode'][:4] if len(x['MailingPostalCode']) == 8 else x[
                    'MailingPostalCode'], axis=1)

            try:
                frame['MailingState'] = frame.apply(
                    lambda x: us.states.lookup(x['MailingState'].str, use_cache=False).abbr if len(
                        x['MailingState']) > 2 else x['MailingState'], axis=1)
            except:
                try:
                    self.log.info("Unable to transform MailingState with the python 'us' library.")
                    frame['MailingState'] = frame.apply(
                        lambda x: zs.by_zipcode(x['MailingPostalCode'])['State'], axis=1)
                except:
                    self.log.info("Unable to transform MailingState with the python 'uszipcode' library.")
                    self.log.info('Will forgo attempting to transform MailingState')

            """ archaic code for zip below
            frame['MailingPostalCode'] = frame['MailingPostalCode'].astype(str)
            for index, row in frame.iterrows():
                frame.loc[index, "MailingPostalCode"] = row["MailingPostalCode"].split('-')[0]
                if len(row["MailingPostalCode"]) == 9:
                    frame.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:5]
                elif len(row["MailingPostalCode"]) == 8:
                    frame.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:4]

            if np.mean(frame['MailingState'].str.len()) > 2:
                import us
                self.log.info('MailingState column needs to be transformed.')
                for index, row in frame.iterrows():
                    try:
                        state = us.states.lookup(frame.loc[index, "MailingState"])
                        frame.loc[index, "MailingState"] = str(state.abbr)
                    except:
                        pass
            """
            # headers = frame.columns.values
            # if "FirstName" in headers and "LastName" in headers:
            #     frame["FirstName"] = frame["FirstName"].apply(lambda x: x.title())
            #     frame["LastName"] = frame["LastName"].apply(lambda x: x.title())
            #     frame["Account"] = frame["Account"].str.replace(',', '')
            #     frame["LkupName"] = frame["FirstName"].str[:3] + frame["LastName"] + frame[
            #                                                                                                "Account"].str[
            #                                                                                            :10] + \
            #                               frame["MailingState"] + frame["MailingPostalCode"]  # .str[:-2]
            #
            # else:
            #     self.log.info("Advisor name or account information missing")
        try:
            frame['FinraLookup'] = frame["FirstName"] + ' ' + frame["LastName"] + " " + \
                                   frame["Account"].str[:9]
        except:
            pass
        return frame

    def _clean_comma_and_space(self, row):
        """
        Helper method to remove spaces and commas from a row within a data frame.

        Parameters
        ----------
        row
            An un-normalized pandas data frame row containing spaces and commas.

        Returns
        -------
            A normalized pandas data frame row void of spaces and commas.
        """
        if ' ' in row:
            row.replace(' ', '')
        if ',' in row:
            row.replace(',', ', ')
        return row

    def _name_preprocessing(self, frame):
        """
        Helper method to split and clean the FullName column of the 3rd party data frame.

        Steps:
        ------
        1) if FullName is present, create a column for First and Last Name.
        2) iterate through the data frame and if a comma is present in the Full Name, check if:
            a) a space preceeds a comma. if so, assume the 1st element of the split FullName is the First Name
                and the 2nd element is the Last Name.
            b) a comma preceeds a space. if so, assume the inverse of the previous statement.
        3) if no comma is present, assume First Last / (suffix or middle) - splitting the FullName on spaces (' ')
        4) attempt to remove potential suffixes (which may include .jr, iii, cfa, etc.)
        5) finally, attempt to appropriately assign the First and Last Name fields to the appropriate columns.

        Parameters
        ----------
        headers
            List; columns names of a pandas data frame
        search_list
            A pandas data frame.

        Returns
        -------
            An updated (enriched) pandas data frame object.
        """
        names_to_remove = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", 'aams', 'aif', 'aifa', 'bcm', 'caia',
                           'casl', 'ccps', 'cdfa', 'cea', 'cebs', 'ces', 'cfa', 'cfe', 'cfp', 'cfs', 'chfc',
                           'chfcicap', 'chfebc', 'cic', 'cima', 'cis', 'cltc', 'clu', 'cpa', 'cpwa', 'crpc',
                           'crps', 'csa', 'iar', 'jd', 'lutcf', 'mba', 'msa', 'msfp', 'pfs', 'phd', 'ppc']

        if "FullName" in frame.columns.tolist():
            frame.insert(0, "LastName", "")
            frame.insert(0, "FirstName", "")
            for index, row in frame.iterrows():
                if ',' in row["FullName"]:
                    if row["FullName"].index(' ') < row["FullName"].index(','):
                        frame.loc[index, "FirstName"] = row["FullName"].split(' ')[0]
                        frame.loc[index, "LastName"] = ' '.join(row["FullName"].split(' ')[1:])
                    else:
                        frame.loc[index, "LastName"] = row["FullName"].split(',')[0]
                        frame.loc[index, "FirstName"] = row["FullName"].split(' ')[1]
                else:
                    full_name_list = row["FullName"].split()
                    for name in full_name_list:
                        if name.lower() in names_to_remove:
                            full_name_list.pop(full_name_list.index(name))
                    if len(full_name_list) == 3:
                        frame.loc[index, "FirstName"] = full_name_list[0]
                        frame.loc[index, "LastName"] = full_name_list[2]
                    else:
                        frame.loc[index, "FirstName"] = full_name_list[0]
                        frame.loc[index, "LastName"] = full_name_list[1]
        return frame

    def perform_search_one(self, _vars):
        """
        User method to implement the first comparison between a 3rd party list and Salesforce.

        Parameters
        ----------
        searching_list_path
            String; Represents a full file path.
        list_type
            String; Represents the name of a Salesforce object.

        Returns
        -------
            A python dictionary containing next steps for list processing.
        """
        _vars.state = _vars.States(_vars.state + 1).value
        self.log.info(
            'Implementing search_one method on the %s list. Search 1 pre-processing begins.' % _vars.list_type)
        self.__init_list_metadata(_vars)
        self.__check_list_type(_vars)
        _vars = self.__data_preprocessing(_vars, additional=True)
        _vars.found_path = create_path_name(path=_vars.list_base_path, new_name='_foundcontacts')
        _vars.review_path = create_path_name(path=_vars.list_base_path, new_name='_review_contacts')
        _vars.create_path = create_path_name(path=_vars.list_base_path, new_name='to_create')
        _vars.found_df = make_df()
        _vars.review_df = make_df()
        _vars.create_df = make_df()

        if 'CRDNumber' in self._headers and not self._is_crd_check:
            self.log.info("Performing a CRD search, as 'CRDNumber' is present.")
            _vars = self._crd_search(_vars)
            if self._search_one_crd_additional:
                self.log.info("Performing additional searches as the CRD search didn't find all records successfully.")
                _vars = self.__search_and_merge(_vars, self._search_fields)

                _vars.list_df.rename(columns={'CRD Provided by List': 'CRDNumber'}, inplace=True)
                _vars.create_df = _vars.list_df[~is_null(_vars.list_df['CRDNumber'])]
                _vars.list_df = _vars.list_df[is_null(_vars.list_df['CRDNumber'])]

        else:
            self.log.info("Performing standard search, as 'CRDNumber' is not present.")
            _vars = self.__search_and_merge(_vars, self._search_fields)

        return _vars

    def perform_search_two(self, _vars):
        """
        User method to implement the second comparison between a 3rd party list and Salesforce.

        All advisors found during the call of this method are moved from the searching_list_path
        to the found_path.

        Parameters
        ----------
        searching_list_path
            String; Represents a full file path of the un-matched advisors.
        found_path
            String; Represents a full file path of the matched advisors.
        list_type
            String; Represents the name of a Salesforce object.

        Returns
        -------
            A python dictionary containing next steps for list processing.
        """
        self.log.info(
            'Implementing search_two method on the %s list. Search 2 pre-processing begins.' % _vars.list_type)
        self._search_fields = ['CRDNumber']
        self._return_fields = ['AccountId', 'SourceChannel', 'ContactID',
                               'Needs Info Updated?', 'BizDev Group']
        self.__init_list_metadata(_vars, search_two=True)
        self._keep_cols = [c for c in _vars.finra_found_df.columns if not c.lower()[:7].__contains__('unknown')]

        self.__check_list_type(_vars)
        _vars = self.__data_preprocessing(_vars, search_two=True)
        self.log.info('Searching against SFDC following FINRA/SEC searches.')
        _vars = self.__search_and_merge(_vars, search_fields=self._search_fields, search_two=True)
        return _vars

    def perform_sec_search(self, _vars, searching_list_path, found_path):
        if not os.path.exists(self._sec_path):
            self.log.info("Skipping SEC Search. Today's files could not be found in the listed directory.")
            return _vars

        self.log.info('Searching against SEC Data.')
        self._search_list = read_df(searching_list_path)
        self.__init_list_metadata(_vars)
        self._sec_files = os.listdir(self._sec_path)
        self._search_fields = ['LkupName']

        for sec in self._sec_files:
            self._sec_df = read_df(sec)
            self._sec_df.rename(columns={'indvlPK': 'CRDNumber'}, inplace=True)
            self.__search_and_merge(self._search_fields)

        return _vars
