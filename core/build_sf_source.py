from ListManagement.utils import general as _ghelp
from ListManagement.utils.pandas_helper import pd
from ListManagement.config import Config

Config = Config()

_ADDRESS_STOP_WORDS = [
    'Address', 'Postal', 'State', 'Street', 'City', 'Metro', 'Geocode'
    , 'Country', 'Latitude', 'Longitude'
]

update_cols = ['Last Meeting/Event', 'Last SP', 'Most Recent Sale']

_query_fields = {
    'FirstName': 'First Name', 'LastName': 'Last Name', 'SFDC_Account_Name_Test__c': 'Account Name'
    , 'AccountId': 'AccountId', 'AMPF_MBR_ID__c': 'AMPF MBR ID', 'Office_Name__c': 'Office Name'
    , 'BizDev_Group__c': 'BizDev Group', 'Email': 'Email', 'MailingStreet': 'Mailing Address Line 1'
    , 'MailingCity': 'Mailing City', 'MailingState': 'Mailing State/Province'
    , 'MailingPostalCode': 'Mailing Zip/Postal Code', 'Phone': 'Phone', 'CRD_Number__c': 'CRDNumber'
    , 'Id': 'ContactId', 'Rating__c': 'Rating', 'Products_Used__c': 'Products Used'
    , 'Licenses__c': 'Licenses', 'Source_Channel__c': 'SourceChannel'
    , 'Last_Meeting_Event__c': 'Last Meeting/Event', 'Last_Sales_Presentation_Date__c': 'Last SP'
    , 'Most_Recent_Sale_New__c': 'Most Recent Sale'
}

_query_where = "DST_Contact_Type__c = 'Single' and Territory__c != 'Partnership Records'"


# this function will coerce the dates from an object format to datetime
def clean_dates(frame, headers):
    for i in range(len(frame.columns)):
        frame.loc[:, headers[i]] = pd.to_datetime(frame.loc[:, headers[i]], errors='coerce')
    return frame


# create function to evalute last time an advisor was contact / updated
def needs_update_flag(frame, headers, activity_range, sales_range):
    df2 = clean_dates(frame, headers)
    activ_day = pd.Timestamp.now() - pd.Timedelta(days=activity_range)
    sale_day = pd.Timestamp.now() - pd.Timedelta(days=sales_range)
    var = []
    for ind, val in df2.iterrows():
        colcount = 0
        count = 0
        for v in val:
            word = str(type(v))
            if colcount < 2:
                if v > activ_day and 'NaTType' not in word:
                    count += 1
                colcount += 1
            else:
                if v > sale_day and 'NaTType' not in word:
                    count += 1
                colcount += 1
        if count > 0:
            var.append('N')
        else:
            var.append('Y')
    return var


def remove_stopwords(fields):
    to_remove = list()
    for stopword in _ADDRESS_STOP_WORDS:
        for field in fields:
            if stopword in field:
                to_remove.append(field)
    to_remove = list(set(to_remove))
    for rm in to_remove:
        fields.remove(rm)
    return fields


def _normalize_query_data(fields, result):
    """
    transforms a list of dictionaries to a column & record based object.
    [{A: '1', 'B': 5}, {A: '2', 'B': 5}, ....]
    Parameters
    ----------
    fields -> list of strs
        list of field names queried for.
    result
        raw output of salesforce bulk api.
    Returns
    -------
        {'A': [1, 2, 3, ..., n], 'B': [5, 6, 7, ...., n]}
    """
    output = {k: [] for k in fields}
    for rec in result:
        for item, val in rec.items():
            if item in output:
                output[item].append(val if val is not None else '')
    return output


def build_current_fa_list(sf):
    print('Building current sf target list.')
    query_start = _ghelp.time.time()
    q_fields = remove_stopwords([k for k, v in _query_fields.items()])
    sql = "SELECT {0} FROM Contact".format(', '.join(q_fields))

    print('Querying from Salesforce.')
    data = pd.DataFrame(_normalize_query_data(q_fields, sf.session.bulk.Contact.query(sql)))
    data.rename(columns={k: v for k, v in _query_fields.items() if k in q_fields}, inplace=True)

    print('Applying business logic.')
    data.insert(len(data.columns), 'Needs Info Updated?',
                needs_update_flag(data[update_cols], update_cols, 180, 90))

    data = data[~data.CRDNumber.str.contains('[a-zA-Z]').fillna(False)]
    data.to_csv(Config.SFDCLoc, header=True, index=False, encoding='utf-8')
    query_end = _ghelp.time.time()
    # printing success and time it took to complete query and save
    print("Saving complete. Query took: %s" % _ghelp.duration(query_start, query_end))

#
# if __name__ == '__main__':
#     from PythonUtilities.salesforcipy import SFPy
#     from ListManagement.config import Config as con
#
#     sf = SFPy(user=con.SFUser, pw=con.SFPass, token=con.SFToken,
#               domain=con.SFDomain, verbose=False, _dir=con.BaseDir)
#     out = build_current_fa_list(sf)
