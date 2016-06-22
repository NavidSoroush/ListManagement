##imports all selenium libraries
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

##Declaring variables for the scraper to use
finra_site = 'http://brokercheck.finra.org/Individual/Summary/'
chromedriver = "C:/Python27/selenium/Chrome/chromedriver"
os.environ["webdriver.chrome.driver"] = chromedriver
elements=['col-md-3']
sel = webdriver.Chrome(chromedriver)
sel.get(finra_site)
wait = WebDriverWait(sel, 1)

##path='C:/Users/rschools/Desktop/CRD_Test.xlsx'

def licenseSearch(path):
    df=pd.read_excel(path)
    df['Licenses']=''
    print df.head()
    print 'Pulling licenses from FINRA for %s advisors.' % len(df[df['CRDNumber'].notnull()].index)
    for index, row in df.iterrows():
        if row['CRDNumber']!='':
            crd=row['CRDNumber']
            try:
                url=finra_site+str(crd)
                lic=[]
                sel.get(url)
                license_code=wait.until(EC.visibility_of_element_located((By.CLASS_NAME,elements[0])))
                reg_info=sel.find_elements_by_class_name(elements[0])
                for reg in reg_info:
                    if reg.text[:6]=='Series':
                        lic.append(int(reg.text[7:]))
                lic.sort()
                lic=['Series {0}'.format(l) for l in lic]
            except Exception,e:
                lic=[]
                print Exception, e
        else:
            lic=[]
        df.loc[index,['Licenses']]=';'.join(lic)
        del lic
    sel.close(), sel.quit()
    df.to_excel(path, index=False)
    return {'BDG Finra Scrape':'Success'}
##licenseSearch(path)

        


