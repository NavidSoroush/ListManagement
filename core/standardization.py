import re

_NAMES_TO_REMOVE = [
    "jr", "jr.", "sr", "sr.", "ii", "iii", "iv", 'aams', 'aif', 'aifa', 'bcm', 'caia',
    'casl', 'ccps', 'cdfa', 'cea', 'cebs', 'ces', 'cfa', 'cfe', 'cfp', 'cfs', 'chfc',
    'chfcicap', 'chfebc', 'cic', 'cima', 'cis', 'cltc', 'clu', 'cpa', 'cpwa', 'crpc',
    'crps', 'csa', 'iar', 'jd', 'lutcf', 'mba', 'msa', 'msfp', 'pfs', 'phd', 'ppc'
]


class DataStandardization:
    def __init__(self, log):
        self.log = log

    def standardize_all(self, _vars):
        self.log.info('Standardizing data formatting.')
        _vars.update_state()
        account_name = _vars.account_name if _vars.account_name is not None else _vars.object_name
        _vars.list_source['frame'] = self.standardize_account_names(_vars.list_source['frame'], account_name)
        _vars.list_source['frame'] = self.standardize_address_metadata(_vars.list_source['frame'])
        _vars.list_source['frame'] = self.standardize_people_names(_vars.list_source['frame'])
        _vars.list_source['frame'] = self.standardize_phone_number(_vars.list_source['frame'])
        _vars.list_source['frame'] = self.make_sfdc_lookup(_vars.list_source['frame'])
        _vars.list_source['frame'], _vars.search_finra = self.make_finra_lookup(_vars.list_source['frame'])
        _vars.list_source['frame'] = self.remove_unknown_columns(_vars.list_source['frame'])
        return _vars

    def notify_status(self, obj):
        self.log.info(' >{0} standardization complete.'.format(obj))

    def standardize_account_names(self, frame, account_name):
        frame = self._is_account_col_present(frame, account_name)
        frame = self._remove_delimiters_from_account_name(frame)
        self.notify_status('Account')
        return frame

    @staticmethod
    def _is_account_col_present(frame, account_name):
        if 'Account' not in frame.columns.values:
            frame.insert(0, "Account", [account_name] * len(frame.index))
        return frame

    @staticmethod
    def _remove_delimiters_from_account_name(frame):
        frame["Account"] = frame["Account"].replace(',', '')
        return frame

    def standardize_address_metadata(self, frame):
        frame = self._combine_mailing_streets(frame)
        frame = self._clean_postal_code(frame)
        frame = self._clean_mailing_state(frame)
        self.notify_status('Address')
        return frame

    @staticmethod
    def _combine_mailing_streets(frame):
        if set(['MailingStreet1', 'MailingStreet2']).issubset(frame.columns.tolist()):
            frame.MailingStreet1 = frame.MailingStreet1.astype(str)
            frame.MailingStreet2 = frame.MailingStreet2.astype(str)
            frame.fillna('nan')
            frame['MailingStreet'] = ''
            for index, row in frame.iterrows():
                if frame.loc[index, 'MailingStreet2'] == 'nan':
                    frame.loc[index, 'MailingStreet'] = frame.loc[index, 'MailingStreet1']
                else:
                    frame.loc[index, 'MailingStreet'] = frame.loc[index, 'MailingStreet1'] + ' ' + \
                                                        frame.loc[index, 'MailingStreet2']

            del frame['MailingStreet1']
            del frame['MailingStreet2']
            frame['MailingStreet'] = frame['MailingStreet'].str.replace(',', '')
        elif 'MailingStreet1' in frame.columns.values and 'MailingStreet2' not in frame.columns.values:
            frame.rename(columns={'MailingStreet1': 'MailingStreet'}, inplace=True)
            frame['MailingStreet'] = frame['MailingStreet'].str.replace(',', '')
        return frame

    @staticmethod
    def _clean_postal_code(frame):
        """
        Standardize formatting for a pandas data frame with a column of 'MailingPostalCode' to
        ensure that MailingPostalCodes are formatted:
            '12345' rather than '12345-1234'
            '01234' rather than '1234'
        Parameters
        ----------
        frame :object:
            pandas data frame

        Returns
        -------
            pandas data frame
        """
        if 'MailingPostalCode' in frame.columns.values:
            frame['MailingPostalCode'] = frame['MailingPostalCode'].astype(str)

            frame['MailingPostalCode'] = frame.apply(
                lambda x: x['MailingPostalCode'].split('-')[0] if '-' in x['MailingPostalCode'] else x[
                    'MailingPostalCode'], axis=1)

            frame['MailingPostalCode'] = frame.apply(
                lambda x: x['MailingPostalCode'][:5] if len(x['MailingPostalCode']) == 9 else x['MailingPostalCode'],
                axis=1)

            frame['MailingPostalCode'] = frame.apply(
                lambda x: str(0) + x['MailingPostalCode'][:4] if len(x['MailingPostalCode']) == 8 else x[
                    'MailingPostalCode'], axis=1)
        return frame

    def _clean_mailing_state(self, frame):
        """
        Standardize formatting for a pandas data frame with a column of 'MailingState' to
        ensure that MailingStates are formatted:
            FL rather than Florida
        Parameters
        ----------
        frame :object:
            pandas data frame

        Returns
        -------
            pandas data frame
        """
        if 'MailingState' in frame.columns.values:
            import us
            import uszipcode
            zs = uszipcode.ZipcodeSearchEngine()
            try:
                frame['MailingState'] = frame.apply(
                    lambda x: us.states.lookup(x['MailingState'].str, use_cache=False).abbr if len(
                        x['MailingState']) > 2 else x['MailingState'], axis=1)
            except:
                try:
                    self.log.info("Unable to transform MailingState with the python 'us' library.")
                    frame['MailingState'] = frame.apply(
                        lambda x: zs.by_zipcode(x['MailingPostalCode'])['State'], axis=1)
                except:
                    self.log.info("Unable to transform MailingState with the python 'uszipcode' library.")
                    self.log.info('Will forgo attempting to transform MailingState')
        return frame

    def standardize_people_names(self, frame):
        frame = self._split_full_names(frame)
        frame = self._normalize_name_case(frame)
        self.notify_status('People names')
        return frame

    @staticmethod
    def _split_full_names(frame):
        if "FullName" in frame.columns.tolist():
            frame.insert(0, "LastName", "")
            frame.insert(0, "FirstName", "")
            for index, row in frame.iterrows():
                if ',' in row["FullName"]:
                    if row["FullName"].index(' ') < row["FullName"].index(','):
                        frame.loc[index, "FirstName"] = row["FullName"].split(' ')[0]
                        frame.loc[index, "LastName"] = ' '.join(row["FullName"].split(' ')[1:])
                    else:
                        frame.loc[index, "LastName"] = row["FullName"].split(',')[0]
                        frame.loc[index, "FirstName"] = row["FullName"].split(' ')[1]
                else:
                    full_name_list = row["FullName"].split()
                    for name in full_name_list:
                        if name.lower() in _NAMES_TO_REMOVE:
                            full_name_list.pop(full_name_list.index(name))
                    if len(full_name_list) == 3:
                        frame.loc[index, "FirstName"] = full_name_list[0]
                        frame.loc[index, "LastName"] = full_name_list[2]
                    else:
                        frame.loc[index, "FirstName"] = full_name_list[0]
                        frame.loc[index, "LastName"] = full_name_list[1]
        return frame

    @staticmethod
    def _normalize_name_case(frame):
        if set(['FirstName', 'LastName']).issubset(frame.columns.tolist()):
            frame["FirstName"] = frame["FirstName"].astype('str').apply(lambda x: x.title())
            frame["LastName"] = frame["LastName"].astype('str').apply(lambda x: x.title())
        return frame

    @staticmethod
    def make_sfdc_lookup(frame):
        lookup_keys = set(['FirstName', 'LastName', 'Account', 'MailingState', 'MailingPostalCode'])
        if lookup_keys.issubset(frame.columns.tolist()):
            frame["LkupName"] = frame["FirstName"].str[:3] + frame["LastName"] + frame["Account"].str[:10] + \
                                frame["MailingState"] + frame["MailingPostalCode"]
        return frame

    @staticmethod
    def make_finra_lookup(frame):
        try:
            frame['FinraLookup'] = frame["FirstName"] + ' ' + frame["LastName"] + " " + \
                                   frame["Account"].str[:10]
        except KeyError:
            return frame, False
        return frame, True

    def standardize_phone_number(self, frame):
        if 'Phone' in frame.columns.values:
            frame['Phone'] = frame['Phone'].apply(self._clean_phone_number)
        self.notify_status('Phone numbers')
        return frame

    @staticmethod
    def _clean_phone_number(number):
        """
        Aims to normalize the formatting of a phone number.

        Parameters
        ----------
        number
            A string representation of a phone number.

        Returns
        -------
            A normalized & updated string representation of a phone number.
        """
        phone = re.sub(r'\D', '', str(number))
        phone = phone.lstrip('1')
        if len(phone) > 10:
            return '({}) {}-{}x{}'.format(phone[0:3], phone[3:6], phone[6:10], phone[10:])

        elif len(phone) < 10:
            return ''
        else:
            return '({}) {}-{}'.format(phone[0:3], phone[3:6], phone[6:])

    @staticmethod
    def remove_unknown_columns(frame):
        return frame[[col for col in frame.columns.tolist() if 'Unknown' not in col]]
