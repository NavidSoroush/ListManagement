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
    fname=splitname(path)
    rootpath=path[:len(path)-len(fname)]
    fname=fname[:-5]+'_foundcontacts.xlsx'
    found_path=rootpath+fname
    return found_path
def review_contact_path(path):
    fname=splitname(path)
    rootpath=path[:len(path)-len(fname)]
    fname=fname[:-5]+'_review_contacts.xlsx'
    found_path=rootpath+fname
    return found_path

def sf_advlist():
    print "Please wait. Downloading SFDC list as today's file was not available."
    from sqlQuery import run
    run()
    
user = os.environ.get("USERNAME")
AdvListPath = 'T:/Shared/FS2 Business Operations/Search Program/Salesforce Data Files/SFDC Advisor List as of ' + time.strftime("%m-%d-%y") + '.csv'
if os.path.exists(AdvListPath)==False:
    sf_advlist()

#path for testing
#path = 'C:/Users/'+user+'/Dropbox/Python Search Program/New Lists/Chicago Pre Attendee.xlsx'
#Grab SF advisor list. Edit to where ever this can be found
#Pseudocode


def df_column_preprocessing(df):
    for col in df.columns:
        if df[col].dtype not in ('int64', 'float64'):
            df[col]=df[col].str.decode('ascii').str.encode('utf-8')
    return df


