from __future__ import absolute_import
import pandas as pd

try:
    from ListManagement.utility.general import determine_ext
except:
    from utility.general import determine_ext


def read_df(path):
    e_len, ext = determine_ext(path)
    if ext in ['.xlsx', '.xls']:
        return pd.read_excel(path)
    elif ext == '.csv':
        return pd.read_csv(path, error_bad_lines=False, low_memory=False)
    else:
        raise TypeError("The file extension '%s' is invalid. Must be '.csv', '.xlsx', or '.xls'.")


def save_df(df, path):
    df.to_excel(path, index=False)


def concat_dfs(df_list):
    return pd.concat(df_list, sort=False)


def make_df(data=None, columns=None):
    if data is not None and columns is not None:
        return pd.DataFrame(data, columns=columns)
    elif data is not None:
        return pd.DataFrame(data)
    else:
        return pd.DataFrame()


def is_null(x):
    return pd.isnull(x)


def new_stat_line(value_dict):
    '''
    writes the new line of data to the stats dataframe

    :param value_dict: values to add to stats
    :return: dataframe of stats to record.
    '''
    df = pd.DataFrame(list(value_dict.values()), index=list(value_dict.keys()))
    df = df.transpose()
    return df


def determine_num_records(path):
    df = read_df(path)
    if 'found' in path:
        num = int(df['ContactID'].count())
    del df
    return num
