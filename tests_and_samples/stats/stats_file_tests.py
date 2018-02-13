from ListManagement.stats.record_stats import record_processing_stats

# raw data from dictionary file from logs
data = """
Lists_Data:'An upload list has been added to Kestra 2018 Ascend Conference with 2/5/2018 by Max Charles\r\nCampaign Link: https://fsinvestments.my.salesforce.com/7010L000000fPFtQAM\r\nAttachment Link: https://fsinvestments.my.salesforce.com/00P0L00000kZFnVUAW\r\nList Link: https://fsinvestments.my.salesforce.com/a310L00000qNoMQQA0'
,Object:Campaign
,Record Name:Kestra 2018 Ascend Conference with 2/5/2018
,Sender Email:max.charles@fsinvestments.com
,Sender Name:Max Charles
,Received Date:02/01/2018 19:16:19
,File Path:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16.xlsx
,Campaign Start Date:2018-02-05 00:00:00
,Next Step:Send Email
,Found Path:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_foundcontacts.xlsx
,ObjectId:7010L000000fPFtQAM
,Pre_or_Post:Post
,process_start:2018-02-13 11:18:37
,CmpAccountName:Kestra Financial, Inc.
,CmpAccountID:001E000000DuekyIAB
,Found in SFDC Search #2:195
,Num Adding:
,Num Removing:
,Num Updating/Staying:
,Review Path:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_review_contacts.xlsx
,SFDC Session:<ListManagement.sf.sf_wrapper.SFPlatform object at 0x000000000A938668>
,AttachmentId:00P0L00000kZFnVUAW
,ListObjId:a310L00000qNoMQQA0
,ExtensionType:.xlsx
,Total Records:514
,Headers:['Account' 'FullName' 'Email' 'MailingState' 'MailingCity']
,SFDC_Found:174
,FINRA?:True
,to_create_path:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_foundcontactscmp_to_create.xlsx
,No CRD:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_nocrd.xlsx
,FINRA_SEC Found:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_finrasec_found.xlsx
,FINRA_Found:22
,FINRA Ambiguous:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_FINRA_ambiguous.xlsx
,SEC_Found:0
,cmp_upload:None
,to_create:None
,to_update:None
,bdg_update:None
,no_update:None
,n_cmp_upload:195
,n_to_create:0
,n_to_update:0
,n_bdg_update:0
,n_no_update:0
,cmp_status:Needs Follow-Up
,no_update_path:None
,update_path:None
,cmp_upload_path:T:/Shared/FS2 Business Operations/Python Search Program/New Lists/7010L000000fPFtQAM\Copy of Invitees--Registrants 1_16/Copy of Invitees--Registrants 1_16_foundcontactscmp_upload.xlsx
,bdg_update_path:None
,Create:0
,Move To Bulk:False
,BDG Remove:
,BDG Add:
,BDG Stay:
,Current Members:
"""

# transform data string into a list of values.
data = [x.replace('\n', '').replace('\r', '') for x in data.split(',')]
new_dict = {}

# for each item, add it to a 'new_data' dict to test record_processing_stats format.
for item in data:
    tmp = item.split(':')
    try:
        tmp_val = int(':'.join(tmp[1:]))
        new_dict[tmp[0]] = tmp_val
    except ValueError:
        pass

# print the constructed dictionary to ensure dict got constructed appropriately.
print(new_dict)

# test running processing stats, do not add data to file/dataframe.
# using only to test the output/creation of the dataframe from a dictionary
print(record_processing_stats(new_dict, save=False))

