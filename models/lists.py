import datetime as _dt
import enum

from pandas import DataFrame

from ListManagement.utility.general import create_path_name
from ListManagement.utility.pandas_helper import read_df

_return_fields = ['CRDNumber', 'AccountId', 'SourceChannel',
                  'ContactID', 'Needs Info Updated?', 'BizDev Group']


class ListBase(object):
    # List states
    class States(enum.Enum):
        pending = enum.auto()
        started = enum.auto()
        profiling = enum.auto()
        header_prediction = enum.auto()
        standardization = enum.auto()
        search_one = enum.auto()
        finra_scrape = enum.auto()
        search_two = enum.auto()
        crud = enum.auto()
        file_parsing = enum.auto()
        sfdc_upload = enum.auto()
        record_stats = enum.auto()
        done = 0
        error = -1

    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.state = self.States.pending.value
        self.search_finra = True
        self.crd_search = False
        self.bulk_processing = False

        # file path starting places
        self.sfdc_base_path = None
        self.list_base_path = kwargs['file_path']
        self.file_name = kwargs['file_name']
        self.extension = kwargs['extension']

        # All potential data frames
        self.list_source = {'frame': read_df(self.list_base_path),
                            'path': self.list_base_path[:-len(self.extension)] + '.xlsx'}
        self.sfdc_target = {'frame': DataFrame(), 'path': None}
        self.found = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], '_foundcontacts')}
        self.create = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], 'to_create')}
        self.update = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], 'to_update')}
        self.remove = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], 'to_remove')}
        self.stay = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], 'to_stay')}
        self.finra_found = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], '_finrasec_found')}
        self.finra_ambiguous = {'frame': DataFrame(),
                                'path': create_path_name(self.list_source['path'], '_FINRA_ambiguous')}
        self.no_crd = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], '_nocrd')}
        self.review = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], '_review_contacts')}
        self.research = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], '_research')}
        self.src_object_upload = {'frame': DataFrame(),
                                  'path': create_path_name(self.list_source['path'], '_sf_update')}
        self.src_object_create = {'frame': DataFrame(),
                                  'path': create_path_name(self.list_source['path'], '_sf_create')}
        self.no_update = {'frame': DataFrame(), 'path': create_path_name(self.list_source['path'], '_no_updates')}
        self.current_members = {'frame': DataFrame(),
                                'path': create_path_name(self.list_source['path'], '_current_members')}

        # Salesforce metadata
        self.list_type = kwargs['list_type']
        self.object_id = kwargs['object_id']
        self.object_name = kwargs['object_name']
        self.list_id = kwargs['list_id']
        self.attachment_id = kwargs['attachment_id']
        self.owner_id = kwargs['owner_id']

        self.account_name = kwargs['account_name'] if 'account_name' in kwargs else None
        self.account_id = kwargs['account_id'] if 'account_id' in kwargs else None
        self.event_start_date = kwargs['event_start'] if 'event_start' in kwargs else None
        self.pre_or_post = kwargs['pre_or_post'] if 'pre_or_post' in kwargs else None
        self.source_channel = self.list_type + '_' + self.object_name + '_' + _dt.date.today().strftime('%Y_%m')
        self.campaign_member_status = 'Needs Follow-Up' if self.pre_or_post == 'Post' else 'Invited'

        # Requestor metadata
        self.requested_by = kwargs['requested_by']
        self.requested_by_email = kwargs['requested_by_email']
        self.requested_timestamp = kwargs['received_date']

        # Profiling attributes
        self.total_records = len(self.list_source['frame'].index)
        self.found_records = 0
        self.updating_records = 0
        self.src_object_upload_records = 0
        self.create_records = 0
        self.remove_records = 0
        self.no_update_records = 0
        self.need_research = 0
        self.match_rate = 0.0
        self.search_found = dict()

        # Base search & return fields
        self.search_on = ['CRDNumber', 'Email', 'AMPFMBRID']
        self.return_fields = _return_fields if self.list_type != 'BizDev Group' else _return_fields[:-1]

        # process_attributes
        self.process_start = _dt.datetime.utcnow()
        self.process_end = None

    def update_statistics(self):
        self.found_records = len(self.found['frame'].index)
        self.updating_records = len(self.update['frame'].index)
        self.src_object_upload_records = len(self.src_object_upload['frame'].index)
        self.create_records = len(self.create['frame'].index)
        self.remove_records = len(self.remove['frame'].index)
        self.no_update_records = len(self.no_update['frame'].index)
        self.need_research = self.total_records - self.found_records
        self.match_rate = self.found_records / float(self.total_records)
