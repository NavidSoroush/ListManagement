import pandas as pd
from functions import splitname

##define necessary variables


def path_toUpdate(path,userString):
    fname=splitname(path)
    rootpath=path[:len(path)-len(fname)]
    fname=fname[:-19]+'_'+userString+'.xlsx'
    newPath=rootpath+fname
    return newPath

def parseList(path,listType=None,preORpost=None, bdgID=None, accId=None):
    cmpUpload=None
    toCreate=None
    noUpdate=None
    toUpdate=None
    num_cmpUpload=0
    num_toCreate=0
    num_noUpdate=0
    num_toUpdate=0
    cmpStatus=None
    noUpdate_path=None
    update_path=None
    toCreate_path=None
    cmpUpload_path=None
    print '\nStep 8. List parsing based on list type.'
    list_df=pd.read_excel(path)
    if listType=='Campaign':
        if preORpost=='Post':
##            cmpStatus='Attended'
            cmpStatus='Needs Follow-Up'
        else:
            cmpStatus='Invited'

        toCreate_path=path_toUpdate(path,'cmp_toCreate')
        cmpUpload_path=path_toUpdate(path,'cmpUpload')
        
        cmpUpload=list_df[list_df['AccountId'].notnull()]
        toCreate=list_df[list_df['AccountId'].isnull()]

        num_cmpUpload=len(cmpUpload.index)
        num_toCreate=len(toCreate.index)

        cmpUpload['Status']=cmpStatus

        toCreate.to_excel(toCreate_path, index=False)
        cmpUpload.to_excel(cmpUpload_path, index=False)
        
    elif listType=='Account':
        noUpdate_path=path_toUpdate(path,'noUpdates')
        update_path=path_toUpdate(path,'toUpdate')
        
        noUpdate=list_df[list_df['Needs Info Updated?']=='N']
        toUpdate=list_df[list_df['Needs Info Updated?']!='N']

        num_noUpdate=len(noUpdate.index)
        num_toUpdate=len(toUpdate.index)

        noUpdate.to_excel(noUpdate_path, index=False)
        toUpdate.to_excel(update_path, index=False)

    elif listType=='BizDev Group':
        noUpdate_path=path_toUpdate(path,'noUpdates')
        update_path=path_toUpdate(path,'toUpdate')
##Need to evaluate if the advisor is in the bizdev group
##And if they are assigned to the right BD. If not then they get updated.
##If they are in the BDG and Account is correct, then we can evaluate
##If the Needs Info Update field is checked or not.
  
        noUpdate=list_df[list_df['BizDev Group']==bdgId and list_df['AccountId']==accId and list_df['Needs Info Updated?']=='N']
        toUpdate=list_df[list_df['BizDev Group']!=bdgId or list_df['AccountId']!=accId or list_df['Needs Info Updated?']!='N']

        num_noUpdate=len(noUpdate.index)
        num_toUpdate=len(toUpdate.index)

        noUpdate.to_excel(noUpdate_path, index=False)
        toUpdate.to_excel(update_path, index=False)

    ret_item = {'Next Step': 'Data prep.'
                ,'No Update Path': noUpdate_path
                ,'Update Path': update_path
                ,'Num To Update': num_toUpdate
                ,'Num Not Updating':num_noUpdate
                ,'Campaign to Create':toCreate_path
                ,'Campaign Upload':cmpUpload_path
                ,'Num to Create Cmp':num_toCreate
                ,'Num Campaign Upload':num_cmpUpload
                ,'Assigned Cmp Status': cmpStatus}
    return ret_item
        
        
