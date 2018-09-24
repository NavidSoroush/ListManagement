import sys

import sqlalchemy

from ListManagement.legacy.sf_adv_formatting import make_lookup_name, needs_update_flag
from ListManagement.utility import general as _ghelp
from ListManagement.utility.pandas_helper import pd


_query_fields = {
    'FirstName': 'First Name', 'LastName': 'Last Name', 'SFDC_Account_Name_Test__c': 'Account Name'
    , 'AccountId': 'AccountId', 'AMPF_MBR_ID__c': 'AMPF MBR ID', 'Office_Name__c': 'Office Name'
    , 'BizDev_Group__c': 'BizDev Group', 'Email': 'Email', 'MailingStreet': 'Mailing Address Line 1'
    , 'MailingCity': 'Mailing City', 'MailingState': 'Mailing State/Province'
    , 'MailingPostalCode': 'Mailing Zip/Postal Code', 'Phone': 'Phone', 'CRD_Number__c': 'CRD Number'
    , 'Id': 'ContactID', 'Rating__c': 'Rating', 'Products_Used__c': 'Products Used'
    , 'Licenses__c': 'Licenses', 'Source_Channel__c': 'SourceChannel'
    , 'Last_Meeting_Event__c': 'Last Meeting/Event', 'Last_Sales_Presentation_Date__c': 'Last SP'
    , 'Most_Recent_Sales_New__c': 'Most Recent Sale'
}

_query_where = "DST_Contact_Type__c = 'Single' and Name NOT LIKE '%/%'"


def run(path_name, logger):
    _dir, _name = _ghelp.os.path.split(path_name)
    _ghelp.auto_maintain(_dir, log=logger)

    # Declaring needed variables
    lkup_strings = ['First Name', 'Last Name', 'Account Name',
                    'Mailing State/Province', 'Mailing Zip/Postal Code']
    update_cols = ['Last Meeting/Event', 'Last SP', 'Most Recent Sale', ]
    rep_headers = ['LkupName', 'First Name', 'Last Name', 'Contact Name',
                   'Account', 'AccountId', 'AMPFMBRID', 'Office Name',
                   'BizDev Group', 'Email', 'Mailing Address 1',
                   'Mailing City', 'Mailing State', 'Mailing Zip', 'Phone',
                   'CRD', 'ContactID', 'Rating',
                   'Products Used', 'Licenses', 'SourceChannel',
                   'Last Meeting/Event', 'Last SP', 'Most Recent Sale', 'Needs Info Updated?']

    logger.info('Connecting to SQL database.')

    try:
        conn = sqlalchemy.create_engine('mssql+pyodbc://PRODDB-FSPHL-01/SalesForce Backups?driver=SQL+Server')
    except BaseException:
        logger.error('Failed to connect to SQL database.', exc_info=True)
        sys.exit()

    query_start = _ghelp.time.time()
    logger.info(' > Extracting data from SQL.')
    df = pd.read_sql_query(list_SQL, conn)
    logger.info(' > Preparing the file for use.')
    logger.debug('   > Making LookupName.')
    df.insert(0, 'LkupName', make_lookup_name(df, lkup_strings))
    logger.debug('   > Adding update flags.')
    df.insert(len(df.columns), 'Needs info updated?', needs_update_flag(df[df.columns[-3:]], update_cols, 180, 90))
    df.columns = rep_headers
    logger.info(' > Transformation complete. Saving to FS shared drive.')
    df.rename(columns={'CRD': 'CRDNumber'}, inplace=True)
    df = df[~df.CRDNumber.str.contains('[a-zA-Z]').fillna(False)]
    df.to_csv(path_name, header=True, index=False, encoding='utf-8')
    logger.info('Closing SQL connection.')
    query_end = _ghelp.time.time()
    # printing success and time it took to complete query and save
    logger.info("Saving complete. Query took: %s" % _ghelp.duration(query_start, query_end))
