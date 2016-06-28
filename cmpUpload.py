import SQLForce
from cred import sfuser, sfpw, sf_token, username
import pandas as pd
from parse_Files import path_toUpdate

colNums=[]

def extract_pdValues(df_path,obj):
    df=pd.read_excel(df_path)
    if obj=='BizDev Group':
        df.rename(columns={'BizDev Group':'BizDev_Group__c','Licenses':'Licenses__c'},inplace=True)
        df=df[['ContactID','BizDev_Group__c','Licenses__c']]
        colNums.append(df.columns.get_loc('BizDev_Group__c'))
        colNums.append(df.columns.get_loc('ContactID'))
        colNums.append(df.columns.get_loc('Licenses__c'))        
    df_values=df.values.tolist()
    df_headers=df.columns.values.tolist()

    
    if obj=='Campaign':
        paths, stats=cmpUpload(df_headers,df_values, obj)
    else:
        paths,stats=upload(df_headers,df_values,obj, colNums, df_path)

    return {'Next Step': 'Send Email',
            'BDG Remove': paths[0],
            'BDG Add': paths[1],
            'BDG Stay': paths[2],
            'Num Removing': stats[0],
            'Num Adding': stats[1],
            'Num Updating/Staying': stats[2]}

def headersCleanUp(headers,toRemove='ContactID'):
    headers.remove(toRemove)
    return headers

def remove(toRemove,objID):
    for to in toRemove:
        if to[1]==objID:
            to[1]=''
    return toRemove

def upload(headers,list_ofValues, obj, colNum=None, df_path=None):
    try:
        session=initSession()
        if obj=='Campaign':
            paths,stats=cmpUpload(session,list_ofValues, obj)
        elif obj=='BizDev Group':
            headers=headersCleanUp(headers)
            paths,stats=bdgUpload(session,headers,list_ofValues,obj, colNum, df_path)
    except Exception, e:
        print e
    return paths,stats
                

def bdgUpload(session, headers, list_ofValues, obj, colNum, df_path, remove_path=None, add_path=None, update_path=None, nAdd=0, nUp=0, nRe=0):
    print '\nStep 10. Salesforce BizDev Group Upload.'
    print 'Attempting to connect to SFDC for BDG upload.'
    try:
        print 'Connection successful.'
        print 'Getting current members.'
        sf_bdgMembers=currentMembers(session, list_ofValues[0][colNum[0]], obj)
        toInsert,toUpdate,toRemove=splitList(sf_bdgMembers,list_ofValues, obj, colNum[1])
        print 'Attempting to insert %s in the BizDev Group.' % len(toInsert)
        if len(toInsert)>0:
            df_add=pd.DataFrame.from_records(toInsert, columns=['ContactID','BizDevGroupID','Licenses'])
            add_path=path_toUpdate(df_path, 'toAdd')
            df_add.to_excel(add_path, index=False)
            
            session.update('Contact',['BizDev_Group__c','Licenses__c'],toInsert)
            nAdd=len(toInsert)
            status='Success'

        if len(toUpdate)>0:
            print 'Attempting to update Licenses for %s advisors staying in the BizDevGroup.' % len(toUpdate)
            df_update=pd.DataFrame.from_records(toUpdate, columns=['ContactID','BizDevGroupID','Licenses'])
            update_path=path_toUpdate(df_path, 'bdg_toStay')
            df_update.to_excel(update_path, index=False)
            nUp=len(toUpdate)

            session.update('Contact',['BizDev_Group__c','Licenses__c'],toUpdate)
            nUp=session.getenv('ROW_COUNT')
            status='Success'

        if len(toRemove)>0:
            print 'Attempting to remove %s from the BizDev Group.' % len(toRemove)
            df_remove=pd.DataFrame.from_records(toRemove, columns=['ContactID','Previous BizDevGroupID'])
            remove_path=path_toUpdate(df_path, 'toRemove')
            df_remove.to_excel(remove_path, index=False)
            
            toRemove=remove(toRemove,list_ofValues[0][colNum[0]])
            session.update('Contact',['BizDev_Group__c'],toRemove)
            nRe=len(toRemove)
            status='Success'
            
        closeSession(session)
    except Exception, e:
        print e
        status='Failed'
        
    finally:
        print status
        print 'Session and server closed.'

    return [remove_path, add_path, update_path], [nRe, nAdd, nUp]

def cmpUpload(session, lists_ofValues, obj,nAdd=0, nRe=0, nUp=0):
    print '\nStep 10. Salesforce Campaign Upload.'
    print 'Attempting to connect to SFDC for cmpMember upload.'
    try:
        print 'Connection successful.'      
        sf_c_cmpMembers=currentMembers(session,lists_ofValues[0][2], obj)
        toInsert, toUpdate, toRemove=splitList(sf_c_cmpMembers,lists_ofValues, obj)
        if len(toInsert)>0:
            print 'Attempting to insert %s into the campaign.' % (len(toInsert))
            session.insert('CampaignMember',['ContactId','Status','CampaignId'],
                               toInsert)
            nAdd=len(toInsert)
            status='Success'
            
        if len(toUpdate)>0:
            print 'Attempting to update %s into the campaign.' % (len(toUpdate))
            session.update('CampaignMember',['Status','CampaignId'],
                               toUpdate)
            nUp=len(toUpdate)
            status='Success'
        closeSession(session)
    except:
        status='Failed'
        
    finally:
        print status
        print 'Session and server closed.'
        return ['','',''],[nRe, nAdd, nUp]

def currentMembers(session, cmpId, obj):
    child_list=[]
    if obj=='Campaign':
        sql='SELECT ContactId, Status, Id FROM CampaignMember WHERE CampaignId="'+cmpId+'"'
        for rec in session.selectRecords(sql):
            child_list.append(rec.ContactId)
            child_list.append(rec.Status)
            child_list.append(rec.Id)
    elif obj=='BizDev Group':
        sql='SELECT Id, BizDev_Group__c FROM Contact WHERE BizDev_Group__c="'+cmpId+'"'
        for rec in session.selectRecords(sql):
            child_list.append(rec.Id)
            child_list.append(rec.BizDev_Group__c)
    return child_list



def splitList(id_inCmp, ids_fromSearch, obj, col=None,remove=None, newList=[]):
    if obj=='Campaign':
        insert=[i for i in ids_fromSearch if i[0] not in id_inCmp]
        update=[i for i in ids_fromSearch if i[0] in id_inCmp]
        if len(update)>0:
            update=cmpMbrId_for_contactId(update,id_inCmp)
    else:
        insert=[i for i in ids_fromSearch if i[col] not in id_inCmp]
        update=[i for i in ids_fromSearch if i[col] in id_inCmp]
        if len(id_inCmp)>0:
            remove=[]
            newList=[id_inCmp[i:i+2] for i in range(0,len(id_inCmp),2)]
            for srch in ids_fromSearch:
                for mbr in newList:
                    if mbr[0] not in srch:
                        remove.append(mbr)
                        newList.remove(mbr)
                        break
            for up in update: 
                for re in remove:
                    if up[:-1] == re:
                        remove.remove(re)                    
        
    return (insert, update, remove)



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
##    cmpPath='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/BDG Test List/BDG Test List_toUpdate.xlsx'
##    path='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/PAG All Advisors 6.3.16 New May 16/PAG All Advisors 6.3.16 New May 16_bdgUpdate.xlsx'
##    obj='BizDev Group'
##    status={}
##    status=extract_pdValues(path,obj)
##    print 'Request status: %s' % status
