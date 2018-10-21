"""
salesforce.py
======================================================
Provides a set of actions to compare the Contact object
of a Salesforce CRM to a 3rd party list (excel, csv).
"""
from ListManagement.utils.general import today
from ListManagement.utils.pandas_helper import make_df, is_null


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
        self._SFDC_advisor_list = None
        self._keep_cols = []
        self._is_crd_check = False
        self._search_one_crd_additional = False
        self._save_to_review_df = False
        self._num_searches_performed = 0
        self._total_found = 0
        self._num_found_contacts = 0

    def __init_list_metadata(self, frame):
        """
        Helper method which stores the list file's column names and determines if it's known, or not.

        Returns
        -------
            Nothing
        """
        self._headers = frame.columns.tolist()
        self._keep_cols = [c for c in self._headers if 'unknown' not in c.lower()]

    @staticmethod
    def _crd_formatter(_series):
        _series = _series.astype(str)
        _series = _series.fillna('').replace('nan', '').apply(lambda x: x.split('.')[0] if '.' in x else x)
        return _series

    def __data_preprocessing(self, frame):
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
        self._headers = frame.columns.tolist()
        return frame

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
        return list(set(joined_headers))

    def __create_meta_data(self, _vars, frame, search_two=False):
        """
        Helper method to determine how a merged list (3rd party & FS SFDC data) get's handled.

        Steps:
        ------
        1) Determine if this is the first, or second, set of searches against SFDC.
        2) If this is the second set of searches, then 'found contacts' are only records that have a ContactId
        3) If this is the first set of searches then:
            a) If a CRD search is passed to the 'create_meta_data' method:
                1a. 'found contacts' are records that have a ContactId merged with the original data
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
            # _vars.found = read_df(self._found_contact_path)
            finra_matched_to_sf = frame[frame['ContactId'] != '']
            self.log.info('\nMatched CRDs from FINRA to %s records in Salesforce' % len(finra_matched_to_sf))
            _vars.found['frame'] = _vars.found['frame'].append(finra_matched_to_sf, ignore_index=True, sort=False)

        else:
            if self._is_crd_check and 'CRD Provided by List' not in self._headers:
                _vars.found['frame'] = _vars.found['frame'].append(
                    frame[frame['ContactId'] != ''], ignore_index=True)

                if frame['CRDNumber'].count() == len(frame.index) and \
                        len(frame['CRDNumber'].nonzero()[0]) == len(frame.index):

                    frame.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
                    _vars.search_finra = False
                    if len(frame.index) != len(_vars.found['frame'].index):
                        self._search_one_crd_additional = True
                        self.log.info('CRD Info provided for all contacts. Will not search FINRA, but will '
                                      'perform remaining standard searches to maximize match rate.')
                        frame = frame[frame['ContactId'] == '']
                        # self._contacts_to_review = self._contacts_to_review.append(
                        #     _vars.list_df[_vars.list_df['ContactId'] == ''], ignore_index=True)
                        # self.log.info('CRD Info provided for all contacts. Will not search FINRA.')

                else:
                    frame = _vars.list_df[frame['ContactId'] == '']
                    frame.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
                self._headers = frame.columns.tolist()

            else:
                frame.fillna('', inplace=True)
                if "CRD Provided by List" in self._headers:
                    frame, _vars = self._identify_to_review_records(frame, _vars)
                    frame.rename(columns={'CRD Provided by List': 'CRDNumber'}, inplace=True)
                    _vars.found['frame'] = _vars.found['frame'].append(frame[frame['ContactId'] != ''],
                                                                       ignore_index=True)
                    frame = frame[frame['ContactId'] == '']
                    frame.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)

                else:
                    _vars.found['frame'] = _vars.found['frame'].append(frame[frame['CRDNumber'] != ''],
                                                                       ignore_index=True)
                    frame = frame[frame['CRDNumber'] == '']

            for r_field in self._return_fields:
                try:
                    del frame[r_field]
                except:
                    pass
        return _vars, frame

    def _identify_to_review_records(self, frame, _vars):
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
        frame['ToReview'] = 0
        frame['ToReview'] = frame.apply(
            lambda x: 1 if x['CRDNumber'] != '' and x['CRDNumber'] != x["CRD Provided by List"] else x[
                'ToReview'], axis=1)
        _vars.review['frame'] = _vars.review['frame'].append(frame[frame['ToReview'] == 1], ignore_index=True)
        frame = frame[frame['ToReview'] == 0]
        del frame['CRDNumber']
        del frame['ToReview']
        self.log.info('Identified %s contacts that need to be reviewed.' % len(_vars.review['frame'].index))
        return frame, _vars

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

    def __search_and_merge(self, _vars, frame, search_fields, search_two=False):
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
        if len(search_fields) > 1:
            self._return_fields = ['CRDNumber', 'AccountId', 'SourceChannel', 'ContactId', 'Needs Info Updated?',
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

                _vars, frame = self.__create_meta_data(_vars, frame, search_two=search_two)

                self._num_remaining = len(frame.index)

                self.__num_found(_vars.found)
                _vars.search_found[header] = self._num_searched_on - self._num_remaining

                self.log.info('Found %s on %s search.\n' % (_vars.search_found[header], header))
                self._headers = frame.columns.tolist()

        return _vars, frame

    def _crd_search(self, _vars, frame, search_field=['CRDNumber']):
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
                               'Needs Info Updated?', 'ContactId', 'BizDev Group']
        frame.fillna('', inplace=True)
        _vars, frame = self.__search_and_merge(_vars, frame, search_field)
        return _vars, frame

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
        _vars.update_state()
        self.log.info('Starting first Salesforce comparison on the %s list.' % _vars.list_type)
        frame = _vars.list_source['frame']
        self._SFDC_advisor_list = _vars.sfdc_target['frame']
        self._SFDC_advisor_list['CRDNumber'] = self._crd_formatter(self._SFDC_advisor_list['CRDNumber'])

        self.__init_list_metadata(frame)
        frame = self.__data_preprocessing(frame)

        if 'CRDNumber' in self._headers and not self._is_crd_check:
            self.log.info("Performing a CRD search, as 'CRDNumber' is present.")
            _vars, frame = self._crd_search(_vars, frame)
            if self._search_one_crd_additional:
                self.log.info("Performing additional searches as the CRD search didn't find all records successfully.")
                _vars, frame = self.__search_and_merge(_vars, frame, _vars.search_one_keys)

                frame.rename(columns={'CRD Provided by List': 'CRDNumber'}, inplace=True)
                _vars.create_df = frame[~is_null(frame['CRDNumber'])]
                frame = frame[is_null(frame['CRDNumber'])]

        else:
            self.log.info("Performing standard search, as 'CRDNumber' is not present.")
            _vars, frame = self.__search_and_merge(_vars, frame, _vars.search_one_keys)

        _vars.list_source['frame'] = frame
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
        _vars.update_state()
        frame = _vars.finra_found['frame']
        self.log.info('Starting second Salesforce comparison on the %s list.' % _vars.list_type)
        self.__init_list_metadata(frame)
        self._keep_cols = [c for c in frame.columns if not c.lower()[:7].__contains__('unknown')]

        frame = self.__data_preprocessing(frame)
        self.log.info('Searching against SFDC following FINRA/SEC searches.')
        _vars, frame = self.__search_and_merge(_vars, frame, search_fields=_vars.search_two_keys, search_two=True)
        _vars.finra_found['frame'] = frame
        return _vars
