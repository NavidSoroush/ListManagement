#importing the necessary libraries and files to complete the sql request
#and save the SFDC file for the list program.
import pypyodbc
import pandas as pd
import datetime
from datetime import date, timedelta
import numpy as np
import sys
import os
from sql_Query_String import list_SQL
from pd_SFDC_Format_Functions import shortenData, lkupName, needsUpdate, cleanDates,date_for_move
from cred import username, password
from pyEmailComplete import sfdcBatchComplete
import logging, logging.handlers


def run():
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)


        #Declaring needed variables
        svr = 'PPHL-PRODDB-1'
        ##svr='PRODDB-FSPHL-01'
        db = 'SalesForce_Backups'
        tcon='yes'
        uid = username
        pw = password
        lkup_strings = ['first name','last name','account name','mailing state/province','mailing zip/postal code']
        updateCols = ['last meeting or call','chg date - email','chg date - mailing address','chg date - phone','chg date - broker dealer']
        repHeaders = ['LkupName','First Name', 'Last Name', 'Contact Name','Account', 'AccountId', 'AMPF MBR ID', 'Office Name',
                      'BizDev Group', 'Email', 'Mailing Address 1', 'Mailing City', 'Mailing State',
                      'Mailing Zip', 'Phone', 'CRD', 'ContactID', 'Last Meeting/Event', 'Rating', 'Products Used',
                      'Licenses','SourceChannel','Last Meeting or Call','Chg Date - Email','Chg Date - Mailing Address','Chg Date - Phone',
                      'Chg Date - Broker Dealer','Needs Info Updated?']

        #Setting save path
        ##dropbPath = 'C:/Users/'+ uid +'/Dropbox/Search Program/Salesforce Data Files/'
        savePath2 = 'T:/Shared/FS2 Business Operations/Search Program/Salesforce Data Files/'
        name = 'SFDC Advisor List as of '
        save_d = format(datetime.datetime.now() ,'%m-%d-%y')
        ext = '.csv'
        ##filename = dropbPath+name+save_d+ext
        filen2=savePath2+name+save_d+ext
        tnow = datetime.datetime.now()
        numFiles = len([f for f in os.listdir(savePath2)if os.path.isfile(os.path.join(savePath2,f))])


        if tnow.hour < 11 and numFiles > 0:
                move_d = 'Y:/Business_Intelligence_Analytics/Lists - Archives/Search Program - SFDC Downloaded Files/'
                date_for_move(savePath2,move_d)
                

        logger.info('Connecting to SQL database.')
        #Starting connection to sql server

        try:
                conn = pypyodbc.connect(driver='{SQL Server}',host=svr,server=svr,trusted_connection=tcon,user=uid,password=pw)
        except (SystemExit,KeyboardInterrupt):
                raise
                sys.exit()
        except Exception, e:
                logger.error('Failed to connect to SQL database.', exc_info=True)
                sys.exit()

        #caching query start time
        qStart = datetime.datetime.now()

        logger.info('Preparing the file for use...')
        #reading data into dataframe, inserting columns
        #saving file, and closing sql connection
        df = pd.read_sql_query(list_SQL,conn)
        df.insert(0,'LkupName',lkupName(df,lkup_strings))
        df.insert(len(df.columns),'Needs info updated?',needsUpdate(df[df.columns[-5:]],updateCols ,180))
        ##df['contact id']=df['contact id']+'-'+df['Needs info updated?']
        df.columns = repHeaders
        ##logger.info('Saving to Dropbox.')
        ##df.to_csv(filename,header=True, index=False,encoding='utf-8')
        logger.info('Saving to FS shared drive.')
        df.rename(columns={'CRD':'CRDNumber'},inplace=True)
        df.to_csv(filen2,header=True, index=False,encoding='utf-8')
        logger.info('Closing SQL connection....')
        conn.close()

        #caching query end time, and returning how long it took to save.
        qEnd = datetime.datetime.now()
        qTime = qEnd - qStart


        #printing success and time it took to complete query and save
        #print "Save successful."
        logger.info("Saving complete. Query took: " + str(qTime.seconds/60) + ' minutes and '+ str(qTime.seconds%60) + ' seconds.')
        #logger.info('SQL query is a ', sfdcBatchComplete())

if __name__=='__main__':
        run()
