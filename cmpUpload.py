import SQLForce
from cred import sfuser, sfpw, sf_token, username
import pandas as pd

def extract_pdValues(df_path):
    df=pd.read_excel(df_path)
    df_values=df.values.tolist()
    del df
    cmpUpload(df_values)
    return {'Next Step': 'Send Email'}


def cmpUpload(lists_ofValues):
    print '\nStep 10. Salesforce Campaign Upload.'
    print 'Attempting to connect to SFDC for cmpMember upload.'
    try:
        session=initSession()
        print 'Connection successful.'
        sf_c_cmpMembers=currentMembers(session,lists_ofValues[0][2])
        toInsert, toUpdate =splitList(sf_c_cmpMembers,lists_ofValues)
        if len(toInsert)>0:
            print 'Attempting to insert %s into the campaign.' % len(toInsert)
            session.insert('CampaignMember',['ContactId','Status','CampaignId'],
                           toInsert)
            status='Success'
            print '%s insert complete.'
            
        if len(toUpdate)>0:
            print 'Attempting to update %s in the campaign.' % len(toUpdate)
            session.update('CampaignMember',['Status','CampaignId'],
                           toUpdate)
            
            status='Success'
            print '%s update complete.' % status
    except:
        status='Failed'
        
    finally:
        closeSession(session)
        print status
        print 'Session and server closed.'
        return status



def currentMembers(session, cmpId):
    child_list=[]
    sql='SELECT ContactId, Status, Id FROM CampaignMember WHERE CampaignId="'+cmpId+'"'
    for rec in session.selectRecords(sql):
        child_list.append(rec.ContactId)
        child_list.append(rec.Status)
        child_list.append(rec.Id)
    return child_list



def splitList(id_inCmp, ids_fromSearch):
    insert=[i for i in ids_fromSearch if i[0] not in id_inCmp]
    update=[i for i in ids_fromSearch if i[0] in id_inCmp]
    if len(update)>0:
        update=cmpMbrId_for_contactId(update,id_inCmp)
    return insert, update



def cmpMbrId_for_contactId(updateList,cmpList):
    for up in range(len(updateList)):
        for u in range(len(updateList[up])):
            for l in range(len(cmpList)):
                if updateList[up][u]==cmpList[l]:
                    updateList[up][u]=str(cmpList[(l+2)])
                    break
            break
    return updateList



def initSession():
    session=SQLForce.Session('Production',sfuser,sfpw, sf_token)
    return session



def closeSession(session):
    session.logout()
    SQLForce.SQLForceServer.killServer()



##for testing
if __name__=='__main__':
##    testData=[['003E000000sasOaIAI','Needs Follow-Up','701E0000000bkmAIAQ'],
##              ['003E000001P0oQEIAZ','Needs Follow-Up','701E0000000bkmAIAQ']]
    cmpPath='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/Copy of Exhibitor Attendee List - 04-15-16/Copy of Exhibitor Attendee List - 04-15-16_cmpUpload.xlsx'
    status=extract_pdValues(cmpPath)
    print 'Request status: %s' % status
