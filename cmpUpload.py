import SQLForce
from cred import sfuser, sfpw, sf_token, username
import pandas as pd

def extract_pdValues(df_path):##,obj):
    df=pd.read_excel(df_path)
    df_values=df.values.tolist()
    df_headers=df.columns.values.tolist()
    del df
##    upload(df_headers,df_values,obj)
    cmpUpload(df_values)
    return {'Next Step': 'Send Email'}

##def headersCleanUp(headers,toRemove='ContactID'):
##    try:
##        headers.remove(toRemove)
##    except:
##        pass
##    return headers
##
##
##def upload(headers,list_ofValues, obj):
##    try:
##        session=initSession()
##        if obj=='Campaign':
##            cmpUpload(session,list_ofValues,obj)
##        elif obj=='BizDev Group':
##            headers=headersCleanUp(headers)
##            bdgUpload(session,headers,list_ofValues,obj)
##                
##
##def bdgUpload(session, headers, list_ofValues):
##    print '\nStep 10. Salesforce BizDev Group Upload.'
##    print 'Attempting to connect to SFDC for BDG upload.'
##    try:
##        session=initSession()
##        print 'Connection successful.'
##        print 'Attempting to update %s in the campaign.' % len(toUpdate)
##        session.update('Contact',headers,
##                       toUpdate)
##        
##            status='Success'
##        closeSession(session)
##    except:
##        status='Failed'
##        
##    finally:
##        print status
##        print 'Session and server closed.'
##        return status

def cmpUpload(lists_ofValues):
    print '\nStep 10. Salesforce Campaign Upload.'
    print 'Attempting to connect to SFDC for cmpMember upload.'
    try:
        session=initSession()
        print 'Connection successful.'
        sf_c_cmpMembers=currentMembers(session,lists_ofValues[0][2])
        toInsert, toUpdate =splitList(sf_c_cmpMembers,lists_ofValues)
        if len(toInsert)>0:
            print 'Attempting to insert %s into the campaign.' % (len(toInsert))
            session.insert('CampaignMember',['ContactId','Status','CampaignId'],
                               toInsert)
            status='Success'
            
        if len(toUpdate)>0:
            print 'Attempting to update %s into the campaign.' % (len(toUpdate))
            session.update('CampaignMember',['Status','CampaignId'],
                               toUpdate)
            status='Success'
        closeSession(session)
    except:
        status='Failed'
        
    finally:
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
    session=SQLForce.Session('Production',sfuser, sfpw, sf_token)
    return session



def closeSession(session):
    session.logout()
    SQLForce.SQLForceServer.killServer()



##for testing
##if __name__=='__main__':
##    testData=[['003E000000sasOaIAI','Needs Follow-Up','701E0000000bkmAIAQ'],
##              ['003E000001P0oQEIAZ','Needs Follow-Up','701E0000000bkmAIAQ']]
##    cmpPath='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/Attendee-List-6-6-2016/Attendee-List-6-6-2016_cmpUpload.xlsx'
##    status=extract_pdValues(cmpPath)
##    print 'Request status: %s' % status
