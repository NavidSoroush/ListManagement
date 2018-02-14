from ListManagement.utility.pandas_helper import pd


# create functions to manage creation of lookup name for each advisor
def shorten_data(df, col_name, x):
    tmp = []
    df2 = df[col_name].fillna('')
    # df2 = df2.astype(str).str.split(',')
    for c in df2:
        if len(c) >= x:
            tmp.append(c[:x])
        elif 0 < x < len(c):
            tmp.append(c)
        else:
            tmp.append('')
    return tmp


def make_lookup_name(df, jstr):
    var = []
    var = shorten_data(df, jstr[0], 3) + df[jstr[1]] + shorten_data(df, jstr[2], 10) + df[jstr[3]] + df[jstr[4]]
    return var


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


# this function will coerce the dates from an object format to datetime
def clean_dates(frame, headers):
    max = len(frame.columns)
    for i in range(max):
        frame[headers[i]] = pd.to_datetime(frame[headers[i]], errors='coerce')
    return frame


# This function is used to evaluate the last business date of a file
# so that it can be moved from one directory to another
def date_for_move(loc_orig, loc_to):
    import os
    tmp_files = []
    for f in os.listdir(loc_orig):
        tmp_files.append(f)
    if len(loc_to + tmp_files[0]) == 0:
        os.rename(loc_orig + tmp_files[0], loc_to + tmp_files[0])
