import datetime as _dt
import enum


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
        self.list_df = None
        self.sfdc_target_df = None
        self.found_df = None
        self.create_df = None
        self.update_df = None
        self.remove_df = None
        self.stay_df = None
        self.finra_found_df = None
        self.finra_ambiguous_df = None
        self.no_crd_df = None
        self.review_df = None
        self.research_df = None
        self.src_object_upload_df = None
        self.src_object_create_df = None
        self.no_update_df = None
        self.current_members_df = None

        # Output file paths
        self.found_path = None
        self.create_path = None
        self.update_path = None
        self.remove_path = None
        self.stay_path = None
        self.finra_found_path = None
        self.finra_ambiguous_path = None
        self.no_crd_path = None
        self.review_path = None
        self.research_path = None
        self.src_object_upload_path = None
        self.src_object_create_path = None
        self.no_update_path = None
        self.current_members_path = None

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
        self.source_channel = None
        self.campaign_member_status = None

        # Requestor metadata
        self.requested_by = kwargs['requested_by']
        self.requested_by_email = kwargs['requested_by_email']
        self.requested_timestamp = kwargs['received_date']

        # Profiling attributes
        self.total_records = 0
        self.found_records = 0
        self.updating_records = 0
        self.src_object_upload_records = 0
        self.create_records = 0
        self.remove_records = 0
        self.no_update_records = 0
        self.need_research = 0
        self.search_found = dict()

        # Base search & return fields
        self.search_on = ['CRDNumber', 'Email', 'AMPFMBRID']
        self.return_fields = ['CRDNumber', 'AccountId', 'SourceChannel',
                              'ContactID', 'Needs Info Updated?', 'BizDev Group']

        # process_attributes
        self.process_start = _dt.datetime.utcnow()
        self.process_end = None
