import pandas as pd


# create functions to manage creation of lookup name for each advisor
def shortenData(df, colName, x):
    tmp = []
    df2 = df[colName].fillna('')
    # df2 = df2.astype(str).str.split(',')
    for c in df2:
        if len(c) >= x:
            tmp.append(c[:x])
        elif len(c) > 0 and len(c) < x:
            tmp.append(c)
        else:
            tmp.append('')
    return tmp


def lkupName(df, jstr):
    var = []
    var = shortenData(df, jstr[0], 3) + df[jstr[1]] + shortenData(df, jstr[2], 10) + df[jstr[3]] + df[jstr[4]]
    return var


# create function to evalute last time an advisor was contact / updated
def needsUpdate(dFrame, colHeaders, Activityrange, Salerange):
    df2 = cleanDates(dFrame, colHeaders)
    activ_day = pd.tslib.Timestamp.now() - pd.tslib.Timedelta(days=Activityrange)
    sale_day = pd.tslib.Timestamp.now() - pd.tslib.Timedelta(days=Salerange)
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
def cleanDates(dFrame, colHeaders):
    max = len(dFrame.columns)
    for i in range(max):
        dFrame[colHeaders[i]] = pd.to_datetime(dFrame[colHeaders[i]], errors='coerce')
    return dFrame


# This function is used to evaluate the last business date of a file
# so that it can be moved from one directory to another
def date_for_move(loc_orig, loc_to):
    import os
    tmp_files = []
    for f in os.listdir(loc_orig):
        tmp_files.append(f)
    if len(loc_to + tmp_files[0]) == 0:
        os.rename(loc_orig + tmp_files[0], loc_to + tmp_files[0])