def searchone(path, listType=None, review_path=None): 
    '''
    In short, this function should be used to prepare the data and perform an
    initial search against the current SFDC advisor database.
    =======================================================================
    
    PSEUDOCODE: 
    This function should open the list 'to-be-searched' (currently assumes
    the data is on the first sheet) as well as the SFDC advisor list. From
    the 'to-be-searched' list, all headers that are marked as 'unknown' by
    the match program should be removed. Fill all 'NA'/'NULL' values with ''.
    If 'FullName'    is present in the 'to-be-searched' headers then the name
    should be split into first and last names. In addition to transforming /
    cleansing full, first, and last name fields - state and zip code should
    cleaned.Following these transformations a 'LkupName' field that is a
    combination of First Name, Last Name,    Account Name, State, And Zip.
    If any values aren't present, skip the 'LkupName' creation. Search the
    'to-be-searched' file by CRD, Email, AMPF_MBR_ID,and LkupName (if present)
    against the SFDC advsior file.
    '''
    
    print '\nStep 4:\nPreparing list and searching against SFDC.'
    Campaign_list = pd.read_excel(path, sheetname=0)
    Advisor_list = pd.read_csv(AdvListPath,error_bad_lines=False,low_memory=False)
    headers = Campaign_list.columns.values

    keepCols = [c for c in Campaign_list.columns if c.lower() != 'unknown']
    Campaign_list = Campaign_list[keepCols]
    Campaign_list = Campaign_list.fillna('')

    Campaign_list = df_column_preprocessing(Campaign_list)

    #If we have the information to make LkupName, do so
    if "MailingPostalCode" in headers and "MailingState" in headers:
        
        #Format Zip codes
        Campaign_list['MailingPostalCode']=Campaign_list['MailingPostalCode'].astype(str)
        for index, row in Campaign_list.iterrows():
            Campaign_list.loc[index,"MailingPostalCode"] = row["MailingPostalCode"].split('-')[0]
            if len(row["MailingPostalCode"])==9:
                Campaign_list.loc[index,"MailingPostalCode"]=row["MailingPostalCode"][:5]
            elif len(row["MailingPostalCode"])==8:
                Campaign_list.loc[index,"MailingPostalCode"]=row["MailingPostalCode"][:4]

        if np.mean(Campaign_list['MailingState'].str.len()) > 2:
            import us
            print 'MailingState column needs to be transformed.'
            for index, row in Campaign_list.iterrows():
                try:
                    state = us.states.lookup(Campaign_list.loc[index,"MailingState"])
                    Campaign_list.loc[index,"MailingState"] = state
                except:
                    pass

        #Format name as necessary
        #Split FullName if given, cleanup first/last name, create lkup name
        if "FirstName" in headers and "LastName" in headers:        
            Campaign_list["LkupName"]=Campaign_list["FirstName"].str[:3] + Campaign_list["LastName"] + Campaign_list["Account"].str[:10] + Campaign_list["MailingState"] + Campaign_list["MailingPostalCode"]
            headers = Campaign_list.columns.values 
        elif "FullName" in headers:
            Campaign_list.insert(0,"LastName","")
            Campaign_list.insert(0,"FirstName","")
            for index, row in Campaign_list.iterrows():
                if ',' in row["FullName"]:
                    if row["FullName"].index(' ') < row["FullName"].index(','): #A Space comes before the comma. Assume we are dealing with First Last, Accred orientatoin
                        row["FirstName"]=row["FullName"].split(' ')[0]
                        row["LastName"]=row["FullName"].split(' ')[1][:-1]
                    else: #Comma before space. Assume Last, First orientation
                        row["LastName"]=row["FullName"].split(',')[0]
                        row["FirstName"]=row["FullName"].split(' ')[1]#Assumes space after ','
                        
                else: #Assume first last/middle last/suffix order
                    names = row["FullName"].split()
                    names_left = []
                    names_to_remove = ["jr","jr.","sr","sr.","ii","iii","iv",'aams','aif','aifa','bcm','caia','casl','ccps','cdfa','cea','cebs','ces','cfa','cfe','cfp','cfs','chfc','chfcicap','chfebc','cic','cima','cis','cltc','clu','cpa','cpwa','crpc','crps','csa','iar','jd','lutcf','mba','msa','msfp','pfs','phd','ppc']
                    for name in names:
                        if name.lower() in names_to_remove:
                            continue
                        else:
                            names_left = names_left+ [name]
                    if len(names_left)==3:
                        Campaign_list.loc[index,"FirstName"]=names_left[0]
                        Campaign_list.loc[index,"LastName"]=names_left[2]
                    else:
                        Campaign_list.loc[index,"FirstName"]=names_left[0]
                        Campaign_list.loc[index,"LastName"]=names_left[1]

            Campaign_list["LkupName"]=Campaign_list["FirstName"].str[:3] + Campaign_list["LastName"] + Campaign_list["Account"].str[:10] + Campaign_list["MailingState"] + Campaign_list["MailingPostalCode"]
            headers = Campaign_list.columns.values
        else:
            print "Advisor name or account information missing"

    #Search through the 3 fields we want to try to match by       
    searchfields = ['AMPFMBRID','Email','LkupName']
    returnFields=['AccountId','SourceChannel','Needs Info Updated?','ContactID', 'CRDNumber','BizDev Group']
    if listType!='BizDev Group':
        del returnFields[-1]
    
    found_contacts = pd.DataFrame()
    contacts_to_review = pd.DataFrame()
    to_FINRA = True
    n=0
    
    if 'CRDNumber' in headers:
        (found_contacts, Campaign_list, n, found, to_FINRA) = CRDsearch(Campaign_list, Advisor_list, n, listType) #output is df

    headers = Campaign_list.columns.values
    if to_FINRA == False:
        print 'CRD Info provided for all contacts. Will not search FINRA.'    
    else:
        for header in searchfields:
            if header in headers:
                n+=1
                print 'Performing search #%s on %s' % (n,header)
                j_headers=[header]
                for rf in returnFields:
                    j_headers.append(rf)
                headerandIDs = Advisor_list[j_headers]
                Campaign_list = Campaign_list.merge (headerandIDs, how='left', on = header)
                Campaign_list = Campaign_list.fillna('')
                num_searched_on = len(Campaign_list)
                if 'CRD Provided by List' in headers:
                    contacts_to_review = contacts_to_review.append(Campaign_list[Campaign_list['ContactID']!=''], ignore_index = True)
                    Campaign_list = Campaign_list[Campaign_list['ContactID']=='']
                else:
                    found_contacts = found_contacts.append(Campaign_list[Campaign_list['CRDNumber']!=''], ignore_index = True)
                    Campaign_list = Campaign_list[Campaign_list['CRDNumber']=='']
                num_remaining = len(Campaign_list)
                found = num_searched_on - num_remaining
                print 'Found %s on %s search.' % (found,header)
                for rField in returnFields:
                    del Campaign_list[rField]
    if 'CRD Provided by List' in headers:
        del Campaign_list['CRD Provided by List']
        review_path = review_contact_path(path)
        contacts_to_review.to_excel(review_path)
    found_cont_path=found_contact_path(path)
    found_contacts.to_excel(found_cont_path, index=False)
    Campaign_list.to_excel(path, index=False)
        
    ret_item = {'Next Step': 'FINRA Search','Found Path': found_cont_path
                    , 'SFDC_Found':len(found_contacts),'FINRA?':to_FINRA
                , 'Review Path':review_path}
    return ret_item

