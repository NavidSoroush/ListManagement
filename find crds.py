from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import re
import pandas as pd
from functions import splitname
import unicodedata

'''
CHANGE LOG

5.18 - Search now in a while loop to account for necessary page refreshes. Need to add confidence check still.

'''

def StripUnicodeChars(row):
    '''
    attempts to remove all unicode data from the row values.

    :param row: cell value with unicode chars
    :return: transformed cell value without unicode chars
    '''
    return [unicodedata.normalize('NFKD',r).encode('utf-8','ignore') for r in row]

def no_crd_path(path):
    '''
    creates a new file for advisors without CRD numbers.

    :param path: original path
    :return: new path for no_crd file
    '''
    fname = splitname(path)
    rootpath = path[:len(path)-len(fname)]
    fname = fname[:-5]+'_nocrd.xlsx'
    found_path = rootpath+fname
    return found_path

def found_FINRASEC_path(path):
    '''
    creates a new file for advisors found by FINRA / SEC scraping.

    :param path: original path
    :return: new path for found file
    '''
    fname=splitname(path)
    rootpath=path[:len(path)-len(fname)]
    fname=fname[:-5]+'_finrasec_found.xlsx'
    found_path=rootpath+fname
    return found_path

def FINRA_ambiguous_path(path):
    '''
    creates a new file for advisors found by FINRA with more than one
    suggestion in the FINRA search.

    :param path: original path
    :return: new path for ambiguous file file
    '''
    fname=splitname(path)
    rootpath=path[:len(path)-len(fname)]
    fname=fname[:-5]+'_FINRA_ambiguous.xlsx'
    found_path=rootpath+fname
    return found_path

##The following code takes the contacts not found in the initial search (rows in Campaign_list)
##and adds search names to a list to be search for via Rickys code'
'It appends the results of the FINRA scrape to a dataframe'
def fin_search(path, foundPath, chromedriver = "C:/Python27/selenium/Chrome/chromedriver"):
    '''
    attempts to search FINRA to get CRD numbers for advisors not found
    in the SFDC search.

    :param path: path of adivsors that need to be scrapped
    :param foundPath: path to advisors that were found via SFDC search 1
    :param chromedriver: path to chromedriver
    :return: updated dictionary data to guide main_module in list processing.
    '''
    os.environ["webdriver.chrome.driver"] = chromedriver
    finra_site = 'http://www.finra.org/'
    
    print '\nStep 5:\nScraping FINRA data.'
    finra_sec_foundPath=found_FINRASEC_path(path)
    no_crd_fname=no_crd_path(path)
    FINRA_uncertain_path=FINRA_ambiguous_path(path)
    no_crd=pd.DataFrame()
    FINRA_ambiguity=pd.DataFrame()
    
    Campaign_list = pd.read_excel(path, sheet=0, encoding='utf-8')

    to_be_searched = []
    try:
        Campaign_list['FirstName']=df.apply(StripUnicodeChars)
        Campaign_list['LastName']=df.apply(StripUnicodeChars)
        Campaign_list['Account']=df.apply(StripUnicodeChars)
    except:
        pass
    
    #Campaign_list['FirstName'].astype(str)
    #Campaign_list['LastName'].astype(str)
    #Campaign_list['Account'].astype(str)

##  Reference to an output dataframe from step 2. Create list of search texts
    for index, row in Campaign_list.iterrows():
        try:
            search_name = row['FirstName'] + ' ' + row['LastName'] + ' ' + row['Account'][:10]
        except:
            search_name = 'Error converting row %s to string' % index
        to_be_searched = to_be_searched + [search_name]
        
    
    sel = webdriver.Chrome(chromedriver)
    sel.get(finra_site)
    wait = WebDriverWait(sel, 1)

    to_be_added=[]
    elements = ['finra_pc_search_box','s4_item-field', 's4_suggestion']

    attempted_search_count = 0
    found = 0
    num_suggestions=[]

    print 'Number of searches to perform: %s' % len(to_be_searched)
    
