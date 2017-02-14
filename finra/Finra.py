import os
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from utility.finra_helpers import strip_unicode_chars
from utility.gen_helpers import create_path_name
from utility.pandas_helper import read_df, save_df
from utility.progress_bar import myprogressbar


class FinraScraping:
    def __init__(self):
        self._chrome_driver = "C:/Python27/selenium/Chrome/chromedriver"
        os.environ["webdriver.chrome.driver"] = self._chrome_driver
        self._finra_site = 'http://www.finra.org/'
        self._elements = ['finra_pc_search_box', 's4_item-field', 's4_suggestion']
        self._xpath = None
        self._attempted_search_count = 0
        self._attempts = 0
        self._found = 0
        self._refresh_count = 0
        self._no_crd = pd.DataFrame()
        self._finra_ambiguity = pd.DataFrame()
        self._search_list = None
        self._found_df = None
        self._type = None
        self._search_data = None
        self._return_name = False
        self._finra_sec_found_path = ''
        self._no_crd_fname = ''
        self._uncertain_path = ''
        self._to_be_searched = []
        self._to_be_added = []
        self._num_suggestions = []
        self._licenses = []
        self._address = []
        self._crd_enabled = False
        self._license_enabled = False

    def __init_selenium_components(self):
        '''
        private method.

        initiates the components needed for selenium to funciton.
        :return: self
        '''
        self._sel = webdriver.Chrome(self._chrome_driver)
        self._wait = WebDriverWait(self._sel, 1)
        return self

    def __create_finra_search_output_paths(self, path):
        '''
        private method.

        creates the relevant output file names where processed
        lists that have been search in finra will be saved to
        :param path: string file path
        :return: self
        '''
        self._finra_sec_found_path = create_path_name(path=path, new_name='_finrasec_found')
        self._no_crd_fname = create_path_name(path, new_name='_nocrd')
        self._uncertain_path = create_path_name(path, new_name='_FINRA_ambiguous')
        return self

    def __data_preparations(self):
        '''
        private method.

        creates what will be searched in finra during list processing to find
        advisor CRD numbers.
        :return: list of all items to_be_searched
        '''
        self._search_list['FirstName'].apply(strip_unicode_chars)
        self._search_list['LastName'].apply(strip_unicode_chars)
        self._search_list['Account'].apply(strip_unicode_chars)
        for index, row in self._search_list.iterrows():
            try:
                search_name = row['FirstName'] + ' ' + row['LastName'] + ' ' + row['Account']
            except ValueError:
                search_name = 'Error converting row %s to string' % index
            self._to_be_searched.append([search_name])

    def __refreshing(self):
        '''
        private method for refreshing the selenium web browser
        :return: n/a
        '''
        self._sel.refresh()
        self._refresh_count += 1
        print('refreshing...%s' % self._refresh_count)

    def __close_selenium_components(self):
        '''
        private method to close and quit selenium
        :return: updated self
        '''
        self._sel.close(), self._sel.quit()
        return self

    def crd_check(self, path=None):
        '''
        public method.

        utilizes all of the private methods to actually perform the CRD search
        :param path: string file path -- required
        :param url: url to FINRA site -- optional
        :return: dictionary of stats and next steps
        '''
        self.__init_crd_metadata(path=path)
        self._sel.get(self._finra_site)
        print('\nAttempting to get CRDs from FINRA for %s names.' % len(self._to_be_searched))

        self.__crd_only_search_functionality()
        print('\nConfidently found %s CRD numbers from FINRA search.' % self._found)

        self.__data_output_prep()

        ret_item = {'Next Step': 'Search SEC',
                    'No CRD': self._no_crd_fname,
                    'FINRA_SEC Found': self._finra_sec_found_path,
                    'FINRA_Found': self._found,
                    'FINRA Ambiguous': self._uncertain_path}
        return ret_item

    def __init_crd_metadata(self, path=None):
        """
        private method.

        initiates the metadata needed for list processing.

        :param path: file path string - required.
        :param url: url to finra search site
        :return: updated self.
        """
        self.__init_selenium_components()

        if path is not None:
            self.__create_finra_search_output_paths(path)
            self._search_list = read_df(path)
            self.__data_preparations()
        return self

    def __crd_only_search_functionality(self):
        '''
        private method.

        is the actual guts of the CRD only search.
        :param elements: html elements to look for
        :return: updated self, has all finra searched meta data
        '''
        while self._attempted_search_count < len(self._to_be_searched):
            myprogressbar(self._attempted_search_count + 1, len(self._to_be_searched), message='CRD progress:')
            try:
                page_source = self._sel.page_source
                if self._elements[0] in page_source:
                    search_bar = self._sel.find_element_by_id(self._elements[0])
                    search_bar.send_keys(self._to_be_searched[self._attempted_search_count])
                    try:
                        code = self._wait.until(ec.visibility_of_element_located((By.CLASS_NAME,
                                                                                  self._elements[1])))
                        s_text = code.text.split()
                        suggestion_code = self._sel.page_source
                        choices = (len(suggestion_code.split(self._elements[2])) - 1)

                        if choices == 0:
                            self._to_be_added += ["CRD Not Found"]
                            self._attempted_search_count += 1
                            self._num_suggestions += [0]

                        elif choices > 1:
                            self._to_be_added += ["Multiple CRDs Present"]
                            self._attempted_search_count += 1
                            self._num_suggestions += [choices]

                        else:
                            crd_text = s_text.index("(CRD#") + 1
                            crd = s_text[crd_text][:-1]
                            self._to_be_added += [crd]
                            self._found += 1
                            self._attempted_search_count += 1
                            self._num_suggestions += [choices]

                    except:
                        self._to_be_added += ["CRD Not Found"]
                        self._attempted_search_count += 1
                        self._num_suggestions += [0]

                    search_bar.clear()
                else:
                    self.__refreshing()
            except:
                self.__refreshing()
        self.__close_selenium_components()
        return self

    def __save_outputs(self):
        '''
        private method.

        saves the files that were created by the finra search program
        :return: updated self
        '''
        save_df(df=self._no_crd, path=self._no_crd_fname)
        save_df(df=self._finra_ambiguity, path=self._uncertain_path)
        save_df(df=self._found_df, path=self._finra_sec_found_path)
        return self

    def __data_output_prep(self):
        '''
        private method.

        inserts the data / metadata from the FINRA search into the excel data file.
        :return: updated self
        '''
        self._search_list.insert(len(self._search_list.columns),
                                 'CRDNumber', self._to_be_added)
        self._search_list.insert(len(self._search_list.columns),
                                 'NumSuggestions', self._num_suggestions)
        self._no_crd = self._search_list[self._search_list['CRDNumber'] == 'CRD Not Found']
        self._finra_ambiguity = self._search_list[self._search_list['CRDNumber'] == 'Multiple CRDs Present']
        self._found_df = self._search_list[(self._search_list['CRDNumber'] != 'CRD Not Found') & (
            self._search_list['CRDNumber'] != 'Multiple CRDs Present')]

        del self._no_crd['CRDNumber']
        del self._search_list['NumSuggestions']
        del self._no_crd['NumSuggestions']
        del self._found_df['NumSuggestions']

        self.__save_outputs()
        return self

    def license_check(self, path):
        '''
        public method.

        utilizes all of the private methods to actually perform the license search
        :param path: string file name -- required
        :return: dicitonary - next step for list program
        '''
        self.__init_license_metadata(path)
        print('Pulling licenses from FINRA for %s advisors.' % (
            len(self._search_list[self._search_list['CRDNumber'].notnull()].index)))

        self.__license_finra_search()
        self.__save_license_output(path)
        return {'BDG Finra Scrape': 'Success'}

    def __init_license_metadata(self, path):
        '''
        private method.

        creates the necessary information that will be utilized by the license search method.
        :param path: file path name to excel file that will be searched.
        :return: updated self
        '''
        self._url = 'https://brokercheck.finra.org/individual/summary/'
        # self._elements = ['md-body-1 ng-binding flex-gt-xs-80']
        self._xpath = "//*[@class='md-body-1 ng-binding flex-gt-xs-80']"
        self._search_list = read_df(path)
        self._search_list['Licenses'] = ''
        self.__init_selenium_components()
        return self

    def __clean_licenses(self):
        '''
        private method.

        cleans the FINRA scraped licenses so that format is SFDC compatible.
        :return: updated self
        '''
        self._search_list.ix[self._attempted_search_count, 'Licenses'] = ';'.join(self._licenses)
        self._attempted_search_count += 1
        del self._licenses
        return self

    def __save_license_output(self, path):
        '''
        private method.

        saves the output of the FINRA license search
        :param path: file path name
        :return: n/a
        '''
        save_df(df=self._search_list, path=path)

    def __license_finra_search(self):
        '''
        private method.

        actual guts of the FINRA license search.
        :return: n/a
        '''
        element = self._xpath
        while self._attempted_search_count < len(self._search_list['CRDNumber']):
            myprogressbar(self._attempted_search_count + 1, len(self._to_be_searched), message='License progress:')
            if self._search_list['CRDNumber'][self._attempted_search_count] != '':
                if self._attempts < 2:
                    try:
                        crd = self._search_list['CRDNumber'][self._attempted_search_count]
                        url = self._url + str(crd)
                        self._sel.get(url)

                        self._licenses = []
                        reg_info = self._sel.find_elements_by_xpath(element)
                        for reg in reg_info:
                            if reg.text[:6] == 'Series':
                                self._licenses.append(int(reg.text[7:9]))
                        self._licenses.sort()
                        self._licenses = ['Series {0}'.format(l) for l in self._licenses]
                        self.__clean_licenses()
                    except:
                        self._licenses = []
                        self._attempts += 1

                else:
                    self._attempts = 0
                    self._licenses = ['CRD Not found']
                    self.__clean_licenses()
            else:
                self._licenses = []
                self.__clean_licenses()
        self.__close_selenium_components()

    def address_check(self, path):
        self.__init_address_metadata(path=path)
        print('Attempting to get addresses from FINRA for %s CRDs.' % len(self._search_list.index))
        self.__address_scrape()
        save_df(self._search_list, path=path)

    def __init_address_metadata(self, path):
        self._url = 'https://brokercheck.finra.org/individual/summary/'
        self._xpath = "//*[@class='leftPadding ng-binding']"
        self._search_list = read_df(path)
        self._search_list['Address'] = ''
        self.__init_selenium_components()

    def __address_scrape(self):
        '''
        private method.

        actual guts of the FINRA address search.
        :return: n/a
        '''
        element = self._xpath
        while self._attempted_search_count < len(self._search_list['CRDNumber']):
            myprogressbar(self._attempted_search_count + 1, len(self._search_list.index), message='Address progress:')
            if self._search_list['CRDNumber'][self._attempted_search_count] != '':
                if self._attempts < 2:
                    try:
                        crd = self._search_list['CRDNumber'][self._attempted_search_count]
                        url = self._url + str(crd)
                        self._sel.get(url)

                        self._address = []
                        reg_info = self._sel.find_elements_by_xpath(element)
                        for reg in reg_info:
                            self._address.append(reg.text)
                            break
                        self.__assign_address()
                    except:
                        self._address = []
                        self._attempts += 1

                else:
                    self._attempts = 0
                    self._address = ['Address Not found']
                    self.__assign_address()
            else:
                self._address = []
                self._address = ['Address Not found']
                self.__assign_address()
        self.__close_selenium_components()

    def __assign_address(self):
        self._search_list.ix[self._attempted_search_count, 'Address'] = self._address[0]
        self._attempted_search_count += 1
        del self._address

    def advisor_search(self, search_input, crd=True, licenses=False):
        '''
        public method.

        allows users to pass in lists or individual names / crds that
        they want to search in FINRA.

        based on whether CRD = True and/or Licenses = True, and the data type of the input,
        will determine what search can / may be performed.

        :param search_input: list or individual items to search for -- required
        :param crd: default = True -- optional
        :param licenses: default = False -- optional
        :return:
        '''
        self.__init_input_metadata(search_input)
        self.__determine_search_method(search_input, crd, licenses)
        self.__advisor_crd_search()
        raise BaseException("This method is incomplete. Instead, "
                            "please use the 'crd_check', 'license_check', or 'address_check' methods.")
        # need to build out actual search method for this.

        # if __name__ == '__main__':

        # how to create a variable to interact with the
        # FINRA scraping object.
        # fin = finraScraping()

        # this class has 3 methods through which the user can currently interact with.


        # 1. CRD Search - Used by List program
        # example of how to call / interact

        # fin.crd_check(path='path_to_excel_file.xlsx')


        # 2. License Search - Used by the List Program
        # example of how to call / interact

        # fin.license_check(path='path_to_excel_file.xlsx')

        # 3. Advisor Search - Used Ad Hoc by User
        # example of how to call / interact
        # Note - this method still needs to be further built out to
        # fully capture the initial intent of the method.

        # fin.advisor_search('Lance Murphy')

    def __str_or_int(self, search_input):
        '''
        private method.

        used to determine if data type of the search input string or int
        :param search_input: input data
        :return: updated self
        '''
        if type(search_input) is int:
            self._crd_enabled = True
            self._license_enabled = True
            self._search_data = [search_input]

        if type(search_input) is str:
            self._crd_enabled = True
            self._search_data = [search_input]

        return self

    def __input_type(self, search_input):
        '''
        private method.

        used to determine if what is passed is a list or individual variable.
        regardless of data type, it is passed to __str_or_int method to determine
        the data type to enable / disable certain FINRA search capabilities.

        :param search_input:
        :return: updated self
        '''
        if type(search_input) is list:
            self.__str_or_int(search_input[0])
            self._search_data = search_input
        else:
            self.__str_or_int(search_input)

        if not self._crd_enabled and not self._license_enabled:
            print('Input %s is of type %s which is not a supported format' % (
                search_input, type(search_input)
            ))
            sys.exit(0)
        return self

    def __init_input_metadata(self, search_input):
        '''
        initiates the metadata for the standard, one-off search functionality
        :param search_input: variable -- required
        :return: updated self
        '''
        self.__input_type(search_input)
        self._to_be_searched = self._search_data
        return self

    def __determine_search_method(self, search_input, crd, licenses):
        '''
        private method.

        used to determine if FINRA processing can be handled in the 'one-off'
        search based on the input of the user.
        :param search_input: variable -- required
        :param crd: boolean
        :param licenses: boolean
        :return: updated self.
        '''
        if not self._crd_enabled and crd:
            print('CRD is not possible to search for given the data type of input %s.' % (
                search_input
            ))
            sys.exit(0)

        if not self._license_enabled and licenses:
            print('License is not possible to search for given the data type of input %s.' % (
                search_input
            ))
            sys.exit(0)

        if (crd and licenses) and not (self._crd_enabled or self._license_enabled):
            print('Finra search cannot return CRD or Licenses as you provided %s'
                  'and the license search does not support %s type.' % (search_input,
                                                                        type(search_input)))
            sys.exit(0)


            # need to build out an actual way to determine what search method to use

        return self

    def __advisor_crd_search(self):
        '''
        private method.

        used to perform one-off / ad-hoc searches in FIRNA
        :return: n/a
        '''
        self.__init_selenium_components()
        self._sel.get(self._finra_site)
        self.__crd_only_search_functionality()
        for search in range(len(self._to_be_searched)):
            print("CRD search for '%s' returned: '%s'" % (self._to_be_searched[search], self._to_be_added[search]))
