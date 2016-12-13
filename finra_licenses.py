##imports all selenium libraries
from selenium import webdriver
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

##Declaring variables for the scraper to use
finra_site = 'http://brokercheck.finra.org/Individual/Summary/'
chromedriver = "C:/Python27/selenium/Chrome/chromedriver"
os.environ["webdriver.chrome.driver"] = chromedriver
elements = ['.md-body-1.ng-binding.flex-gt-xs-80']


##path='C:/Users/rschools/Desktop/CRD_Test.xlsx'

def licenseSearch(path, attempted_search_count=0, attempts=0):
    '''
<div class="md-body-1 ng-binding flex-gt-xs-80" flex-gt-xs="80">Series 65 - Uniform Investment Adviser Law Examination</div>
    :param path: file path for list of advisors to scrape FINRA licenses
    :param attempted_search_count:
    :param attempts:
    :return: status of the finra license scraping
    '''
    df = pd.read_excel(path)
    df['Licenses'] = ''
    print 'Pulling licenses from FINRA for %s advisors.' % len(df[df['CRDNumber'].notnull()].index)
    sel = webdriver.Chrome(chromedriver)
    wait = WebDriverWait(sel, 1)
    while attempted_search_count < len(df['CRDNumber']):
        if df['CRDNumber'][attempted_search_count] != '':
            if attempts < 2:
                try:
                    crd = df['CRDNumber'][attempted_search_count]
                    url = finra_site + str(crd)
                    sel.get(url)
                    lic = []
                    wait
                    reg_info = sel.find_elements_by_css_selector(elements[0])
                    for reg in reg_info:
                        if reg.text[:6] == 'Series':
                            split=reg.text.split()
                            lic.append(int(split[1]))
                    lic.sort()
                    lic = ['Series {0}'.format(l) for l in lic]
                    df.loc[attempted_search_count, ['Licenses']] = ';'.join(lic)
                    attempted_search_count += 1
                    del lic
                except:
                    lic = []
                    attempts += 1

            else:
                attempts = 0
                lic = ['CRD Not found']
                df.loc[attempted_search_count, ['Licenses']] = ';'.join(lic)
                attempted_search_count += 1
                del lic
        else:
            lic = []
            df.loc[attempted_search_count, ['Licenses']] = ';'.join(lic)
            attempted_search_count += 1
            del lic

    sel.close(), sel.quit()
    df.to_excel(path, index=False)
    return {'BDG Finra Scrape': 'Success'}

##licenseSearch(path)
