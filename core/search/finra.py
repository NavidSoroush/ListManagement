"""
finra.py
======================================================
Provides an 'API' via Selenium for extracting metadata
on registered financial advisors from Finra BrokerCheck.
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from chromedriver import CHROMEDRV_PATH

try:
    from ListManagement.utils import general as _ghelp
    from ListManagement.utils.pandas_helper import read_df, save_df, make_df
except:
    from ListManagement.utils import general as _ghelp
    from ListManagement.utils.pandas_helper import read_df, save_df, make_df


class Finra:
    """
    A web scraper that leverages FINRA to:
        1) Find the CRD of a financial advisor given a 'Lookup Name'. (First, Last, Firm Name)
        2) Find metadata (see self._x_paths keys below) on a financial advisor, given their CRD Number.
    """

    def __init__(self, log=None):
        self._log = log
        self._sel = None
        self._scrape_type = None
        self._search = None
        self.lkup_name = None
        self.url = None
        self._scraped_dict = None
        self._save_to_path = None
        self._attempted_count = 0
        self._attempts = 0
        self._crd_scrape_url = 'http://www.finra.org/'
        self._broker_check_url = 'https://brokercheck.finra.org/individual/summary/'
        self._x_paths = {
            'Disclosures': "//*[@id='disclosuresSection']/div/div/div/bc-section-content/div/md-list",
            'Name': "//*[@id='bio-geo-summary']/div[1]/div[1]",
            'Licenses': "//*[@class='md-body-1 ng-binding flex-gt-xs-80']",
            'CRDNumber': "//*[@id='crdnumber']/span[2]",
            'Experience': '//*[@id="top"]/md-grid-list/md-grid-tile[2]/figure/bc-key-stats-item/div/md-card-content/div[1]/div[1]/div',
            'Address': "//*[@class='leftPadding ng-binding']",
            'CurrentFirm': "//*[@id='bio-geo-summary']/div[2]/div[3]/div[1]/div[1]",
            'crd_only_scrape': ['finra_pc_search_box', 's4_item-field', 's4_suggestion']
        }

    def _determine_save_path(self, path, alter_name):
        """
        Helper function to determine where to save the results of their scrape.
        Parameters
        ----------
        path
            A string; Represents a full file path.
        alter_name
            A string; Represents a suffix to append to a full file path.
        Returns
        -------
            A string representing the original (or updated) full file path.
        """
        if alter_name is None:
            return path
        else:
            return _ghelp.create_path_name(path, alter_name)

    def scrape(self, _vars, alter_name=None, scrape_type=None, parse_list=False, save=False):
        """
        User level method allowing them access to the Finra 'API'. Given a tabular file (Excel, CSV),
        a user can specify:
            1) The scrape type ('all', see self._x_paths above, or 'crdnumber') they desire to perform.
            2) If they want to save the results of the file.
            3) An option to parse the results of the scrape into 3 parts: (typically for scrape_type='crdnumber'
                a) Found
                b) Not found
                c) Ambiguous (due to multiple advisors having the same name)
        Parameters
        ----------
        path
            A string; Represents a full file path.
        alter_name
            A string; Represents a suffix to append to a full file path.
        scrape_type
            A string; The scrape type ('all', see self._x_paths above, or 'crdnumber') they desire to perform.
        parse_list
            Boolean; Used to enable the list parsing (see 3) above).
        save
            Boolean; Determines whether scraped results are saved to a file path or returned to the user in a console.

        Returns
        -------
            Dependent on save parameter above.
            Scraped results are saved to a file path or returned to the user in a console.
        """
        _vars.update_state()
        self._init_selenium_components()
        self._save_to_path = self._determine_save_path(path=_vars.list_base_path, alter_name=alter_name)
        df = _vars.list_source['frame'].copy() if scrape_type == 'crd' else _vars.found['frame'].copy()
        df_cols = [x.lower().strip() for x in df.columns.tolist()]

        if 'crdnumber' in df_cols or scrape_type == 'all':
            self._scrape_type = 'all'
            self.url = self._broker_check_url
            self._search = [int(x) if x != '' else 0 for x in df['CRDNumber'].values.tolist()]
            xpath_keys = [x for x in self._x_paths.keys() if x != 'crd_only_scrape']
            self._scraped_dict = {x: list() for x in xpath_keys}
            on = 'CRDNumber'

        elif 'finralookup' in df_cols or scrape_type == 'crd':
            self._scrape_type = 'crd'
            xpath_keys = self._x_paths['crd_only_scrape']
            self._search = [x for x in df['FinraLookup'].values.tolist()]
            self._scraped_dict = {'CRDNumber': list(), 'NumSuggestions': list(), 'FinraLookup': self._search}
            self._sel.get(self._crd_scrape_url)
            on = 'FinraLookup'

        else:
            raise KeyError('Not able to infer a search type from the data provided. \n%s' % ','.join(df.columns))

        self._main_scraper(xpath_keys=xpath_keys)
        df = self.return_scraped_data(df=df, on=on)
        if parse_list:
            _vars, df = self._parse_scraped_list(df=df, _vars=_vars)
            if scrape_type == 'crd':
                _vars.list_source['frame'] = df
            else:
                _vars.found['frame'] = df
            return _vars

        if save:
            _vars.found['frame'] = df
            return _vars

    def _main_scraper(self, xpath_keys):
        """
        Worker that loops through all available requests (dependent on scrape_type) and returns
        the available data for that scrape type.

        Parameters
        ----------
        xpath_keys
            A list of HTML xpath keys to extract from a HTML web-page.

        Returns
        -------
            Nothing.
        """
        # self.log.info('Attempting to get %s meta data from an individual Finra page.' % ', '.join(xpath_keys))
        self._attempted_count = 0
        while not len(set(map(len, self._scraped_dict.values()))) == 1 and self._attempted_count < len(self._search):
            _ghelp.myprogressbar(self._attempted_count + 1, len(self._search),
                                 message='%s FINRA scraping' % self._scrape_type.upper())

            if self._attempts < 2:
                try:
                    if self._scrape_type == 'all':
                        tmp_url = self.url + str(self._search[self._attempted_count])
                        self._sel.get(tmp_url)

                        for xk in xpath_keys:
                            intel = self._sel.find_elements_by_xpath(self._x_paths[xk])
                            meta = [i.text for i in intel]

                            if xk == 'Licenses':
                                meta = [int(m[7:9]) for m in meta if m[:6] == 'Series']
                                meta.sort()
                                meta = ['Series {0}'.format(l) for l in meta]
                                try:
                                    self._scraped_dict[xk].append(';'.join(meta))
                                except:
                                    self._scraped_dict[xk].append(None)

                            elif xk in ['Disclosures']:
                                self._scraped_dict[xk].append(len(meta))

                            elif xk in ['CRDNumber', 'Experience', 'CurrentFirm', 'Name', 'Address']:
                                try:
                                    if xk == 'CRDNumber':
                                        self._scraped_dict[xk].append(int(meta[0]))
                                    else:
                                        self._scraped_dict[xk].append(meta[0].title())
                                except:
                                    self._scraped_dict[xk].append('CRD Not Found')
                    else:
                        page_src = self._sel.page_source
                        if xpath_keys[0] in page_src:
                            search_bar = self._sel.find_element_by_id(xpath_keys[0])
                            search_bar.send_keys(str(self._search[self._attempted_count]))
                            try:
                                code = self._wait.until(ec.visibility_of_element_located((By.CLASS_NAME,
                                                                                          xpath_keys[1])))
                                page_src = self._sel.page_source
                                crd_text = code.text.split()
                                suggestions = (len(page_src.split(xpath_keys[2])) - 1)
                                if suggestions == 0:
                                    self._scraped_dict['CRDNumber'].append("CRD Not Found")
                                    self._scraped_dict['NumSuggestions'].append(suggestions)

                                elif suggestions > 1:
                                    self._scraped_dict['CRDNumber'].append("Multiple CRDs Present")
                                    self._scraped_dict['NumSuggestions'].append(suggestions)

                                else:
                                    self._scraped_dict['CRDNumber'].append(crd_text[crd_text.index("(CRD#") + 1][:-1])
                                    self._scraped_dict['NumSuggestions'].append(suggestions)
                            except:
                                self._scraped_dict['CRDNumber'].append("CRD Not Found")
                                self._scraped_dict['NumSuggestions'].append(0)

                            search_bar.clear()
                        else:
                            self._refreshing()
                            self._attempts += 1

                    self._attempted_count += 1

                except:
                    self._attempts += 1
            else:
                self._attempted_count += 1
                self._attempts = 0

        self._sel.close()

    def _init_selenium_components(self):
        """
        Helper function. Instantiates Selenium driver and Wait objects.

        Returns
        -------
            Updated Finra object.
        """
        self._sel = webdriver.Chrome(CHROMEDRV_PATH)
        self._wait = WebDriverWait(self._sel, 1)
        return self

    def _parse_scraped_list(self, df, _vars):
        """
        Given a scraped list, a pandas data frame parsed into:
            1) Found
            2) Not found (No CRD)
            3) Ambiguous
        Parameters
        ----------
        df
            A pandas data frame containing scraped metadata from FINRA.

        Returns
        -------
            A tuple, (number of advisors found, updated data frame of Found reps only.)
        """
        _vars.no_crd['frame'] = df[df['CRDNumber'] == 'CRD Not Found']
        _vars.finra_ambiguous['frame'] = df[df['CRDNumber'] == 'Multiple CRDs Present']
        _vars.finra_found['frame'] = df[~(df['CRDNumber'].isin(['Multiple CRDs Present', 'CRD Not Found']))]

        df = df[(df['CRDNumber'] == 'Multiple CRDs Present') | (df['CRDNumber'] == 'CRD Not Found')]
        return _vars, df

    def _refreshing(self):
        """
        Helper function to refresh a web page via Selenium.
        Returns
        -------
        Nothing.
        """
        self._sel.refresh()

    def return_scraped_data(self, df, on):
        """
        Transforms a dictionary (containing scraped advisor metadata) into a pandas data frame.
        Parameters
        ----------
        df
            A pandas data frame containing the original information/advisors to scrape.
        on
            A string; Represents what we should
        Returns
        -------
            The original pandas data frame joined with the scraped data frame.
        """
        scraped_df = make_df(self._scraped_dict)
        df = df.merge(scraped_df, how='left', left_on=on, right_on=on, suffixes=['_og', '_finra'])
        return df
