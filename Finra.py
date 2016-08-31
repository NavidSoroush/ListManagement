from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import re
import pandas as pd
from functions import splitname
import unicodedata


def strip_unicode_chars(row):
    '''
    attempts to remove all unicode data from the row values.

    :param row: cell value with unicode chars
    :return: transformed cell value without unicode chars
    '''
    return [unicodedata.normalize('NFKD', r).encode('utf-8', 'ignore') for r in row]


def no_crd_path(path):
    '''
    creates a new file for advisors without CRD numbers.

    :param path: original path
    :return: new path for no_crd file
    '''
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_nocrd.xlsx'
    found_path = rootpath + fname
    return found_path


def found_finra_sec_path(path):
    '''
    creates a new file for advisors found by FINRA / SEC scraping.

    :param path: original path
    :return: new path for found file
    '''
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_finrasec_found.xlsx'
    found_path = rootpath + fname
    return found_path


def finra_ambiguous_path(path):
    '''
    creates a new file for advisors found by FINRA with more than one
    suggestion in the FINRA search.

    :param path: original path
    :return: new path for ambiguous file file
    '''
    fname = splitname(path)
    rootpath = path[:len(path) - len(fname)]
    fname = fname[:-5] + '_FINRA_ambiguous.xlsx'
    found_path = rootpath + fname
    return found_path


def read_excel(path):
    return pd.read_excel(path, sheet=0, encoding='utf-8')


class finraScraping:
    def __init__(self):
        self._chrome_driver = "C:/Python27/selenium/Chrome/chromedriver"
        os.environ["webdriver.chrome.driver"] = self._chrome_driver
        self._finra_site = 'http://www.finra.org/'
        self._elements = ['finra_pc_search_box', 's4_item-field', 's4_suggestion']
        self._attempted_search_count = 0
        self._found = 0
        self._no_crd = pd.DataFrame()
        self._finra_ambiguity = pd.DataFrame()
        self._search_list = None
        self._finra_sec_found_path = ''
        self._no_crd_fname = ''
        self._uncertain_path = ''
        self._to_be_searched = []
        self._to_be_added = []
        self._num_suggestions = []
        self._found_df = ''

    def __init_selenium_components(self):
        self._sel = webdriver.Chrome(self._chrome_driver)
        self._wait = WebDriverWait(self._sel, 1)

    def __create_finra_search_output_paths(self, path):
        self._finra_sec_found_path = found_finra_sec_path(path)
        self._no_crd_fname = no_crd_path(path)
        self._uncertain_path = finra_ambiguous_path(path)
        return self

    def __data_preparations(self):
        self._search_list['FirstName'] = pd.apply(strip_unicode_chars)
        self._search_list['LastName'] = pd.apply(strip_unicode_chars)
        self._search_list['Account'] = pd.apply(strip_unicode_chars)
        for index, row in self._search_list.iterrows():
            try:
                search_name = row['FirstName'] + ' ' + row['LastName'] + ' ' + row['Account']
            except ValueError:
                search_name = 'Error converting row %s to string' % index
            self._to_be_searched.append([search_name])
        return self

    def __refreshing(self):
        self._sel.refresh()
        print('refreshing...')

    def __crd_only_search_functionality(self, elements=[]):
        if len(elements) > 0:
            self._elements = elements
        while self._attempted_search_count < len(self._to_be_searched):
            try:
                page_source = self._sel.page_source
                if self._elements[0] in page_source:
                    search_bar = self._sel.find_element_by_id(self._elements[0])
                    search_bar.send_keys(self._to_be_searched[self._attempted_search_count])
                    try:
                        code = self._wait.until(EC.visibility_of_element_located((By.CLASS_NAME,
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
        self._sel.close(), self._sel.quit()
        return self

    def __save_outputs(self):
        self._no_crd.to_excel(self._no_crd_fname, index=False)
        self._finra_ambiguity.to_excel(self._uncertain_path, index=False)
        self._found_df.to_excel(self._finra_sec_found_path, index=False)
        return self

    def __data_output_prep(self):
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

    def crd_only_finra_search(self, path, url=''):
        if url != '':
            self._finra_site = url
        print('\nStep 5:\nScraping FINRA data.')
        self.__create_finra_search_output_paths(path)
        self._search_list = read_excel(path)
        self.__data_preparations()

        self._sel.get(self._finra_site)
        print('Number of searches to perform: %s' % len(self._to_be_searched))

        self.__crd_only_search_functionality()
        print('Confidently found %s CRD numbers from the FINRA search.' % self._found)

        self.__data_output_prep()

        ret_item = {'Next Step': 'Search SEC',
                    'No CRD': self._no_crd_fname,
                    'FINRA_SEC Found': self._finra_sec_found_path,
                    'FINRA_Found': self._found,
                    'FINRA Ambiguous': self._uncertain_path}
        return ret_item
