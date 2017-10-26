import sys
import datetime
import logging
import logging.handlers

import sqlalchemy
import pandas as pd

try:
    from ListManagement.legacy.sf_adv_query import list_SQL
    from ListManagement.legacy.sf_adv_formatting import lkupName, needsUpdate
except:
    from legacy.sf_adv_query import list_SQL
    from legacy.sf_adv_formatting import lkupName, needsUpdate


def run(path_name):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

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

    query_start = datetime.datetime.now()
    logger.info('Preparing the file for use..')
    df = pd.read_sql_query(list_SQL, conn)
    df.insert(0, 'LkupName', lkupName(df, lkup_strings))
    df.insert(len(df.columns), 'Needs info updated?', needsUpdate(df[df.columns[-3:]], update_cols, 180, 90))
    df.columns = rep_headers
    logger.info('Saving to FS shared drive.')
    df.rename(columns={'CRD': 'CRDNumber'}, inplace=True)
    df = df[~df.CRDNumber.str.contains('[a-zA-Z]').fillna(False)]
    df.to_csv(path_name, header=True, index=False, encoding='utf-8')
    logger.info('Closing SQL connection....')
    query_end = datetime.datetime.now()
    query_time = query_end - query_start
    # printing success and time it took to complete query and save
    # print "Save successful."
    logger.info("Saving complete. Query took: " + str(query_time.min / 60) + ' minutes and ' + str(
        query_time.seconds % 60) + ' seconds.')
    # # logger.info('SQL query is a ', sfdcBatchComplete())

