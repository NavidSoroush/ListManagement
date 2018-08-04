import sys

import sqlalchemy

try:
    from ListManagement.legacy.sf_adv_query import list_SQL
    from ListManagement.legacy.sf_adv_formatting import make_lookup_name, needs_update_flag
    from ListManagement.utility import auto_maintain, os, duration, time
    from ListManagement.utility.pandas_helper import pd
except:
    from legacy.sf_adv_query import list_SQL
    from legacy.sf_adv_formatting import make_lookup_name, needs_update_flag
    from utility import auto_maintain, os, duration, time
    from utility.pandas_helper import pd


def run(path_name, logger):
    _dir, _name = os.path.split(path_name)
    auto_maintain(_dir, log=logger)

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

    query_start = time.time()
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
    query_end = time.time()
    # printing success and time it took to complete query and save
    logger.info("Saving complete. Query took: %s" % duration(query_start, query_end))
