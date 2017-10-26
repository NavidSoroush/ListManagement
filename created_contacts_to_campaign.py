import pandas as pd
from sqlalchemy import create_engine

from cred import sfuser, sfpw, sf_token
try:
    from ListManagement.utility.log_helper import ListManagementLogger
    from ListManagement.sf.sf_wrapper import SFPlatform
except:
    from utility.log_helper import ListManagementLogger
    from sf.sf_wrapper import SFPlatform

log = ListManagementLogger().logger
log.info('Starting conference creation contact processing.')
log.info('Initializing variables and objects.')
sfdc = SFPlatform(user=sfuser, pw=sfpw, token=sf_token, log=log)
engine = create_engine('mssql+pyodbc://DPHL-PROPSCORE/ListManagement?driver=SQL+Server')
sql = "SELECT ObjId, SourceChannel, Status FROM [dbo].[ConferenceCreation] WHERE AddedToCampaign=0"

log.info('Reading data from ListManagement database.')
data = pd.read_sql(sql=sql, con=engine).values

if len(data) < 1:
    log.info('There are no new contacts that need to be associated with a campaign. Trying again tomorrow morning.')
else:
    soql = "SELECT Id, Source_Channel__c FROM Contact WHERE Source_Channel__c IN ('%s')" % "','".join([x[1]
                                                                                                       for x in data])
    log.info('Grabbing data, based on Source_Channel__c, from SFDC.')
    result = sfdc.session.selectRecords(soql)

    log.info('Creating data mappings for SFDC campaign upload.')
    mappings = {x[1]: [] for x in data}
    for rec in result:
        for x in data:
            if rec.Source_Channel__c == x[1]:
                mappings[x[1]].append([rec.Id, x[2], x[0]])

    log.info('Attempting to associate new contacts to the campaign related to the list request. ')
    messages = []
    for k, v in mappings.iteritems():
        if len(v) > 0:
            log.info(
                'Creating %s campaign member records to %s campaign id with a source channel of %s.' % (len(v), v[0][2],
                                                                                                        k))
            sfdc.create_records(obj='CampaignMember', fields=['ContactId', 'Status', 'CampaignId'], upload_data=v)
            sql = "UPDATE [dbo].[ConferenceCreation] SET AddedToCampaign=1 WHERE SourceChannel='%s'" % k
            engine.execute(sql)

sfdc.close_session()
engine.dispose()
