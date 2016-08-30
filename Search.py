"""
Module 2:
    - Step following trainHeadersModelv1
    - Translation of 'SearchSFforAdvisors_FirstTime'
    - PrepFileforSearch
    - Searches by CRD, AMPF ID, Email, and LkupName
    - Shortens search code to 10 lines!

Change Log:
    - Did not include getNamesOfOpenWorkbooks()
    - Zip Code formatting
    - Full Name formatting
    - Accreditation's corner cases added
    - (5.11) Deeper searching added if CRD included, doesn't rule out other searches if CRD does not find Contact ID
"""

import pandas as pd
import numpy as np
import time
import os
from functions import splitname


def found_contact_path(path):
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_foundcontacts.xlsx'
    found_path = rootpath + fname
    return found_path


def review_contact_path(path):
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_review_contacts.xlsx'
    found_path = rootpath + fname
    return found_path


def sf_advlist():
    """

    :rtype: object
    """
    print "Please wait. Downloading SFDC list as today's file was not available."
    from sqlQuery import run
    run()


user = os.environ.get("USERNAME")
AdvListPath = 'T:/Shared/FS2 Business Operations/Search Program/Salesforce Data Files/SFDC Advisor List as of ' \
              + time.strftime("%m-%d-%y") + '.csv'
if os.path.exists(AdvListPath) == False:
    sf_advlist()


def df_column_preprocessing(df):
    count = 0
    for col in df.columns:
        if df[col].dtype not in ('int64', 'float64', 'object'):
            # print count, df[col].dtype, df[col]
            for cell in xrange(0, len(df[col])):
                df[cell][count] = df[cell][count].encode('utf-8', 'ignore')
        else:
            count += 1
    return df


def clean_comma_and_space(row):
    if ' ' in row:
        row.replace(' ', '')
    if ',' in row:
        row.replace(',', ', ')
    return row


def init_advisor_list():
    return pd.read_csv(AdvListPath, error_bad_lines=False, low_memory=False)


def read_list(path_to_load):
    return pd.read_excel(path, sheetname=0)


def name_preprocessing(headers, search_list):
    if "FullName" in headers:
        search_list.insert(0, "LastName", "")
        search_list.insert(0, "FirstName", "")
        for index, row in search_list.iterrows():
            if ',' in row["FullName"]:
                # search_list.loc[index,"FullName"]=clean_comma_and_space(row["FullName"])
                if row["FullName"].index(' ') < row["FullName"].index(','):
                    # A Space comes before the comma. Assume we are dealing with First Last, Accreditation orientation
                    row["FirstName"] = row["FullName"].split(' ')[0]
                    row["LastName"] = row["FullName"].split(' ')[1][:-1]
                else:  # Comma before space. Assume Last, First orientation
                    row["LastName"] = row["FullName"].split(',')[0]
                    row["FirstName"] = row["FullName"].split(' ')[1]  # Assumes space after ','

            else:  # Assume first last/middle last/suffix order
                names = row["FullName"].split()
                names_left = []
                names_to_remove = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", 'aams', 'aif', 'aifa', 'bcm', 'caia',
                                   'casl', 'ccps', 'cdfa', 'cea', 'cebs', 'ces', 'cfa', 'cfe', 'cfp', 'cfs', 'chfc',
                                   'chfcicap', 'chfebc', 'cic', 'cima', 'cis', 'cltc', 'clu', 'cpa', 'cpwa', 'crpc',
                                   'crps', 'csa', 'iar', 'jd', 'lutcf', 'mba', 'msa', 'msfp', 'pfs', 'phd', 'ppc']
                for name in names:
                    if name.lower() in names_to_remove:
                        continue
                    else:
                        names_left = names_left + [name]
                if len(names_left) == 3:
                    search_list.loc[index, "FirstName"] = names_left[0]
                    search_list.loc[index, "LastName"] = names_left[2]
                else:
                    search_list.loc[index, "FirstName"] = names_left[0]
                    search_list.loc[index, "LastName"] = names_left[1]
    return search_list


def lkup_name_address_processing(headers, search_list):
    # If we have the information to make LkupName, do so
    if "MailingPostalCode" in headers and "MailingState" in headers:

        # Format Zip codes
        search_list['MailingPostalCode'] = search_list['MailingPostalCode'].astype(str)
        for index, row in search_list.iterrows():
            search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"].split('-')[0]
            if len(row["MailingPostalCode"]) == 9:
                search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:5]
            elif len(row["MailingPostalCode"]) == 8:
                search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:4]

        if np.mean(search_list['MailingState'].str.len()) > 2:
            import us_state_abbr
            print 'MailingState column needs to be transformed.'
            for index, row in Campaign_list.iterrows():
                try:
                    state = us.states.lookup(search_list.loc[index, "MailingState"])
                    search_list.loc[index, "MailingState"] = str(state.abbr)
                except:
                    pass

        # Format name as necessary
        # Split FullName if given, cleanup first/last name, create lkup name
        if "FirstName" in headers and "LastName" in headers:
            search_list["LkupName"] = search_list["FirstName"].str[:3] + \
                                      search_list["LastName"] + search_list["Account"].str[:10] + \
                                      search_list["MailingState"] + search_list["MailingPostalCode"]

        else:
            print "Advisor name or account information missing"
    return search_list


