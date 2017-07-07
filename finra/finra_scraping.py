import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from utility.gen_helper import create_path_name
from utility.pandas_helper import read_df, save_df, make_df
from utility.progress_bar import myprogressbar


class Finra:
    def __init__(self, path, alter_name=None):
        self.sel = None
        self.scrape_type = None
        self.crd = None
        self.url = None
        self.scraped_dict = None
        self.file_path = path
        self.save_to_path = self.__determine_save_path__(path=path, alter_name=alter_name)
        self.attempted_count = 0
        self._attempts = 0
        self._crd_scrape_url = 'http://www.finra.org/'
        self._broker_check_url = 'https://brokercheck.finra.org/individual/summary/'
        self.x_paths = {
            'disclosures': "//*[@id='disclosuresSection']/div/div/div/bc-section-content/div/md-list",
            'name': "//*[@id='bio-geo-summary']/div[1]/div[1]",
            'licenses': "//*[@class='md-body-1 ng-binding flex-gt-xs-80']",
            'crd': "//*[@id='crdnumber']/span[2]",
            'experience': '//*[@id="top"]/md-grid-list/md-grid-tile[2]/figure/bc-key-stats-item/div/md-card-content/div[1]/div[1]/div',
            'address': "//*[@class='leftPadding ng-binding']",
            'current_firm': "//*[@id='bio-geo-summary']/div[2]/div[3]/div[1]/div[1]",
            'crd_only_scrape' : ['finra_pc_search_box', 's4_item-field', 's4_suggestion']
        }
        self._chrome_driver = "C:/Python27/selenium/Chrome/chromedriver"
        os.environ["webdriver.chrome.driver"] = self._chrome_driver

    def __determine_save_path__(self, path, alter_name):
        if alter_name is None:
            return path
        else:
            return create_path_name(path, alter_name)

    def scrape(self):
        df = read_df(self.file_path)
        df.columns = [x.lower().strip() for x in df.columns]
        if 'crd' in df.columns:
            self.scrape_type = 'all'
            self.url = self._broker_check_url
            self.crd = [int(x) for x in df['crd'].values.tolist()]

        elif 'name' in df.columns:
            self.scrape_type = 'crd'
            self.url = self._crd_scrape_url

        else:
            raise KeyError('Not able to infer a search type from the data provided. \n%s' % ','.join(df.columns))

        self.__main_scraper__()
        df = self.return_scraped_data(df=df)
        save_df(df, self.save_to_path)

    def __main_scraper__(self, xpath_keys='all'):
        if xpath_keys == 'all':
            xpath_keys = [x for x in self.x_paths.keys() if x != 'crd_only_scrape']
            self.scraped_dict = {x: list() for x in xpath_keys}
        elif xpath_keys == 'crd':
            xpath_keys = self.x_paths['crd_only_scrape']
            self.scraped_dict = {x: list() for x in xpath_keys}

        self.__init_selenium_components()

        print('Attempting to get %s meta data from an individual Finra page.' % ', '.join(xpath_keys))
        while self.attempted_count < len(self.crd):
            myprogressbar(self.attempted_count + 1, len(self.crd), message='FINRA scraping')

            if self._attempts < 2:
                try:
                    tmp_url = self.url + str(self.crd[self.attempted_count])
                    self._sel.get(tmp_url)

                    for xk in xpath_keys:
                        intel = self._sel.find_elements_by_xpath(self.x_paths[xk])
                        meta = [i.text for i in intel]

                        if xk == 'licenses':
                            meta = [int(m[7:9]) for m in meta if m[:6] == 'Series']
                            meta.sort()
                            meta = ['Series {0}'.format(l) for l in meta]
                            try:
                                self.scraped_dict[xk].append(';'.join(meta))
                            except:
                                self.scraped_dict[xk].append(None)

                        elif xk in ['disclosures']:
                            self.scraped_dict[xk].append(len(meta))

                        elif xk in ['crd', 'experience', 'current_firm', 'name', 'address']:
                            try:
                                if xk == 'crd':
                                    self.scraped_dict[xk].append(int(meta[0]))
                                else:
                                    self.scraped_dict[xk].append(meta[0].title())
                            except:
                                self.scraped_dict[xk].append('unable to scrape.')

                    self.attempted_count += 1

                except:
                    self._attempts += 1
                    print('i hit an error.')
            else:
                self.attempted_count += 1
                self._attempts = 0
                print('skipping to the next record')

        self._sel.close()

    def __init_selenium_components(self):
        '''
        private method.

        initiates the components needed for selenium to funciton.
        :return: self
        '''
        self._sel = webdriver.Chrome(self._chrome_driver)
        self._wait = WebDriverWait(self._sel, 1)
        return self

    def return_scraped_data(self, df):
        scraped_df = pd.DataFrame(self.scraped_dict)
        df = df.merge(scraped_df, how='left', on='crd', suffixes=['_og', '_finra'])
        return df
