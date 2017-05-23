import pandas as pd
from gen_helper import determine_ext


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


def concat_dfs(df1, df2, df3=None):
    if df3 is not None:
        return pd.concat([df1, df2, df3])
    else:
        return pd.concat([df1, df2])


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
    df = pd.DataFrame(value_dict.values(), index=value_dict.keys())
    df = df.transpose()
    return df


def determine_num_records(path):
    df = read_df(path)
    if 'found' in path:
        num = df['ContactID'].count()
    del df
    return num
