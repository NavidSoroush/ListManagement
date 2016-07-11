import pandas as pd
import usaddress as usa

def read_data(path):
    df=pd.read_excel(path)
    df=df.fillna('')
    return df

def save_df(df,path):
    df.to_excel(path,index=False)
    del df

def identify_address_components(df):
    headers=df.columns.values
    mailing_headers=[h for h in headers if 'Mailing' in h]
    return mailing_headers


def transform_address(add, final_address='', street='', city='', state='',zcode=''):
    order=['AddressNumber','StreetNamePreModifier','StreetName',
           'StreetNamePostType','OccupancyType','OccupancyIdentifier',
           'PlaceName','StateName','ZipCode']
    for o in order:
        for key, value in add[0].items():
            if o==key:
                final_address+= (str(value))+' '
                
            if o==key and (key!='PlaceName' and key!='StateName' and key!='ZipCode'):
                street+= str(value) + ' '
            elif key=='PlaceName':
                city=str(value)
            elif key=='StateName':
                state=str(value)
            elif key=='ZipCode':
                zcode=value
                
    return [street, city, state, zcode, final_address]
        

def address_parsing(df, mh):
    df['MailingAddress']=''
    df['MailingStreet']=''
    headers=['MailingStreet','MailingCity','MailingState',
             'MailingPostalCode','MailingAddress']
    for index, row in df.iterrows():
        address=', '.join(str(row[m]) for m in mh if m!='')
        try:
            tag_address=usa.tag(address)
            address_items=transform_address(tag_address)
            for i in range(len(headers)):
                df.loc[index,headers[i]]=address_items[i]
        except:
            df.loc[index,'MailingAddress']=address


if __name__=='__main__':
    path='C:/Users/rschools/Documents/AMPF_Updated Rep List.xlsx'
    df=read_data(path)
    mh=identify_address_components(df)
    address_parsing(df, mh)
    save_df(df,path)
