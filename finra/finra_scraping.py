import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from utility.gen_helper import create_path_name
from utility.pandas_helper import read_df, save_df, make_df
from utility.progress_bar import myprogressbar


class Finra:
    def __init__(self, log=None):
        self.log = log
        self.sel = None
        self.scrape_type = None
        self.search = None
        self.lkup_name = None
        self.url = None
        self.scraped_dict = None
        self.save_to_path = None
        self.attempted_count = 0
        self._attempts = 0
        self._crd_scrape_url = 'http://www.finra.org/'
        self._broker_check_url = 'https://brokercheck.finra.org/individual/summary/'
        self.x_paths = {
            'Disclosures': "//*[@id='disclosuresSection']/div/div/div/bc-section-content/div/md-list",
            'Name': "//*[@id='bio-geo-summary']/div[1]/div[1]",
            'Licenses': "//*[@class='md-body-1 ng-binding flex-gt-xs-80']",
            'CRDNumber': "//*[@id='crdnumber']/span[2]",
            'Experience': '//*[@id="top"]/md-grid-list/md-grid-tile[2]/figure/bc-key-stats-item/div/md-card-content/div[1]/div[1]/div',
            'Address': "//*[@class='leftPadding ng-binding']",
            'CurrentFirm': "//*[@id='bio-geo-summary']/div[2]/div[3]/div[1]/div[1]",
            'crd_only_scrape': ['finra_pc_search_box', 's4_item-field', 's4_suggestion']
        }
        self._chrome_driver = "C:/Python27/selenium/Chrome/chromedriver"
        os.environ["webdriver.chrome.driver"] = self._chrome_driver

    def __determine_save_path__(self, path, alter_name):
        if alter_name is None:
            return path
        else:
            return create_path_name(path, alter_name)

    def scrape(self, path, alter_name=None, scrape_type=None, parse_list=False):
        self.__init_selenium_components()
        self.save_to_path = self.__determine_save_path__(path=path, alter_name=alter_name)
        df = read_df(path)
        df_cols = [x.lower().strip() for x in df.columns.tolist()]

        if 'crdnumber' in df_cols or scrape_type == 'all':
            self.scrape_type = 'all'
            self.url = self._broker_check_url
            self.search = [int(x) for x in df['CRDNumber'].values.tolist()]
            xpath_keys = [x for x in self.x_paths.keys() if x != 'crd_only_scrape']
            self.scraped_dict = {x: list() for x in xpath_keys}
            on = 'CRDNumber'

        elif 'finralookup' in df_cols or scrape_type == 'crd':
            self.scrape_type = 'crd'
            xpath_keys = self.x_paths['crd_only_scrape']
            self.search = [x for x in df['FinraLookup'].values.tolist()]
            self.scraped_dict = {'CRDNumber': list(), 'NumSuggestions': list(), 'FinraLookup': self.search}
            self._sel.get(self._crd_scrape_url)
            on = 'FinraLookup'

        else:
            raise KeyError('Not able to infer a search type from the data provided. \n%s' % ','.join(df.columns))

        self.__main_scraper__(xpath_keys=xpath_keys)
        df = self.return_scraped_data(df=df, on=on)
        save_df(df, self.save_to_path)
        if parse_list:
            found = self.__parse_scraped_list__(df=df)
            return {'Next Step': 'Search SEC',
                    'No CRD': create_path_name(self.save_to_path, new_name='_nocrd'),
                    'FINRA_SEC Found': create_path_name(self.save_to_path, new_name='_finrasec_found'),
                    'FINRA_Found': found,
                    'FINRA Ambiguous': create_path_name(self.save_to_path, new_name='_FINRA_ambiguous')}

    def __main_scraper__(self, xpath_keys):
        # self.log.info('Attempting to get %s meta data from an individual Finra page.' % ', '.join(xpath_keys))
        while self.attempted_count < len(self.search):
            myprogressbar(self.attempted_count + 1, len(self.search),
                          message='%s FINRA scraping' % self.scrape_type.upper())

            if self._attempts < 2:
                try:
                    if self.scrape_type == 'all':
                        tmp_url = self.url + str(self.search[self.attempted_count])
                        self._sel.get(tmp_url)

                        for xk in xpath_keys:
                            intel = self._sel.find_elements_by_xpath(self.x_paths[xk])
                            meta = [i.text for i in intel]

                            if xk == 'Licenses':
                                meta = [int(m[7:9]) for m in meta if m[:6] == 'Series']
                                meta.sort()
                                meta = ['Series {0}'.format(l) for l in meta]
                                try:
                                    self.scraped_dict[xk].append(';'.join(meta))
                                except:
                                    self.scraped_dict[xk].append(None)

                            elif xk in ['Disclosures']:
                                self.scraped_dict[xk].append(len(meta))

                            elif xk in ['CRDNumber', 'Experience', 'CurrentFirm', 'Name', 'Address']:
                                try:
                                    if xk == 'CRDNumber':
                                        self.scraped_dict[xk].append(int(meta[0]))
                                    else:
                                        self.scraped_dict[xk].append(meta[0].title())
                                except:
                                    self.scraped_dict[xk].append('CRD Not Found')
                    else:
                        page_src = self._sel.page_source
                        if xpath_keys[0] in page_src:
                            search_bar = self._sel.find_element_by_id(xpath_keys[0])
                            if self.attempted_count == 0:
                                search_bar.send_keys('test')
                                search_bar.clear()
                            search_bar.send_keys(str(self.search[self.attempted_count]))
                            try:
                                code = self._wait.until(ec.visibility_of_element_located((By.CLASS_NAME,
                                                                                          xpath_keys[1])))
                                crd_text = code.text.split()
                                suggestions = (len(page_src.split(xpath_keys[2])) - 1)

                                if suggestions == 0:
                                    self.scraped_dict['CRDNumber'].append("CRD Not Found")
                                    self.scraped_dict['NumSuggestions'].append(suggestions)

                                elif suggestions > 1:
                                    self.scraped_dict['CRDNumber'].append("Multiple CRDs Present")
                                    self.scraped_dict['NumSuggestions'].append(suggestions)

                                else:
                                    self.scraped_dict['CRDNumber'].append(crd_text[crd_text.index("(CRD#") + 1][:-1])
                                    self.scraped_dict['NumSuggestions'].append(suggestions)
                            except:
                                self.scraped_dict['CRDNumber'].append("CRD Not Found")
                                self.scraped_dict['NumSuggestions'].append(0)

                            search_bar.clear()
                        else:
                            self.__refreshing__()
                            self._attempts += 1

                    self.attempted_count += 1

                except:
                    self._attempts += 1
            else:
                self.attempted_count += 1
                self._attempts = 0

        self._sel.close()

    def __init_selenium_components(self):
        '''
        private method.

        initiates the components needed for selenium to funciton.
        :return: self
        '''
        self._sel = webdriver.Chrome(self._chrome_driver)
        self._wait = WebDriverWait(self._sel, 3)
        return self

    def __parse_scraped_list__(self, df):
        no_crd = df[df['CRDNumber'] == 'CRD Not Found']
        multiple_crds = df[df['CRDNumber'] == 'Multiple CRDs Present']
        found = df[(df['CRDNumber'] != 'Multiple CRDs Present') & (df['CRDNumber'] == 'CRD Not Found')]
        save_df(df=no_crd, path=create_path_name(self.save_to_path, new_name='_nocrd'))
        save_df(df=multiple_crds, path=create_path_name(self.save_to_path, new_name='_FINRA_ambiguous'))
        save_df(df=found, path=create_path_name(self.save_to_path, new_name='_finrasec_found'))
        return len(found.index)

    def __refreshing__(self):
        self._sel.refresh()

    def return_scraped_data(self, df, on):
        scraped_df = pd.DataFrame(self.scraped_dict)
        df = df.merge(scraped_df, how='left', left_on=on, right_on=on, suffixes=['_og', '_finra'])
        return df