def CRDsearch(list_df, advisor_df, n, obj=None):
    '''
    If a column titled 'CRDNumber' is present in the 'to-be-searched' list,
    then the df from 'searchone' function is thrown here for the search against
    SFDC.
    '''
    
    list_df.fillna('')
##    list_df['CRDNumber'].astype(int)
    to_FINRA = True
    searchfields = ['CRDNumber']
    returnFields=['AccountId','SourceChannel','ContactID','Needs Info Updated?','BizDev Group']
    if obj!='BizDev Group':
        del returnFields[-1]
    headers = list_df.columns.values
    found_contacts = pd.DataFrame()
    for header in searchfields:
        if header in headers:
            n+=1
            j_headers=[header]
            for rf in returnFields:
                j_headers.append(rf)
            headerandIDs = advisor_df[j_headers]
            #headerandIDs = Advisor_list[keepCols]
            list_df = list_df.merge (headerandIDs, how='left', on = header)
            list_df = list_df.fillna('')
            found_contacts = found_contacts.append(list_df[list_df['ContactID']!=''], ignore_index = True)
            list_df = list_df[list_df['ContactID']=='']
            found = len(found_contacts)
            print 'Found %s on %s search.' % (found,header)
            for rField in returnFields:
                del list_df[rField]
            if list_df['CRDNumber'].count() == len(list_df) and len(list_df['CRDNumber'].nonzero()[0]) == len(list_df):
                to_FINRA = False
                list_df.rename(columns={'CRDNumber':'CRD Provided by List'},inplace=True)
            else:
                list_df.rename(columns={'CRDNumber':'CRD Provided by List'},inplace=True)
    
    return (found_contacts, list_df, n, found, to_FINRA)

    

def searchtwo(path, found_path, listType=None):
    '''
    Following the 'to-be-searched' list that had already be searched against
    SFDC, the remaining names that could not be identified in the database
    were sent to FINRA / SEC for CRD scrapping.

    After the scrapping, we re-search the SFDC database to attempt to find any
    additional contacts that were missed during the 'searchone' function.    
    '''
    
    FINRA_Found_list = pd.read_excel(path, sheetname=0)
    Advisor_list = pd.read_csv(AdvListPath,error_bad_lines=False,low_memory=False)
    headers = FINRA_Found_list.columns.values
    print '\nStep 7:\nSearching against SFDC following FINRA/SEC searches.'
    #remove unknown header columns from search - ricky added 3.21.2016
    keepCols = [c for c in FINRA_Found_list.columns if c.lower()[:7] != 'unknown']
    FINRA_Found_list = FINRA_Found_list[keepCols]
    
    #Empty blank cells
    FINRA_Found_list = FINRA_Found_list.fillna('')
    #--> check here for null values in searched fields, subset#
   
    searchfields = ['CRDNumber']
    returnFields=['AccountId','SourceChannel','ContactID','Needs Info Updated?', 'BizDev Group']
    if listType!='BizDev Group':
        del returnFields[-1]
    
    found_contacts = pd.DataFrame()

    FINRA_Found_list['CRDNumber'].astype(int)
    #IF LIST TYPE IS CONFERENCE
    n=0
    for header in searchfields:
        if header in headers:
            n+=1
            print 'Performing search #%s on %s' % (n,header)
            j_headers=[header]
            for rf in returnFields:
                j_headers.append(rf)
            headerandIDs = Advisor_list[j_headers]
            #headerandIDs = Advisor_list[keepCols]
            FINRA_Found_list = FINRA_Found_list.merge(headerandIDs, how='left', on = header)
            FINRA_Found_list = FINRA_Found_list.fillna('')
            found_contacts = found_contacts.append(FINRA_Found_list, ignore_index = True)
