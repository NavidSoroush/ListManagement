from ListManagement.utils.pandas_helper import crud


def _bdg_split(frame):
    frame['Licenses'] = frame['Licenses'].astype(str)
    frame = frame[(frame['Licenses'].str.contains('Series 7')) | (frame['Licenses'].str.contains('Series 22'))]
    return frame


def _campaign_split(frame):
    return frame


_switcher = {
    'Campaign': lambda df: _campaign_split(df),
    'BizDev Group': lambda df: _bdg_split(df)
}

_query_map = {
    'Campaign': {
        'object': 'CampaignMember'
        , 'fields': ['ContactId', 'Status', 'CampaignId', 'Id']
        , 'rename': None
        , 'where': "CampaignId='{0}'"
    },
    'BizDev Group': {
        'object': 'Contact'
        , 'fields': ['Id', 'BizDev_Group__c', 'Licenses__c']
        , 'rename': {'Id': 'ContactId'}
        , 'where': "BizDev_Group__c ='{0}'"
    }
}


class Parser:
    def __init__(self, log):
        self.log = log

    def split_found_into_actions(self, _vars, sf):
        _vars.update_state()
        _vars.no_update['frame'], _vars.update['frame'], _vars.create['frame'] = self._split_found(_vars.found['frame'])
        if _vars.list_type in _switcher:
            _vars.src_object_upload['frame'] = _switcher[_vars.list_type](
                df=_vars.found['frame'][_vars.found['frame']['action_flag'] == 'found'])
            _vars = self._split_existing_members(_vars, sf)
        self.log.info('Successfully split the list request into actionable chunks.')
        return _vars

    @staticmethod
    def _split_found(frame):
        if len(frame.index) > 0:
            no_update = frame[(frame['action_flag'] == 'found') & (frame['Needs Info Updated?'] == 'N')]
            update = frame[(frame['action_flag'] == 'found') & (frame['Needs Info Updated?'] == 'Y')]
            create = frame[frame['action_flag'] == 'create']
            return no_update, update, create
        else:
            pass

    @staticmethod
    def _split_existing_members(_vars, sf):
        frame = _vars.src_object_upload['frame']
        if len(_vars.found['frame'].index) > 0:
            _vars.current_members['frame'] = sf.query(sfdc_object=_query_map[_vars.list_type]['object']
                                                      , fields=_query_map[_vars.list_type]['fields']
                                                      , where=_query_map[_vars.list_type]['where'].format(
                    _vars.object_id))
            if _query_map[_vars.list_type]['rename']:
                _vars.current_members['frame'].rename(columns=_query_map[_vars.list_type]['rename'], inplace=True)
                _query_map[_vars.list_type]['fields'][0] = _query_map[_vars.list_type]['rename'][_query_map[_vars.list_type]['fields'][0]]
            if len(_vars.current_members['frame'].index) > 0:
                add, stay, remove = crud(source=frame, target=_vars.current_members['frame'],
                                         on=_query_map[_vars.list_type]['fields'][0])
                _vars.add['frame'], _vars.stay['frame'], _vars.remove['frame'] = add, stay, remove
            else:
                _vars.src_object_create['frame'] = frame
        return _vars
