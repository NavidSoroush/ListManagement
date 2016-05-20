import pandas as pd

statsPath='T:/Shared/FS2 Business Operations/Python Search Program/Search Program Stats2.xlsx'

def initStatsFile():
    df=pd.read_excel(statsPath)
    return df

def saveStatsFile(df):
    df.to_excel(statsPath,index=False)

def newstatline(value_dict):
    df2 = pd.DataFrame(value_dict.values(),index=value_dict.keys())
    df2 = df2.transpose()
    return df2
 
def recordStats(values):
    df=initStatsFile()
    print '\nStep 11. Recording stats from processing.'
    df2 = newstatline(values)
##    print df2
    df = df.append(df2, ignore_index=True)
    saveStatsFile(df)
    del df
    del df2
    return {'Next Step': 'Done.'}


##for testing
##statsData={'Received Date': '1/1/2016', 'CRD Found Not in SFDC': 3, 'File Type': 'Campaign', 'Last Search Date': '2016-04-18 15:20:30', 'Created By': 'Ricky Schools', 'Match Rate': 0, 'Received From': u'Ricky Schools', 'Creating': 3, 'Advisors w/CID': 62, 'File Name': u'campaign_list_test_ALM.xlsx', 'Processing Time': '1 minute', 'Advisors w/CID old Contact Info': 0, 'Unable to Find': 32, 'Advisors on List': 94}
##recordStats(statsData)
##
##tatsData)

