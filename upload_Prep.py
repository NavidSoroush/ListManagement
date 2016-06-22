import pandas as pd
import datetime
import re

yyyymm = datetime.datetime.strftime(datetime.datetime.now(),'%Y%m')

acceptedColumns=['CRDNumber','FirstName','LastName','AccountId'
                 ,'MailingStreet','MailingCity','MailingState','MailingPostalCode'
                 ,'SourceChannel','Email','Website','AUM','GDC','Fax'
                 ,'HomePhone','MobilePhone','Phone','toAlternatives','toAdvisory']

necessaryColumns=acceptedColumns[:8]

bdg_acceptedColumns=['ContactID','BizDev Group', 'Licenses']

cmp_acceptedColumns=['ContactID','CampaignId','Status']

##phoneNumbers=[ '1554-568-889525'
##              , '6587453214545'
##              , '(123)469-7891454'
##              , '012.321.4587'
##              ,'1425665873']

def sourceChannel(path, recordName, objId, obj, aid=None):
    move_toBulk=False
    if obj=='Campaign':
        print '\nStep 9. Data Prep (will be performed twice)'
    elif obj=='BizDev Group':
        print '\nStep 9. Data Prep (will be performed thrice)'
    else:
        print '\nStep 9. Data Prep'
    list_df=pd.read_excel(path, sheetname=0)
    
    
    if obj=='Account':
        sc_toAdd='firm_'+recordName+'_'+yyyymm
        list_df=drop_unneedColumns(list_df,obj)
        new_contactDF=list_df[list_df['AccountId'].isnull()]
        crd_SC=new_contactDF[['CRDNumber','SourceChannel']]
        to_create=len(new_contactDF.index)
        list_df.loc[list_df['AccountId'].isnull(),'AccountId']=objId
        list_df.loc[list_df['AccountId'].notnull(),'AccountId']=objId
        list_df.loc[list_df['SourceChannel'].isnull(),'SourceChannel']=sc_toAdd
    
        list_df=list_df.merge(crd_SC, how='left', on='CRDNumber')
        del list_df['SourceChannel_y']
        list_df.rename(columns={'SourceChannel_x':'SourceChannel'},inplace=True)
        move_toBulk=determineMovetoBulkProcessing(list_df) 
        del crd_SC
        del new_contactDF
        
    elif obj=='Campaign':
        sc_toAdd='conference_'+recordName+'_'+yyyymm
        if 'toCreate' in path:
            list_df=drop_unneedColumns(list_df,obj)
            to_create=0
            list_df.loc[list_df['AccountId'].isnull(),'AccountId']=objId
            list_df.loc[list_df['SourceChannel'].isnull(),'SourceChannel']=sc_toAdd
            move_toBulk=determineMovetoBulkProcessing(list_df) 
        else:
            list_df=drop_unneedColumns(list_df,obj,create=False)
            to_create=0
            list_df['CampaignId']=objId

    elif obj=='BizDev Group':
        sc_toAdd='bdg_'+recordName+'_'+yyyymm
        if 'toCreate' in path:
            list_df=drop_unneedColumns(list_df,obj)
            to_create=len(list_df.index)
            list_df.loc[list_df['AccountId'].isnull(),'AccountId']=aid
            list_df.loc[list_df['SourceChannel'].isnull(),'SourceChannel']=sc_toAdd
        elif 'bdgUpdate' in path:
            list_df=drop_unneedColumns(list_df, obj, ac=bdg_acceptedColumns)
            to_create=0
            list_df['BizDev Group']=objId
        else:
            list_df=drop_unneedColumns(list_df, obj)
            to_create=0
            list_df['AccountId']=aid
            list_df['BizDev Group']=objId

        move_toBulk=determineMovetoBulkProcessing(list_df)
        move_toBulk=False


##Clean up phone and fax numbers (ie. format for SFDC upload)
    if 'Phone' in list_df.columns.values:
        try:
            list_df['Phone'].astype(str)
            numRows=len(list_df.index)
            for index, row in list_df.iterrows():
                list_df.loc[index,'Phone']=clean_phoneNumber(row['Phone'])
        except:
            print "Can't clean up phone numbers due to %s." % (Exception)

    if 'Fax' in list_df.columns.values:
        try:
            list_df['Fax'].astype(str)
            numRows=len(list_df.index)
            for index, row in list_df.iterrows():
                list_df.loc[index,'Fax']=clean_phoneNumber(row['Fax'])
        except:
            print "Can't clean up fax numbers due to %s." % (Exception)
            
    list_df.to_excel(path,index=False)
    return {'Next Step': 'Parse Out Advisors Updates'
            ,'Create': to_create
            ,'Move To Bulk':move_toBulk}


def determineMovetoBulkProcessing(df):
    headers=df.columns.values
    for ac in necessaryColumns:
        if ac not in headers:
            move=False
            break
        else:
            move=True
    if len(df.index) == 0:
        move = False
    return move


def drop_unneedColumns(dataframe, obj, ac=acceptedColumns, create=True):
    headers=dataframe.columns.values
    if obj!='Campaign' or create==True:
        for header in headers:
            if header not in ac:
                del dataframe[header]
        return dataframe
    else:
        for header in headers:
            if header not in cmp_acceptedColumns:
                del dataframe[header]
        return dataframe

def clean_phoneNumber(pn):
    phone=re.sub(r'\D','',str(pn))
    phone=phone.lstrip('1')
    if len(phone)>10:
        return '({}) {}-{}x{}'.format(phone[0:3],phone[3:6],phone[6:10],phone[10:])
      
    elif len(phone)<10:
##        return 'notValid: Phone len is %s. Must be len of 10 or more. {}'.format(phone) %(len(phone))
        return ''
    
    else:
        return '({}) {}-{}'.format(phone[0:3],phone[3:6],phone[6:])
        

##if __name__=='__main__':
##    path='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/BDG Test List PAG/BDG Test List PAG_bdgUpdate.xlsx'
##    sourceChannel(path, "Ricky's Test Group", 'a0vE00000069dt3IAA','BizDev Group','001E000000DueknIAB') 
##    for p in phoneNumbers:
##        print clean_phoneNumber(p)