##  Perform search
    while attempted_search_count < len(to_be_searched): 
        try:
            page_source = sel.page_source
            if elements[0] in page_source:
                sBar = sel.find_element_by_id(elements[0])
                sBar.send_keys(to_be_searched[attempted_search_count])
                try:
                    code = wait.until(EC.visibility_of_element_located((By.CLASS_NAME,elements[1])))
                    s_text = code.text.split()
                    suggestion_code=sel.page_source
                    choices = len(suggestion_code.split(elements[2]))-1
                    if choices == 0:
                        to_be_added += ["CRD Not Found"]
                        attempted_search_count += 1
                        num_suggestions += [0]
                    elif choices>1:
                        to_be_added += ["Multiple CRDs Present"] 
                        attempted_search_count +=1
                        num_suggestions += [choices]
                  
                    else:
                        crd_text = s_text.index("(CRD#")+1
                        crd = ' '.join(s_text[:crd_text+1])
                        to_be_added += [crd]
                        found += 1
                        attempted_search_count += 1
                        num_suggestions += [choices]
                    
                except:
                    to_be_added += ["CRD Not Found"]
                    attempted_search_count += 1
                    num_suggestions += [0]

##                for debugging
##                print '\nSearch # %s\nSearching for: %s' % (attempted_search_count, to_be_searched[attempted_search_count-1])
##                print 'Number FINRA suggestions: %s' % num_suggestions[attempted_search_count-1]
##                print 'CRD Return Num Or String: %s\n\n' % to_be_added[attempted_search_count-1]
                
                sBar.clear()
            else:
                sel.refresh()
                print 'refreshing...'
        except:
            sel.refresh()
            print 'refreshing...'
            
    sel.close(), sel.quit()


    print 'Confidently found %s CRD numbers from the FINRA search.' % found
    Campaign_list.insert(len(Campaign_list.columns),'CRDNumber',to_be_added)
    Campaign_list.insert(len(Campaign_list.columns),'NumSuggestions',num_suggestions)
    no_crd=Campaign_list[Campaign_list['CRDNumber']=='CRD Not Found']
    FINRA_ambiguity = Campaign_list[Campaign_list['CRDNumber']=='Multiple CRDs Present']
    found_df=Campaign_list[(Campaign_list['CRDNumber']!='CRD Not Found') & (Campaign_list['CRDNumber']!='Multiple CRDs Present')]
    del no_crd['CRDNumber']
    del Campaign_list['NumSuggestions']
    del no_crd['NumSuggestions']
    del found_df['NumSuggestions']
    no_crd.to_excel(no_crd_fname,index=False)
    FINRA_ambiguity.to_excel(FINRA_uncertain_path, index=False)
    found_df.to_excel(finra_sec_foundPath,index=False)
##    Campaign_list.to_excel(path, index=False)

    ret_item = {'Next Step': 'Search SEC', 'No CRD': no_crd_fname
                ,'FINRA_SEC Found':finra_sec_foundPath,'FINRA_Found':found, 'FINRA Ambiguous':FINRA_uncertain_path}
    return ret_item




### End of Max's ideas ###


##for testing
##if __name__=='__main__':
##    found_contacts_macpath='/Users/rickyschools/Desktop/found_contacts.xlsx'
##    test_file_macpath='/Users/rickyschools/Desktop/test_list.xlsx'
##    mac_chrome_driver='/Users/rickyschools/Documents/ChromeDriver/chromedriver'
##    fin_search(test_file_macpath, found_contacts_macpath, mac_chrome_driver)
##    test_file_windows='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/FINRA_Search_Test/test_list.xlsx'
##    found_contacts_windows='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/FINRA_Search_Test/found_contacts.xlsx'
##    fin_search(test_file_windows, found_contacts_windows)


fin_search('C:/Users/mcharles/Desktop/test_list.xlsx','C:/Users/mcharles/Desktop/found_list.xlsx')