from ListManagement.utils.general import (
    shorten_fname_to_95chars, shutil, split_name
)

_DEST = '//sc12-fsphl-01/BulkImports/'

_sfdc_uploads = {
    'Campaign': {
        'sf_create': {
            'object': 'CampaignMember'
            , 'fields': ['ContactId', 'Status', 'CampaignId']
        }
        , 'sf_update': {
            'object': 'CampaignMember'
            , 'fields': ['ContactId', 'Status', 'CampaignId', 'ID']
        }

    },
    'BizDev Group': {
        'sf_create': {
            'object': 'Contact'
            , 'fields': ['Id', 'Biz_Dev_Group__c', 'Licences__c']
        }
        , 'sf_update': {
            'object': 'Contact'
            , 'fields': ['Id', 'Biz_Dev_Group__c', 'Licences__c']
        }
    }

}


class Uploader:
    def __init__(self, log):
        self.log = log

    def upload(self, _vars, sf):
        _vars.update_state()
        # self._handle_bulk([_vars.update, _vars.create])
        self._salesforce_upload(list_type=_vars.list_type, updates=[_vars.stay],
                                creates=[_vars.add, _vars.src_object_create], sf=sf)
        return _vars

    def _handle_bulk(self, items):
        for item in items:
            if item['bulk']:
                short_name = shorten_fname_to_95chars(split_name(item['path']))
                self.log.info('Dropping %s for bulk processing.' % short_name)
                shutil.copy(item['path'], _DEST + short_name)

    def _salesforce_upload(self, list_type, updates, creates, sf):
        for update in updates:
            if len(update['frame'].index) > 0:
                self.log.info('Updating {0} salesforce records for the {1} list.'.format(len(update['frame'].index),
                                                                                         list_type))
                sf.update_records(obj=_sfdc_uploads[list_type]['sf_update']['object'],
                                  fields=_sfdc_uploads[list_type]['sf_update']['fields'],
                                  upload_data=update['frame'].values.tolist())
        for create in creates:
            if len(create['frame'].index) > 0:
                self.log.info('Creating {0} salesforce records for the {1} list.'.format(len(create['frame'].index),
                                                                                         list_type))
                sf.create_records(obj=_sfdc_uploads[list_type]['sf_create']['object'],
                                  fields=_sfdc_uploads[list_type]['sf_create']['fields'],
                                  upload_data=create['frame'].values.tolist())
