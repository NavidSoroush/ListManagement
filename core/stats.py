import os

_list_stats_cols = ['Id', 'Status__c', 'Advisors_on_List__c', 'Contacts_Added_to_Related_Record__c',
                    'Contacts_Created__c', 'Contacts_Found_in_SF__c', 'Contacts_Not_Found__c',
                    'Contacts_to_Research__c', 'Contacts_Updated__c', 'Match_Rate__c', 'List_Process_Completed_At__c',
                    'Processed_By__c']


class ProcessingStats:
    def __init__(self, log):
        self.log = log

    def record(self, item, sfdc):
        item.update_state()
        item.record_end_time()
        _list_stats = [item.list_id, 'Process Completed', item.total_records, item.add_records,
                       item.create_records, item.found_records, item.need_research,
                       item.need_research, item.updating_records, item.match_rate * 100, item.process_end.isoformat(),
                       os.environ['SFUSERID']]
        sfdc.update_records(obj='List__c', fields=_list_stats_cols, upload_data=[_list_stats])
