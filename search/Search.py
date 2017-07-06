import os
import time
import numpy as np
from legacy.get_sf_adv_list import run
from utility.gen_helper import create_path_name, today
from utility.pandas_helper import read_df, save_df, make_df, is_null

_AdvListPath = 'T:/Shared/FS2 Business Operations/Search Program/Salesforce Data Files/SFDC Advisor List as of ' \
               + time.strftime("%m-%d-%y") + '.csv'


def sf_advlist():
    print("Please wait. Downloading SFDC list, as today's file was not available.")
    run()


if not os.path.exists(_AdvListPath):
    sf_advlist()


class Search:
    def __init__(self, log=None):
        """
        declare instance variables for the search class and child methods.
        """
        self.log = log
        self._today = today
        self._SFDC_advisor_list = read_df(_AdvListPath)
        self.__preprocess_sfdc_list()
        self._search_fields = ['AMPFMBRID', 'Email', 'LkupName']
        self._return_fields = ['CRDNumber', 'AccountId', 'SourceChannel', 'ContactID', 'Needs Info Updated?',
                               'BizDev Group']
        self._found_contacts = make_df()
        self._contacts_to_review = make_df()
        self._to_create = make_df()
        self._keep_cols = []
        self._to_finra = True
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
        self._sec_path = 'T:/Shared/FS2 Business Operations/Python Search Program/SEC_Data/' \
                         'Individuals/processed_data/' + self._today + '/'

    def __init_list_metadata(self):
        """
        helper method which stores the list file's column names and determines if it's known, or not.

        :return: n/a
        """
        self._headers = self._search_list.columns.values
        self._keep_cols = [c for c in self._headers if 'unknown' not in c.lower()]

    def __preprocess_sfdc_list(self):
        """
        helper method that pre-preprocesses our source SalesForce contact file.
        1) identify and keep only unique records (rows)
        2) convert the CRDNumber column to string type
        :return: n/a
        """
        _, i = np.unique(self._SFDC_advisor_list.columns, return_index=True)
        self._SFDC_advisor_list = self._SFDC_advisor_list.iloc[:, i]
        self._SFDC_advisor_list['CRDNumber'].astype(str)

    def __data_preprocessing(self, additional=False):
        """
        helper method that attempts to clean the 3rd party list file.

        1) slice and keep only the 'known' columns
        2) fill NaN/NULL (blank) values and drop all rows that don't have at least 3 full columns
        3) if Full Name is a column, attempt to split into First and Last name columns to improve match-rates
        4) if First Name, Last Name, Account Name, State, and Zip are present attempt to make LkupName

        :param additional: boolean, default=False
        :return: n/a
        """
        self._search_list = self._search_list[self._keep_cols]
        self._search_list.fillna('', inplace=True)
        if len(self._search_list.columns) > 3:
            self._search_list.dropna(axis=0, thresh=3, inplace=True)
        if additional:
            self._search_list = self._name_preprocessing(self._headers, self._search_list)
            self._search_list = self._lkup_name_address_processing(self._headers, self._search_list)
        self._headers = self._search_list.columns.values

    def __check_list_type(self):
        """
        helper method to subset the fields returned upon merging 3rd party list with SF, based on the source object.

        :return: n/a
        """
        if self._list_type != 'BizDev Group':
            del self._return_fields[-1]

    def _df_column_preprocessing(self, df):
        """
        helper method to encode columns in a data frame to 'utf-8' based on the column's data type

        :param df: data frame object
        :return: transformed data frame
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
        helper method to combine merge key (header) and the metadata we want from SFDC to associate with
        an individual record (row) from a 3rd party list.

        :param header: merge key, i.e. a column we will merge on
        :return: key and joined headers (ex. [CRDNumber, ContactId, AccountId, SourceChannel, etc.])
        """
        joined_headers = [header]
        [joined_headers.append(rf) for rf in self._return_fields]
        return list(joined_headers)

    def __create_meta_data(self, headers=None, search_two=False):
        """
        helper method to determine how a merged list (3rd party & FS SFDC data) get's handled.
        
        1) determine if this is the first, or second, set of searches against SFDC.
        2) if this is the second set of searches, then 'found contacts' are only records that have a ContactID
        3) if this is the first set of searches then:
            a) if a CRD search is passed to the 'create_meta_data' method:
                1a. 'found contacts' are records that have a ContactID merged with the original data
                2a. if CRD's are provided for all records, set 'to_finra' to False and rename the CRDNumber column
                3a. if the length of the search list and found contact list are not the same, we need to 
                    perform additional searches to attempt to identify additional matches & duplicate records.
            
        :param headers: 
        :param search_two: 
        :return: 
        """
        # may need to try and clean this method up, it's a bit confusing and messy.
        if search_two:
            self._found_contacts = read_df(self._found_contact_path)
            finra_matched_to_sf = self._search_list[self._search_list['ContactID'] != '']
            self.log.info('\nMatched CRDs from FINRA to %s records in Salesforce' % len(finra_matched_to_sf))
            self._found_contacts = self._found_contacts.append(finra_matched_to_sf, ignore_index=True)

        else:
            if self._is_crd_check and 'CRD Provided by List' not in self._headers:
                self._found_contacts = self._found_contacts.append(
                    self._search_list[self._search_list['ContactID'] != ''], ignore_index=True)

                if self._search_list['CRDNumber'].count() == len(self._search_list.index) and \
                                len(self._search_list['CRDNumber'].nonzero()[0]) == len(self._search_list.index):

                    self._search_list.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
                    self._to_finra = False
                    if len(self._search_list.index) != len(self._found_contacts.index):
                        self._search_one_crd_additional = True
                        self.log.info('CRD Info provided for all contacts. Will not search FINRA, but will '
                                      'perform remaining standard searches to maximized match rate.')
                        self._search_list = self._search_list[self._search_list['ContactID'] == '']
                        # self._contacts_to_review = self._contacts_to_review.append(
                        #     self._search_list[self._search_list['ContactID'] == ''], ignore_index=True)
                        # self.log.info('CRD Info provided for all contacts. Will not search FINRA.')

                else:
                    self._search_list = self._search_list[self._search_list['ContactID'] == '']
                    self._search_list.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
                self._headers = self._search_list.columns.values

            else:
                self._search_list.fillna('', inplace=True)
                if "CRD Provided by List" in self._headers:
                    self._identify_to_review_records()
                    self._search_list.rename(columns={'CRD Provided by List': 'CRDNumber'}, inplace=True)
                    self._found_contact = self._found_contacts.append(
                        self._search_list[self._search_list['ContactID'] != ''],
                        ignore_index=True)
                    self._search_list = self._search_list[self._search_list['ContactID'] == '']
                    self._search_list.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)

                else:
                    self._found_contact = self._found_contacts.append(
                        self._search_list[self._search_list['CRDNumber'] != ''],
                        ignore_index=True)
                    self._search_list = self._search_list[self._search_list['CRDNumber'] == '']

            for r_field in self._return_fields:
                try:
                    del self._search_list[r_field]
                except:
                    pass

    def _identify_to_review_records(self):
        """
        a method that's used to help identify records that need to be manually reviewed
        
        1) flag a record as needing review if:
            a) a SFDC CRDNumber is not null doesn't equal the CRD Provided by List Number
        :return: 
        """
        self._search_list['ToReview'] = 0
        self._search_list['ToReview'] = self._search_list.apply(
            lambda x: 1 if x['CRDNumber'] != '' and x['CRDNumber'] != x["CRD Provided by List"] else x[
                'ToReview'], axis=1)
        print(self._search_list.head())
        self._contacts_to_review = self._contacts_to_review.append(
            self._search_list[self._search_list['ToReview'] == 1], ignore_index=True)
        self._search_list = self._search_list[self._search_list['ToReview'] == 0]
        del self._search_list['CRDNumber']
        del self._search_list['ToReview']
        self._save_to_review_df = True
        print(self._search_list.head())
        self.log.info('Identified %s contacts that need to be reviewed.' % len(self._contacts_to_review.index))

    def __num_found(self, found_df):
        """
        records the number of records found during the search process
    
        :param found_df: data frame
        :return: n/a
        """
        self._num_found_contacts = len(found_df)
        self._total_found += self._num_found_contacts

    def __search_and_merge(self, search_fields, search_two=False):
        """
        helper method that actually performs the merging of data from 3rd party and SF list files.
        1) for each search field, determine if it's present in the 3rd party file's column names
        2) create a sliced data frame of SF data to include only columns we need in 'n'th search (via join_headers)
        3) merge data from 3rd party and SF subsetted data frame, merging on the search header
        4) submit the merged 3rd party list to the create_metadata method to determine how the list
            should be further sliced for subsequent processing, or if all records were found.
    
        :param search_fields: list of columns to search (pandas merge) on
        :param search_two: boolean, default=False
        :return: n/a
        """
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

                self._search_list = self._search_list.merge(self._headers_and_ids, how='left', on=header)
                self._search_list.fillna('', inplace=True)
                self._num_searched_on = len(self._search_list)
                self.__create_meta_data(self._headers, search_two=search_two)
                self._num_remaining = len(self._search_list)

                self.__num_found(self._found_contacts)

                self.log.info('Found %s on %s search.\n' % (self._num_found_contacts, header))
                self._headers = self._search_list.columns.values

    def _crd_search(self, search_field=['CRDNumber']):
        """
        helper method to help properly guide the search process when matching on CRDNumbers
    
        1) set the fields that will be returned to the 3rd party list from the SFDC file, and fill blank values
        2) merge the 3rd party list and SFDC file, leveraging the __search_and_merge method.
    
        :param search_field:
        :return:
        """
        self._is_crd_check = True
        self._return_fields = ['AccountId', 'SourceChannel',
                               'Needs Info Updated?', 'ContactID', 'BizDev Group']
        self._search_list.fillna('', inplace=True)
        self.__search_and_merge(search_field)
        return self

    def _lkup_name_address_processing(self, headers, search_list):
        """
        helper method to create the LkupName search field, if the necessary columns are present, and pre-process them.
    
        1) check if PostalCode and State are available in the data frame, and convert the data types to strings
        2) loop through each row, and attempt to clean the Postal code.
        3) attempt to clean the State column, if the name (rather than abbr.) is provided. leverage us.states.lookup
        4) check if FirstName and LastName are present
            a) if all columns are present combine first 3 chars of First Name, Last Name, Account, State, and Postal
            b) ex. RicSchools FS Investm PA 19112
    
        :param headers: list of column headers of the data frame
        :param search_list: data frame value
        :return: transformed data frame
        """
        if "MailingPostalCode" in headers and "MailingState" in headers:
            import us
            #import uszipcode
            #zs = uszipcode.ZipcodeSearchEngine()

            search_list['MailingPostalCode'] = search_list['MailingPostalCode'].astype(str)
            for index, row in search_list.iterrows():
                search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"].split('-')[0]
                if len(row["MailingPostalCode"]) == 9:
                    search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:5]
                elif len(row["MailingPostalCode"]) == 8:
                    search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:4]

            if np.mean(search_list['MailingState'].str.len()) > 2:
                import us
                self.log.info('MailingState column needs to be transformed.')
                for index, row in search_list.iterrows():
                    try:
                        state = us.states.lookup(search_list.loc[index, "MailingState"])
                        search_list.loc[index, "MailingState"] = str(state.abbr)
                    except:
                        pass

            if "FirstName" in headers and "LastName" in headers:
                search_list["FirstName"] = map(lambda x: x.title(), search_list["FirstName"])
                search_list["LastName"] = map(lambda x: x.title(), search_list["LastName"])
                search_list["LkupName"] = search_list["FirstName"].str[:3] + search_list["LastName"] + search_list["Account"].str[:10] + search_list["MailingState"] + search_list["MailingPostalCode"].str[:-2]

            else:
                self.log.info("Advisor name or account information missing")
        return search_list

    def _clean_comma_and_space(self, row):
        """
        helper method to remove spaces and commas from a row of data.
    
        :param row: data frame row of data
        :return: transformed row
        """
        if ' ' in row:
            row.replace(' ', '')
        if ',' in row:
            row.replace(',', ', ')
        return row

    def _name_preprocessing(self, headers, search_list):
        """
        helper method to split and clean the FullName column of the 3rd party data frame.
    
        1) if FullName is present, create a column for First and Last Name.
        2) iterate through the data frame and if a comma is present in the Full Name, check if:
            a) a space preceeds a comma. if so, assume the 1st element of the split FullName is the First Name
                and the 2nd element is the Last Name.
            b) a comma preceeds a space. if so, assume the inverse of the previous statement.
        3) if no comma is present, assume First Last / (suffix or middle) - splitting the FullName on spaces (' ')
        4) attempt to remove potential suffixes (which may include .jr, iii, cfa, etc.)
        5) finally, attempt to appropriately assign the First and Last Name fields to the appropriate columns.
    
    
        :param headers: columns of the data frame
        :param search_list: data frame
        :return: transformed data frame
        """
        names_to_remove = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", 'aams', 'aif', 'aifa', 'bcm', 'caia',
                           'casl', 'ccps', 'cdfa', 'cea', 'cebs', 'ces', 'cfa', 'cfe', 'cfp', 'cfs', 'chfc',
                           'chfcicap', 'chfebc', 'cic', 'cima', 'cis', 'cltc', 'clu', 'cpa', 'cpwa', 'crpc',
                           'crps', 'csa', 'iar', 'jd', 'lutcf', 'mba', 'msa', 'msfp', 'pfs', 'phd', 'ppc']

        if "FullName" in headers:
            search_list.insert(0, "LastName", "")
            search_list.insert(0, "FirstName", "")
            for index, row in search_list.iterrows():
                if ',' in row["FullName"]:
                    if row["FullName"].index(' ') < row["FullName"].index(','):
                        row["FirstName"] = row["FullName"].split(' ')[0]
                        row["LastName"] = ' '.join(row["FullName"].split(' ')[1:])
                    else:
                        row["LastName"] = row["FullName"].split(',')[0]
                        row["FirstName"] = row["FullName"].split(' ')[1]
                else:
                    full_name_list = row["FullName"].split()
                    for name in full_name_list:
                        if name.lower() in names_to_remove:
                            full_name_list.pop(full_name_list.index(name))
                    if len(full_name_list) == 3:
                        search_list.loc[index, "FirstName"] = full_name_list[0]
                        search_list.loc[index, "LastName"] = full_name_list[2]
                    else:
                        search_list.loc[index, "FirstName"] = full_name_list[0]
                        search_list.loc[index, "LastName"] = full_name_list[1]
        return search_list

    def perform_search_one(self, searching_list_path, list_type):
        self.log.info('Implementing search_one method on the %s list. Search 1 pre-processing begins.' % list_type)
        self._search_list = read_df(searching_list_path)
        self.__init_list_metadata()
        self._list_type = list_type
        self.__check_list_type()
        self.__data_preprocessing(additional=True)
        self._found_contact_path = create_path_name(path=searching_list_path, new_name='_foundcontacts')
        self._review_contact_path = create_path_name(path=searching_list_path, new_name='_review_contacts')
        self._to_create_path = create_path_name(path=searching_list_path, new_name='to_create')

        if 'CRDNumber' in self._headers and not self._is_crd_check:
            self.log.info("Performing a CRD search, as 'CRDNumber' is present.")
            self._crd_search()
            if self._search_one_crd_additional:
                self.log.info("Performing additional searches as the CRD search didn't find all records successfully.")
                self.__search_and_merge(self._search_fields)

                self._search_list.rename(columns={'CRD Provided by List': 'CRDNumber'}, inplace=True)
                self._to_create = self._search_list[~is_null(self._search_list['CRDNumber'])]
                self._search_list = self._search_list[is_null(self._search_list['CRDNumber'])]

        else:
            self.log.info("Performing standard search, as 'CRDNumber' is not present.")
            self.__search_and_merge(self._search_fields)

        if self._save_to_review_df:
            save_df(df=self._contacts_to_review, path=self._review_contact_path)

        if len(self._to_create.index) > 0:
            save_df(df=self._to_create, path=self._to_create_path)

        save_df(df=self._found_contacts, path=self._found_contact_path)
        save_df(df=self._search_list, path=searching_list_path)

        ret_item = {'Next Step': 'FINRA Search',
                    'Found Path': self._found_contact_path,
                    'SFDC_Found': self._num_found_contacts,
                    'FINRA?': self._to_finra,
                    'Review Path': self._review_contact_path,
                    'to_create_path': self._to_create_path}
        return ret_item

    def perform_search_two(self, searching_list_path, found_path, list_type):
        self.log.info('Implementing search_two method on the %s list. Search 2 pre-processing begins.' % list_type)
        self._search_fields = ['CRDNumber']
        self._return_fields = ['AccountId', 'SourceChannel', 'ContactID',
                               'Needs Info Updated?', 'BizDev Group']
        self._found_contacts = read_df(found_path)

        self._search_list = read_df(searching_list_path)
        self.__init_list_metadata()
        self._keep_cols = [c for c in self._search_list.columns if not c.lower()[:7].__contains__('unknown')]
        self._list_type = list_type

        self.__check_list_type()
        self.__data_preprocessing()
        self.log.info('Searching against SFDC following FINRA/SEC searches.')
        self.__search_and_merge(search_fields=self._search_fields, search_two=True)
        save_df(df=self._found_contacts, path=found_path)
        save_df(df=self._search_list, path=searching_list_path)

        ret_item = {'Next Step': 'Upload Prep',
                    'Found in SFDC Search #2': self._num_found_contacts}
        return ret_item

    def perform_sec_search(self, searching_list_path, found_path):
        if not os.path.exists(self._sec_path):
            self.log.info("Skipping SEC Search. Today's files could not be found in the listed directory.")
            ret_item = {'Next Step': 'SFDC Search #2', 'SEC_Found': 0}
            return ret_item

        self.log.info('Searching against SEC Data.')
        self._search_list = read_df(searching_list_path)
        self.__init_list_metadata()
        self._sec_files = os.listdir(self._sec_path)
        self._search_fields = ['LkupName']

        for sec in self._sec_files:
            self._sec_df = read_df(sec)
            self._sec_df.rename(columns={'indvlPK': 'CRDNumber'}, inplace=True)
            self.__search_and_merge(self._search_fields)

        save_df(df=self._found_contacts, path=found_path)
        save_df(df=self._search_list, path=searching_list_path)

        ret_item = {'Next Step': 'SFDC Search #2', 'SEC_Found': self._num_found_contacts}
        return ret_item