class Search():
    def __init__(self):
        self._SFDC_advisor_list = init_advisor_list()
        self._headers = self._search_list.columns.values
        self._keep_cols = [c for c in self._headers if c.lower() != 'unknown']
        self._search_fields = ['AMPFMBRID', 'Email', 'LkupName']
        self._return_fields = ['AccountId', 'SourceChannel', 'Needs Info Updated?',
                               'ContactID', 'CRDNumber', 'BizDev Group']
        self._found_contacts = pd.DataFrame()
        self._contacts_to_review = pd.DataFrame()
        self._to_finra = True
        self._num_searches_performed = 0

    def __data_preprocessing(self, additional=False):
        search_list = self._search_list
        search_list = search_list[self._keep_cols]
        search_list = search_list.fillna('')
        if additional:
            search_list = name_preprocessing(self._headers, search_list)
            search_list = lkup_name_address_processing(self._headers, search_list)
        self._headers = search_list.columns.values
        self._search_list = search_list
        return self

    def __check_list_type(self):
        if self._list_type != 'BizDev Group':
            del self._return_fields[-1]
        return self

    def __join_headers(self, header):
        joined_headers = header
        for ret_field in self._return_fields:
            joined_headers.append(ret_field)
        return joined_headers

    def __create_meta_data(self, headers=None, search_two=False):
        if not search_two:
            if 'CRD Provided by List' in headers:
                search_list = self._search_list
                to_review = self._contacts_to_review
                to_review = to_review.append(search_list[search_list['ContactID'] != ''], ignore_index=True)
                search_list = search_list[search_list['ContactID'] == '']
                self._search_list = search_list
                self._contacts_to_review = to_review
            else:
                found_contacts = self._found_contacts
                search_list = self._search_list
                found_contacts = found_contacts.append(search_list[search_list['CRDNumber'] != ''], ignore_index=True)
                search_list = search_list[search_list['CRDNumber'] == '']
                self._search_list = search_list
                self._contacts_to_review = found_contacts
        else:
            self._found_contacts = read_list(self._found_contact_path)
            self._found_contacts.append(self._search_list, ignore_index=True)
        return self

    def __num_found(self, found_df):
        self._num_found_contacts = len(found_df)
        return self

    def __search_and_merge(self, search_fields, search_two=False):
        for header in search_fields:
            for header in self._headers:
                self._num_searches_performed += 1
                print 'Performing search #%s on %s' % (self._num_searches_performed, header)
                self._joined_headers = self.__join_headers(header)
                self._headers_and_ids = self._SFDC_advisor_list[joined_headers]
                self._search_list = self._search_list.merge(self._headers_and_ids, how='left', on='header')
                self._search_list = self._search_list.fillna('')
                self._num_searched_on = len(self._search_list)
                self.__create_meta_data(self._headers)
                self._num_remaining = len(self._search_list)
                if not search_two:
                    print 'Found %s on %s search.' % (self.__num_found(self._found_contacts), header)
                else:
                    print 'Found %s on %s search.' % (self.__num_found(self._found_contacts['ContactID'].nonzero()[0]),
                                                      header)
                for ret_field in self._return_fields:
                    del self._search_list[ret_field]

        return self

    def _crd_search(self, list_df, sfdc_df, n, search_field=['CRDNumber']):
        self._search_list.fillna('')
        self.__search_and_merge(search_field)
        if self._search_list.count() == len(self._search_list) and \
                        + len(self._search_list['CRDNumber'].nonzero()[0]) == len(self._search_list):
            self._to_finra = False
        self._search_list.rename(columns={'CRDNumber': 'CRD Provided by List'}, inplace=True)
        return self

    def perform_search_one(self, searching_list_path, list_type):
        self._search_list = read_list(searching_list_path)
        self._list_type = list_type
        self.__check_list_type()
        self.__data_preprocessing(additional=True)

        if 'CRDNumber' in self._headers:
            self._crd_search(self._search_list, self._SFDC_advisor_list,
                             self._num_searches_performed, self._list_type)

        if self._to_finra == False:
            print('CRD Info provided for all contacts. Will not search FINRA.')

        else:
            self.__search_and_merge(self._search_fields)

        if 'CRD Provided by List' in self._headers and self._to_finra == False:
            self._contacts_to_review = self._contacts_to_review.append(self._search_list, ignore_index=True)
            self._review_path = review_contact_path(searching_list_path)
            self._contacts_to_review.to_excel(self._review_path, index=False)
        self._found_contact_path = found_contact_path(searching_list_path)
        self._found_contacts.to_excel(self._found_contact_path, index=False)
        self._search_list.to_excel(searching_list_path, index=False)

        ret_item = {'Next Step': 'FINRA Search',
                    'Found Path': self._found_contact_path,
                    'SFDC_Found': self._num_found_contacts,
                    'FINRA?': self._to_finra,
                    'Review Path': self._review_path}
        return ret_item

    def perform_search_two(self, searching_list_path, found_path, list_type):
        self._search_fields = ['CRDNumber']
        self._return_fields = ['AccountId', 'SourceChannel', 'ContactID',
                               'Needs Info Updated?', 'BizDev Group']
        self._found_contact_path = read_list(found_path)

        self._search_list = read_list(searching_list_path)
        self._keep_cols = [c for c in self._search_list.columns if c.lower()[:7] != 'unknown']
        self._list_type = list_type

        self.__check_list_type()
        self.__data_preprocessing()
        print '\nStep 7:\nSearching against SFDC following FINRA/SEC searches.'
        self.__search_and_merge(self._search_fields, search_two=True)

        self._found_contacts.to_excel(found_path, index=False)
        self._search_list.to_excel(searching_list_path, index=False)

        ret_item = {'Next Step': 'Upload Prep',
                    'Found in SFDC Search #2': self._num_found_contacts}
        return ret_item


