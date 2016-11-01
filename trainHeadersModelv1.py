import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import os, re
import string

username = os.environ.get("USERNAME")


def path_leaf(path):
    '''
    :param path: path to a file
    :return: file name or file directory.
    '''
    import ntpath
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def splitByUppers(line):
    '''
    takes row of dataframe and if the entire word is upper case
    it attempts to split it if there are no spaces.
    :param line: dataframe cell value
    :return: split cell value
    '''
    tmp = []
    return_words = ""
    line = removeUnderscores(line)
    try:
        x = 0
        sum(x + 1 for i in range(len(line)) if line[i].isupper() == True)
        if len(line) > 5 and x / len(line) >= .7 and (" " not in line):
            tmp = re.findall('[A-Z][^A-Z]*', line)
            return_words = " ".join(tmp)
        else:
            return_words = line

    except:
        return_words = line

    return (return_words)


##this function allows headers to be evaluated in lowercase form for ease
##of comparison.
def lowerHeadVal(lname):
    '''
    transforms dataframe cell value to all lowercase letters.

    :param lname: value
    :return: returns lower-case format of value.
    '''
    tmp = []
    for i in lname:
        i = splitByUppers(i)

        try:
            tmp.append(str(i.lower()))
        except:
            tmp.append(str(i))
    return tmp


def removeUnderscores(line):
    '''
    replaces underscores with spaces.
    :param line: original cell value
    :return: transformed cell value without '_' underscores
    '''

    try:
        if "_" in str(line):
            line = str(line.replace("_", " "))
    except:
        pass
    return line


