from __future__ import absolute_import
import pandas as pd

try:
    from .general import determine_ext
except:
    from ListManagement.utils.general import determine_ext


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
    return pd.concat(df_list, sort=False, ignore_index=True)


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
        num = int(df['ContactId'].count())
    del df
    return num


def regex_search_columns(frame, regex, add=None):
    cols = frame.filter(regex=regex).columns.tolist()
    if add is not None:
        if isinstance(add, str):
            cols.append(add)
        elif isinstance(add, list):
            cols.extend(add)
    return cols


def determine_output(frame, replace):
    return [col.replace(replace, '') for col in frame.columns.tolist()]


def crud(source, target, on):
    """
    source_data = {'A': [1, 2, 3], 'B': ['X', 'Y', 'Z']}
    target_data = {'A': [2, 3, 4], 'B': ['A', 'Z', 'S'], 'C': [9, 7, 3]}
    Parameters
    ----------
    source
    target
    on

    Returns
    -------

    """
    comparison_df = pd.merge(source, target, on=on, how='outer', indicator=True, suffixes=['_src', '_tgt'])

    insert = comparison_df[comparison_df['_merge'] == 'left_only'].drop(
        columns=regex_search_columns(comparison_df, 'tgt', '_merge'), axis=1).dropna(axis=1)
    update = comparison_df[comparison_df['_merge'] == 'both'].drop(
        columns=regex_search_columns(comparison_df, 'tgt', '_merge'), axis=1).dropna(axis=1)
    remove = comparison_df[comparison_df['_merge'] == 'right_only'].drop(
        columns=regex_search_columns(comparison_df, 'src', '_merge'), axis=1).dropna(axis=1)
    insert.columns, update.columns, remove.columns = determine_output(insert, '_src'), \
                                                     determine_output(update, '_src'), \
                                                     determine_output(remove, '_src')
    return insert, update, remove
