from ListManagement.core.ml.model import HeaderPredictions
from ListManagement.utils.pandas_helper import read_df, make_df, save_df, concat_dfs

_confidence = .99


def _update_column_names_with_predictions():
    pass


def predict_headers_and_pre_processing(_vars, log, mode):
    _vars.update_state()
    model = HeaderPredictions(log=log,) #  use_saved=True)
    model.predict(_vars)
    headers = model.p_df.columns.values
    log.info("Here are the headers in the '%s' file: \n\n %s \n" % (model.predict_file_name, headers))
    output = make_df(data={"1. Header": headers, "3. Prediction": model.predictions})

    expected_inputs = model.train_class.unique().tolist()
    expected_inputs.sort()

    need_validation = output[['1. Header', '3. Prediction']]
    need_validation = need_validation.rename(columns={'1. Header': 'Header Value', '3. Prediction': 'Class'})
    if len(need_validation) > 0:
        log.info("Here are the predictions that I'm less than %s sure on:\n" % "{0:.0f}%".format(_confidence * 100))

    new_headers = []
    for index, row in need_validation.iterrows():
        if model.probability[index] > _confidence or mode == 'auto':
        # if mode == 'auto':
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

    # clean up this part of the code
    new_data = make_df(data=new_headers, columns=('Header Value', 'Class'))
    new_brain = concat_dfs([read_df(model.brain), new_data])
    save_df(new_brain, model.brain)
    _vars.list_source['frame'] = model.p_df
    return _vars
