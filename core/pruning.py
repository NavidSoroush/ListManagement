_accepted_cols = [
    'CRDNumber', 'FirstName', 'LastName', 'AccountId'
    , 'MailingStreet', 'MailingCity', 'MailingState', 'MailingPostalCode'
    , 'SourceChannel', 'Email', 'Website', 'AUM', 'GDC', 'Fax'
    , 'HomePhone', 'MobilePhone', 'Phone'
]
_necessary_cols = _accepted_cols[:8]
_bdg_accepted_cols = ['ContactID', 'BizDev Group', 'Licenses']
_cmp_accepted_cols = ['ContactID', 'Status', 'CampaignId']

_switcher = {
    'Account': {'bulk_upload': _accepted_cols, 'sf_upload': _accepted_cols},
    'BizDev Group': {'bulk_upload': _accepted_cols, 'sf_upload': _bdg_accepted_cols},
    'Campaign': {'bulk_upload': _accepted_cols, 'sf_upload': _cmp_accepted_cols}
}


class Pruning:
    def __init__(self, log):
        self.log = log

    def upload_preparation(self, _vars):
        _vars.update_state()
        _vars = self._prune_frames(_vars)
        return _vars

    def _prune_frames(self, _vars):
        bulk_cols = _switcher[_vars.list_type]['bulk_upload']

        if len(_vars.update['frame'].index) > 0:
            _vars.update['frame'] = self._limit_cols(_vars.update['frame'], bulk_cols)
            _vars.update = self._is_bulk_possible(_vars.update)

        if len(_vars.create['frame'].index) > 0:
            _vars.create['frame'] = self._limit_cols(_vars.create['frame'], bulk_cols)
            _vars.create = self._is_bulk_possible(_vars.create)

        sf_cols = _switcher[_vars.list_type]['sf_upload']
        if len(_vars.src_object_upload['frame'].index) > 0:
            _vars.src_object_upload['frame'] = self._limit_cols(_vars.src_object_upload['frame'], sf_cols)
            _vars.src_object_upload['frame'] = _vars.src_object_upload['frame'][sf_cols]

        if len(_vars.src_object_upload['frame'].index) > 0:
            _vars.src_object_create['frame'] = self._limit_cols(_vars.src_object_create['frame'], sf_cols)
            _vars.src_object_create['frame'] = _vars.src_object_create['frame'][sf_cols]

        if len(_vars.add['frame'].index) > 0:
            _vars.add['frame'] = self._limit_cols(_vars.add['frame'], sf_cols)
            _vars.add['frame'] = _vars.add['frame'][sf_cols]

        if len(_vars.stay['frame'].index) > 0:
            _vars.stay['frame'] = self._limit_cols(_vars.stay['frame'], sf_cols)
            _vars.stay['frame'] = _vars.stay['frame'][sf_cols]

        return _vars

    @staticmethod
    def _limit_cols(frame, cols):
        for header in frame.columns.tolist():
            if header not in cols:
                del frame[header]
        return frame

    @staticmethod
    def _is_bulk_possible(item):
        if set(_necessary_cols).issubset(item['frame'].columns.tolist()):
            item['bulk'] = True
        else:
            item['bulk'] = False
        return item
