import pandas as pd
import usaddress as usa


def read_data(path):
    '''
    reads in list to dataframe

    :param path: list file (required)
    :return: dataframe
    '''
    df = pd.read_excel(path)
    df = df.fillna('')
    return df


def save_df(df, path):
    '''
    saves the data frame to the specified path and then deletes the dataframe.

    :param df: processed dataframe (required)
    :param path: directory / path to save the file to
    :return: NONE
    '''
    df.to_excel(path, index=False)
    del df


def identify_address_components(df):
    '''
    finds all of the headers in the data frame to identify all
    data points associated with the mailing address

    :param df: data frame (required)
    :return: headers that are part of mailing address
    '''
    headers = df.columns.values
    mailing_headers = [h for h in headers if 'Mailing' in h]
    return mailing_headers


def transform_address(add, final_address='', street='', city='', state='', zcode=''):
    '''
    takes the original address and attempts to transform / clean it up
    for 'easier' processing in SFDC.

    :param add: address line
    :param final_address: default = ''
    :param street: default = ''
    :param city: default = ''
    :param state: default = ''
    :param zcode: default = ''
    :return: tuple of the cleansed data
    '''
    order = ['AddressNumber', 'StreetNamePreModifier', 'StreetName',
             'StreetNamePostType', 'OccupancyType', 'OccupancyIdentifier',
             'PlaceName', 'StateName', 'ZipCode']
    for o in order:
        for key, value in add[0].items():
            if o == key:
                final_address += (str(value)) + ' '

            if o == key and (key != 'PlaceName' and key != 'StateName' and key != 'ZipCode'):
                street += str(value) + ' '
            elif key == 'PlaceName':
                city = str(value)
            elif key == 'StateName':
                state = str(value)
            elif key == 'ZipCode':
                zcode = value

    return [street, city, state, zcode, final_address]


def address_parsing(df, mh):
    '''
    parses the mailing address

    :param df: data frame with mailing address (required)
    :param mh: list of mailing headers (required)
    :return: NONE
    '''

    df['MailingAddress'] = ''
    df['MailingStreet'] = ''
    headers = ['MailingStreet', 'MailingCity', 'MailingState',
               'MailingPostalCode', 'MailingAddress']
    for index, row in df.iterrows():
        address = ', '.join(str(row[m]) for m in mh if m != '')
        try:
            tag_address = usa.tag(address)
            address_items = transform_address(tag_address)
            for i in range(len(headers)):
                df.loc[index, headers[i]] = address_items[i]
        except:
            df.loc[index, 'MailingAddress'] = address


# if __name__ == '__main__':
#     path = 'C:/Users/rschools/Documents/AMPF_Updated Rep List.xlsx'
#     df = read_data(path)
#     mh = identify_address_components(df)
#     address_parsing(df, mh)
#     save_df(df, path)
