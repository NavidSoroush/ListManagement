def _cmp_fill_campaign_ids(frame, campaign_id, status):
    frame['CampaignId'] = campaign_id
    frame['Status'] = status
    return frame


def _bdg_fill_bizdevgroup_ids(frame, bdg_id):
    frame['BizDev Group'] = bdg_id
    return frame


def _acct_fill_account_ids(frame, account_id):
    frame.loc[frame['AccountId'].notnull(), 'AccountId'] = account_id
    return frame


_switcher = {
    'Campaign': lambda df, obj_id, status: _cmp_fill_campaign_ids(df, obj_id, status),
    'Account': lambda df, obj_id, _: _acct_fill_account_ids(df, obj_id),
    'BizDev Group': lambda df, obj_id, _: _bdg_fill_bizdevgroup_ids(df, obj_id)
}


class Staging:
    def __init__(self, log):
        self.log = log

    def fill_gaps(self, _vars):
        # identify known/to create records
        # populate source channel.
        # populate account id
        # pass to appropriate source/module (bdg, accounts, campaign) for additional staging steps.
        _vars.update_state()
        _account_id = _vars.account_id if _vars.account_id is not None else _vars.object_id
        _vars.found['frame'] = self._identify_actions(_vars.found['frame'])
        _vars.found['frame'] = self._populate_source_channel(_vars.found['frame'], _vars.source_channel)
        _vars.found['frame'] = self._populate_empty_account_ids(_vars.found['frame'], _account_id)
        _vars.found['frame'] = _switcher[_vars.list_type](_vars.found['frame'], _vars.object_id,
                                                          _vars.campaign_member_status)
        return _vars

    @staticmethod
    def _identify_actions(frame):
        frame['action_flag'] = frame['SourceChannel'].apply(lambda x: 'create' if x == '' else 'found')
        return frame

    @staticmethod
    def _populate_source_channel(frame, source_channel):
        frame.loc[frame['SourceChannel'].isnull(), 'SourceChannel'] = source_channel
        return frame

    @staticmethod
    def _populate_empty_account_ids(frame, account_id):
        frame.loc[frame['AccountId'].isnull(), 'AccountId'] = account_id
        return frame
