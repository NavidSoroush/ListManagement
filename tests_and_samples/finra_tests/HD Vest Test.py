import pandas as pd
from ListManagement.search.finra import Finra
from ListManagement.utility.log_helper import ListManagementLogger


searching_path = 'C:\\Users\\mcharles\\Downloads\\HDVestStepThrough.xlsx'
list_type = 'Account'

df = pd.read_excel(searching_path)
headers = df.columns.values


def _name_preprocessing(headers, search_list):
    """
    helper method to split and clean the FullName column of the 3rd party data frame.

    1) if FullName is present, create a column for First and Last Name.
    2) iterate through the data frame and if a comma is present in the Full Name, check if:
        a) a space preceeds a comma. if so, assume the 1st element of the split FullName is the First Name
            and the 2nd element is the Last Name.
        b) a comma preceeds a space. if so, assume the inverse of the previous statement.
    3) if no comma is present, assume First Last / (suffix or middle) - splitting the FullName on spaces (' ')
    4) attempt to remove potential suffixes (which may include .jr, iii, cfa, etc.)
    5) finally, attempt to appropriately assign the First and Last Name fields to the appropriate columns.


    :param headers: columns of the data frame
    :param search_list: data frame
    :return: transformed data frame
    """
    names_to_remove = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv", 'aams', 'aif', 'aifa', 'bcm', 'caia',
                       'casl', 'ccps', 'cdfa', 'cea', 'cebs', 'ces', 'cfa', 'cfe', 'cfp', 'cfs', 'chfc',
                       'chfcicap', 'chfebc', 'cic', 'cima', 'cis', 'cltc', 'clu', 'cpa', 'cpwa', 'crpc',
                       'crps', 'csa', 'iar', 'jd', 'lutcf', 'mba', 'msa', 'msfp', 'pfs', 'phd', 'ppc']

    if "FullName" in headers:
        search_list.insert(0, "LastName", "")
        search_list.insert(0, "FirstName", "")
        for index, row in search_list.iterrows():
            if ',' in row["FullName"]:
                if row["FullName"].index(' ') < row["FullName"].index(','):
                    search_list.loc[index, "FirstName"] = row["FullName"].split(' ')[0]
                    search_list.loc[index, "LastName"] = ' '.join(row["FullName"].split(' ')[1:])
                else:
                    search_list.loc[index, "LastName"] = row["FullName"].split(',')[0]
                    search_list.loc[index, "FirstName"] = row["FullName"].split(' ')[1]
            else:
                full_name_list = row["FullName"].split()
                for name in full_name_list:
                    if name.lower() in names_to_remove:
                        full_name_list.pop(full_name_list.index(name))
                if len(full_name_list) == 3:
                    search_list.loc[index, "FirstName"] = full_name_list[0]
                    search_list.loc[index, "LastName"] = full_name_list[2]
                else:
                    search_list.loc[index, "FirstName"] = full_name_list[0]
                    search_list.loc[index, "LastName"] = full_name_list[1]
    return search_list


def _lkup_name_address_processing(headers, search_list):
    """
    helper method to create the LkupName search field, if the necessary columns are present, and pre-process them.

    1) check if PostalCode and State are available in the data frame, and convert the data types to strings
    2) loop through each row, and attempt to clean the Postal code.
    3) attempt to clean the State column, if the name (rather than abbr.) is provided. leverage us.states.lookup
    4) check if FirstName and LastName are present
        a) if all columns are present combine first 3 chars of First Name, Last Name, Account, State, and Postal
        b) ex. RicSchools FS Investm PA 19112

    :param headers: list of column headers of the data frame
    :param search_list: data frame value
    :return: transformed data frame
    """
    if "MailingPostalCode" in headers and "MailingState" in headers:
        import us
        import uszipcode
        zs = uszipcode.ZipcodeSearchEngine()

        search_list['MailingPostalCode'] = search_list['MailingPostalCode'].astype(str)

        search_list['MailingPostalCode'] = search_list.apply(
            lambda x: x['MailingPostalCode'].split('-')[0] if '-' in x['MailingPostalCode'] else x[
                'MailingPostalCode'], axis=1)

        search_list['MailingPostalCode'] = search_list.apply(
            lambda x: x['MailingPostalCode'][:5] if len(x['MailingPostalCode']) == 9 else x['MailingPostalCode'],
            axis=1)

        search_list['MailingPostalCode'] = search_list.apply(
            lambda x: str(0) + x['MailingPostalCode'][:4] if len(x['MailingPostalCode']) == 8 else x[
                'MailingPostalCode'], axis=1)

        try:
            search_list['MailingState'] = search_list.apply(
                lambda x: us.states.lookup(x['MailingState'].str, use_cache=False).abbr if len(
                    x['MailingState']) > 2 else x['MailingState'], axis=1)
        except:
            try:
                self.log.info("Unable to transform MailingState with the python 'us' library.")
                search_list['MailingState'] = search_list.apply(
                    lambda x: zs.by_zipcode(x['MailingPostalCode'])['State'], axis=1)
            except:
                self.log.info("Unable to transform MailingState with the python 'uszipcode' library.")
                self.log.info('Will forgo attempting to transform MailingState')

        """ archaic code for zip below
        search_list['MailingPostalCode'] = search_list['MailingPostalCode'].astype(str)
        for index, row in search_list.iterrows():
            search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"].split('-')[0]
            if len(row["MailingPostalCode"]) == 9:
                search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:5]
            elif len(row["MailingPostalCode"]) == 8:
                search_list.loc[index, "MailingPostalCode"] = row["MailingPostalCode"][:4]

        if np.mean(search_list['MailingState'].str.len()) > 2:
            import us
            self.log.info('MailingState column needs to be transformed.')
            for index, row in search_list.iterrows():
                try:
                    state = us.states.lookup(search_list.loc[index, "MailingState"])
                    search_list.loc[index, "MailingState"] = str(state.abbr)
                except:
                    pass
        """
        if "FirstName" in headers and "LastName" in headers:
            search_list["FirstName"] = search_list["FirstName"].apply(lambda x: x.title())
            search_list["LastName"] = search_list["LastName"].apply(lambda x: x.title())
            search_list["LkupName"] = search_list["FirstName"].str[:3] + search_list["LastName"] + search_list[
                                                                                                       "Account"].str[
                                                                                                   :10] + \
                                      search_list["MailingState"] + search_list["MailingPostalCode"]  # .str[:-2]

        else:
            self.log.info("Advisor name or account information missing")
    try:
        search_list['FinraLookup'] = search_list["FirstName"] + ' ' + search_list["LastName"] + " " + \
                                     search_list["Account"].str[:10]
    except:
        _to_finra = False
    return search_list

_name_preprocessing(headers,df)
_lkup_name_address_processing(headers,df)

df.to_excel(searching_path)

logger = ListManagementLogger().logger
fin = Finra(log=logger)

fin.scrape(searching_path, scrape_type ='crd',parse_list=True,save=True)