def searchsec(path, found_path):
    '''
    Following the 'to-be-searched' list that had already be searched against
    SFDC, and attempted FINRA scraping, the remaining names that could not be
    scrapped are searched against the SEC database for CRD scrapping.
    database

    After the scrapping, we re-search the SFDC database to attempt to find any
    additional contacts that were missed during the 'searchone' function.
    '''

    import datetime
    today = datetime.datetime.strftime(datetime.datetime.now(), '%m_%d_%Y')
    SECpath = 'T:/Shared/FS2 Business Operations/Python Search Program/SEC_Data/Individuals/processed_data/' + today + '/'
    if os.path.exists(SECpath) == False:
        print "Skipping SEC Search. Today's files could not be found in the listed directory."
        ret_item = {'Next Step': 'SFDC Search #2', 'SEC_Found': 0}
        return ret_item

    print '\nStep 6:\nSearching against SEC Data.'
    Campaign_list = pd.read_excel(path, sheetname=0)
    headers = Campaign_list.columns.values
    # test_SECpath='C:/Users/rschools/Downloads/SEC_Data/processed_data/03_30_2016/'
    SECfiles = os.listdir(SECpath)
    found = 0
    for sec in SECfiles:

        sec_df = pd.read_csv(SECpath + sec)
        sec_df.rename(columns={'indvlPK': 'CRDNumber'}, inplace=True)

        searchfields = ['LkupName']
        found_contacts = pd.DataFrame()

        n = 0
        for header in searchfields:
            if header in headers:
                n += 1

                print 'Performing search #%s on %s for %s sec file' % (n, header, sec)
                headerandIDs = sec_df[[header, 'CRDNumber']]
                Campaign_list = Campaign_list.merge(headerandIDs, how='left', on=header)
                Campaign_list = Campaign_list.fillna('')
                found_contacts = found_contacts.append(Campaign_list[Campaign_list['CRDNumber'] != ''],
                                                       ignore_index=True)
                Campaign_list = Campaign_list[Campaign_list.CRDNumber == '']
                if n > 1:
                    found = (len(found_contacts) - found)
                else:
                    found = len(found_contacts)
                print 'Found %s on %s search.' % (found, header)
                del Campaign_list['CRDNumber']

    df = pd.read_excel(found_path, sheetname=0)
    df = df.append(found_contacts)
    df.to_excel(found_path, index=False)
    Campaign_list.to_excel(path, index=False)
    ret_item = {'Next Step': 'SFDC Search #2', 'SEC_Found': found}
    return ret_item

##test_nocrd='C:/Users/rschools/Dropbox/Python Search Program/New Lists/Chicago Pre Attendee_nocrd.xlsx'
##test_found='C:/Users/rschools/Dropbox/Python Search Program/New Lists/Chicago Pre Attendee_foundcontacts.xlsx'
##
##test_search1='C:/Users/rschools/Dropbox/Python Search Program/New Lists/AMPF Update Rep List_ALPTest/AMPF Update Rep List_ALPTest.xlsx'
##if __name__=="__main__":
##    print searchsec('xyz', 'pdq')
##    searchone(test_search1, listType='Account')
