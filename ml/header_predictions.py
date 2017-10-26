try:
    from ListManagement.ml.model import HeaderPredictions
    from ListManagement.utility.pandas_helper import read_df, make_df, save_df, concat_dfs
except:
    from ml.model import HeaderPredictions
    from utility.pandas_helper import read_df, make_df, save_df, concat_dfs

_confidence = .99


def predict_headers_and_pre_processing(path, obj, log):
    model = HeaderPredictions(log=log)
    model.predict(predict_path=path, obj=obj)
    headers = model.p_df.columns.values
    log.info("\nHere are the headers in the '%s' file: \n\n %s \n" % (model.predict_file_name, headers))
    output = make_df(data={"1. Header": headers, "3. Prediction": model.predictions})

    expected_inputs = model.train_class.unique().tolist()
    expected_inputs.sort()

    need_validation = output[['1. Header', '3. Prediction']]
    need_validation = need_validation.rename(columns={'1. Header': 'Header Value', '3. Prediction': 'Class'})
    if len(need_validation) > 0:
        log.info("Here are the predictions that I'm less than %s sure on:\n" % "{0:.0f}%".format(_confidence * 100))

    new_headers = []
    for index, row in need_validation.iterrows():
        if model.probability[index] > _confidence:
            tmp = [row['Header Value'], row['Class']]
            new_headers.append(tmp)
            model.p_df.rename(columns={headers[index]: new_headers[index][1]}, inplace=True)
        else:
            log.info("\nHeader given: '%s'"
                     "\nMy prediction: '%s'"
                     "\nMy confidence: %s." % (str(row['Header Value']), str(row['Class']),
                                               "{0:.0f}%".format(model.probability[index] * 100)))
            was_i_right = ""
            while was_i_right.lower not in ('y', 'n'):
                was_i_right = input("Was I right? Please just put 'Y' or 'N'.\n")
                if was_i_right.lower() == 'y':
                    tmp = [row['Header Value'], row['Class']]
                    new_headers.append(tmp)
                    log.info("Thanks. Updating your file and my training data.\n")
                    break
                elif was_i_right.lower() == 'n':
                    expected = ""
                    while expected not in expected_inputs:
                        log.info("Can you tell me what it should have been?\n")
                        expected = input("\n".join(expected_inputs) + '\n\n')
                        if expected in expected_inputs:
                            tmp = [row['Header Value'], expected]
                            new_headers.append(tmp)
                            log.info("Thanks. Updating your file and my training data.\n")
                            break
                        else:
                            log.info("Sorry, I think you typed a value wrong.")
                    break
                else:
                    log.info("I don't think you typed 'Y' or 'N', can you try again?")

            model.p_df.rename(columns={headers[index]: new_headers[index][1]}, inplace=True)

    model.p_df = pre_processing(df=model.p_df, obj=obj)

    # clean up this part of the code
    new_data = make_df(data=new_headers, columns=('Header Value', 'Class'))
    num_records = len(model.p_df.index)
    new_brain = concat_dfs(read_df(model.brain), new_data)
    save_df(new_brain, model.brain)
    save_df(df=model.p_df, path=path)

    return {'Next Step': 'Matching', 'Total Records': num_records, 'Headers': model.p_df.columns.values}


def pre_processing(df, obj):
    if 'Account' not in df.columns.values:
        acc_list = [obj] * len(df.index)
        df.insert(0, "Account", acc_list)

    if 'MailingStreet1' in df.columns.values and 'MailingStreet2' in df.columns.values:
        df.MailingStreet1 = df.MailingStreet1.astype(str)
        df.MailingStreet2 = df.MailingStreet2.astype(str)
        df.fillna('NaN')
        df['MailingStreet'] = ''
        for index, row in df.iterrows():
            if df.loc[index, 'MailingStreet2'] == 'nan':
                df.loc[index, 'MailingStreet'] = df.loc[index, 'MailingStreet1']
            else:
                df.loc[index, 'MailingStreet'] = df.loc[index, 'MailingStreet1'] + ' ' + \
                                                 df.loc[index, 'MailingStreet2']

        del df['MailingStreet1']
        del df['MailingStreet2']
        df['MailingStreet'] = df['MailingStreet'].str.replace(',', '')
    elif 'MailingStreet1' in df.columns.values and 'MailingStreet2' not in df.columns.values:
        df.rename(columns={'MailingStreet1': 'MailingStreet'}, inplace=True)
        df['MailingStreet'] = df['MailingStreet'].str.replace(',', '')

    return df