def training(list_file_path, objName):
    '''

    :param list_file_path: path to file whose headers need predictions
    :param objName: object of list that's being searched.
    :return: dictionary data used by main_module to determine list processing.
    '''
    print '\nStep 3:\nMatching and processing headers.'
    ###This imports the training data set and extracts the features needed
    ###to train the model
    confidence = 1.0
    filename = 'T:/Shared/FS2 Business Operations/Python Search Program/Training Data/Headers_Train.xlsx'
    train = pd.read_excel(filename)
    train_DUP = pd.read_excel(filename)
    headers = train['Header Value']
    lower_head = lowerHeadVal(headers)

    train.insert(0, 'headers', lower_head)
    del train['Header Value']
    ###Creating word vectorizer and finding the features of the
    ###training data set
    vectorizer = CountVectorizer(analyzer="char", \
                                 tokenizer=None, \
                                 preprocessor=None, \
                                 stop_words=None, \
                                 max_features=100)

    train_data_features = vectorizer.fit_transform(lower_head)
    train_data_features = train_data_features.toarray()
    vocab = vectorizer.get_feature_names()
    dist = np.sum(train_data_features, axis=0)
    ###Creates the Random forest classifier and tunes the basic
    ###settings of the model
    forest = RandomForestClassifier(n_estimators=1000, n_jobs=-1, oob_score=True)
    forest = forest.fit(train_data_features, train["Class"])
    ###imports the new list file and pulls out the column headers
    ###so that it can make preditions
    '''predict_folder = 'C:/Users/'+username+'/Dropbox/Python Search Program/New Lists/'
    p_files = os.listdir(predict_folder)
    predictFile = predict_folder + p_files[0]
    '''
    predictFile = list_file_path
    pFileName = path_leaf(predictFile)
    testPredict = pd.read_excel(predictFile)
    tpHeaders = testPredict.columns.values
    # tpHeaders = [re.sub('[^A-Za-z0-9]+', '', t) for t in tpHeaders]
    print "Here are the headers in the '%s' file: \n\n %s \n" % (pFileName, tpHeaders)
    ###This applies the preprocessing fucntions to the headers
    ###in the list file makes predicitons on them
    print 'Here is the first five lines in the list.\n\n%s' % testPredict.head()
    lower_p_headers = lowerHeadVal(tpHeaders)
    p_test_features = vectorizer.transform(lower_p_headers)
    p_test_features = p_test_features.toarray()
    result = forest.predict(p_test_features)
    result_prob = forest.predict_proba(p_test_features)
    probs =[np.max(rp)/np.sum(rp) for rp in result_prob]
    #
    # for r in range(len(result)):
    #     print "Prediction: '%s' - %s confident" % (result[r], probs[r])

    ###This just gives us the oob_score of the model based on
    ###the training data that we gave it.

    ###This creates a dataframe that houses the headers of the list program and the predictions that the model made
    output = pd.DataFrame(data={"1. Header": tpHeaders,
                                "3. Prediction": result})  # ,"2. Expected":tpHeaders})#,"4. Match?":matches})#,"Prob":tmp})
    ###This gives us the list of the unique classes that the model knows

    uniqueExpections = train['Class'].unique()
    uniqueExpections.sort()
    ###This section creates a data frame which will
    ###have the user validate the predictions of the model
    predictions_to_validate = output[['1. Header', '3. Prediction']]
    predictions_to_validate = predictions_to_validate.rename(columns={
        '1. Header': 'Header Value',
        '3. Prediction': 'Class'})
    ###This section forces the user to validate the
    ###predictions and correct them if the model guessed wrong
    ###Based on the users inputs this section will also
    ###update the headers of the original file.
    ### W_I_R stands for 'Was I Right'.
    print("\nHere are the predictions that I'm less than %s sure on:\n" % "{0:.0f}%".format(confidence*100))
    trainingAppends = []
    for index, row in predictions_to_validate.iterrows():
        if probs[index] >= confidence:
            tmp = (row['Header Value'], row['Class'])
            trainingAppends.append(tmp)
            testPredict.rename(columns={tpHeaders[index]: trainingAppends[index][1]}, inplace=True)
        else:
            print("Header given: '%s'\nMy prediction: '%s'\nConfidence: %s." % (str(row['Header Value']),
                                                                                str(row['Class']),
                                                                                "{0:.0f}%".format(probs[index] * 100)))
            W_I_R = ""
            while W_I_R.lower not in ('y', 'n'):
                W_I_R = raw_input("Was I right? Please just put 'Y' or 'N'.\n")
                if W_I_R.lower() == 'y':
                    tmp = (row['Header Value'], row['Class'])
                    trainingAppends.append(tmp)
                    print("Thanks. Updating your file and my training data.\n")
                    break
                elif W_I_R.lower() == 'n':
                    expected = ""
                    while expected not in uniqueExpections:
                        print("Can you tell me what it should have been?\n")
                        expected = raw_input("\n".join(uniqueExpections) + '\n\n')
                        if expected in uniqueExpections:
                            tmp = (row['Header Value'], expected)
                            trainingAppends.append(tmp)
                            print("Thanks. Updating your file and my training data.\n")
                            break
                        else:
                            print("Sorry, I think you typed a value wrong.")
                    break
                else:
                    print("I don't think you typed 'Y' or 'N', can you try again?")

            testPredict.rename(columns={tpHeaders[index]: trainingAppends[index][1]}, inplace=True)
    ###This section takes the users inputs and adds
    ###the headers (value) and correct class (key) of
    ###the header and updates the training file
    ###It also saves the original list file with the new header names
    if 'Account' not in testPredict.columns.values:
        accList = [objName] * len(testPredict.index)
        testPredict.insert(0, "Account", accList)

    ##this if, else statement helps to better organize the data so that uploads (updates and creation)
    ##in SFDC is 'cleaner' when transitioning from the list tool to Andrew's data updater.
    if 'MailingStreet1' in testPredict.columns.values and 'MailingStreet2' in testPredict.columns.values:
        #testPredict['MailingStreet1'].str.encode('ascii','ignore')
        #testPredict['MailingStreet2'].str.encode('ascii','ignore')
        testPredict.MailingStreet1 = testPredict.MailingStreet1.astype(str)
        testPredict.MailingStreet2 = testPredict.MailingStreet2.astype(str)
        testPredict.fillna('NaN')
        testPredict['MailingStreet'] = ''
        for index, row in testPredict.iterrows():
            if testPredict.loc[index, 'MailingStreet2'] == 'nan':
                testPredict.loc[index, 'MailingStreet'] = testPredict.loc[index, 'MailingStreet1']
            else:
                testPredict.loc[index, 'MailingStreet'] = testPredict.loc[index, 'MailingStreet1'] + ' ' + \
                                                          testPredict.loc[index, 'MailingStreet2']

        del testPredict['MailingStreet1']
        del testPredict['MailingStreet2']
        testPredict['MailingStreet'] = testPredict['MailingStreet'].str.replace(',', '')
    elif 'MailingStreet1' in testPredict.columns.values and 'MailingStreet2' not in testPredict.columns.values:
        testPredict.rename(columns={'MailingStreet1': 'MailingStreet'}, inplace=True)
        testPredict['MailingStreet'] = testPredict['MailingStreet'].str.replace(',', '')

    newData = pd.DataFrame(trainingAppends, columns=('Header Value', 'Class'))
    numRecords = len(testPredict.index)
    joining = [train_DUP, newData]
    newTrainDF = pd.concat(joining)
    newTrainDF.to_excel(filename, index=False)
    filefornextstep = predictFile  # Ricky added this variable assignment so that the code is workable for testing and to maintain continuity.
    testPredict.to_excel(filefornextstep,
                         index=False)  # Max changed from 'TestPredict' to 'filefornextstep' for continuity with pseudocode
    ret_item = {'Next Step': 'Matching', 'Total Records': numRecords, 'Headers': testPredict.columns.values}
    return ret_item