##            Campaign_list = Campaign_list[Campaign_list.ContactID=='']
            found = len(found_contacts['ContactID'].nonzero()[0])
            print 'Found %s on %s search.' % (found,header)
##            for rField in returnFields:
##                del Campaign_list[rField]
    
    df=pd.read_excel(found_path, sheetname=0)
    df=df.append(found_contacts)
    df.to_excel(found_path, index=False)
    FINRA_Found_list.to_excel(path, index=False)
    ret_item = {'Next Step': 'Upload Prep', 'Found in SFDC Search #2': found}
    return ret_item


def searchsec(path,found_path):
    '''
    Following the 'to-be-searched' list that had already be searched against
    SFDC, and attempted FINRA scraping, the remaining names that could not be
    scrapped are searched against the SEC database for CRD scrapping.
    database

    After the scrapping, we re-search the SFDC database to attempt to find any
    additional contacts that were missed during the 'searchone' function.    
    '''
    
    import datetime
    today = datetime.datetime.strftime(datetime.datetime.now(),'%m_%d_%Y')
    SECpath='T:/Shared/FS2 Business Operations/Python Search Program/SEC_Data/Individuals/processed_data/'+today+'/'
    if os.path.exists(SECpath)==False:
        print "Skipping SEC Search. Today's files could not be found in the listed directory."
        ret_item = {'Next Step': 'SFDC Search #2','SEC_Found':0}
        return ret_item

    print '\nStep 6:\nSearching against SEC Data.'
    Campaign_list = pd.read_excel(path, sheetname=0)
    headers = Campaign_list.columns.values
    #test_SECpath='C:/Users/rschools/Downloads/SEC_Data/processed_data/03_30_2016/'
    SECfiles = os.listdir(SECpath)
    found=0
    for sec in SECfiles:
        
        sec_df=pd.read_csv(SECpath+sec)
        sec_df.rename(columns={'indvlPK':'CRDNumber'},inplace=True)
        
        searchfields = ['LkupName']
        found_contacts = pd.DataFrame()

        n=0
        for header in searchfields:
            if header in headers:
                n+=1
            
                print 'Performing search #%s on %s for %s sec file' % (n,header, sec)
                headerandIDs = sec_df[[header,'CRDNumber']]
                Campaign_list = Campaign_list.merge (headerandIDs, how='left', on = header)
                Campaign_list = Campaign_list.fillna('')
                found_contacts = found_contacts.append(Campaign_list[Campaign_list['CRDNumber']!=''], ignore_index = True)
                Campaign_list = Campaign_list[Campaign_list.CRDNumber=='']
                if n > 1:
                    found =(len(found_contacts)-found)
                else:
                    found = len(found_contacts)
                print 'Found %s on %s search.' % (found,header)
                del Campaign_list['CRDNumber']

    df=pd.read_excel(found_path, sheetname=0)
    df=df.append(found_contacts)
    df.to_excel(found_path, index=False)
    Campaign_list.to_excel(path, index=False)
    ret_item = {'Next Step': 'SFDC Search #2','SEC_Found':found}
    return ret_item

##test_nocrd='C:/Users/rschools/Dropbox/Python Search Program/New Lists/Chicago Pre Attendee_nocrd.xlsx'
##test_found='C:/Users/rschools/Dropbox/Python Search Program/New Lists/Chicago Pre Attendee_foundcontacts.xlsx'
##
##test_search1='C:/Users/rschools/Dropbox/Python Search Program/New Lists/AMPF Update Rep List_ALPTest/AMPF Update Rep List_ALPTest.xlsx'
##if __name__=="__main__":
##    print searchsec('xyz', 'pdq')
##    searchone(test_search1, listType='Account')
