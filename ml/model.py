import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics

try:
    from ListManagement.utility.pandas_helper import read_df
    from ListManagement.utility.gen_helper import path_leaf, lower_head_values
except:
    from utility.pandas_helper import read_df
    from utility.gen_helper import path_leaf, lower_head_values


class HeaderPredictions:
    def __init__(self, log=None):
        self.log = log
        self.log.info('Entering header prediction module.')
        self.brain = 'T:/Shared/FS2 Business Operations/Python Search Program/Training Data/Headers_Train.xlsx'
        self.predict_path = None
        self.obj = None
        self.predict_file_name = None
        self.p_df = None
        self.p_headers = None
        self.p_features = None
        self.vectorizer = self._init_vectorizer()
        self.features, self.train_class = self.data_preprocessing()
        self.classifier = self._init_and_train_classifier()
        self.predictions, self.probability = None, None

    def data_preprocessing(self):
        self.log.info('Preprocessing header data for Random Forest Classification.')
        train_df = read_df(self.brain)
        train_df.rename(columns={'Header Value': 'headers'}, inplace=True)
        train_df.dropna(axis=0, inplace=True)
        headers = lower_head_values(train_df['headers'])
        train_class = train_df['Class']
        features = self.create_training_features(headers)
        return features, train_class

    def _init_vectorizer(self):
        return CountVectorizer(analyzer='char', tokenizer=None, preprocessor=None, stop_words=None, max_features=100)

    def _init_and_train_classifier(self):
        train_size = int(len(self.features) * 0.8)
        train_feat, train_class, test_feat, test_class = self.features[:train_size], self.train_class[
                                                                                     :train_size], self.features[
                                                                                                   train_size:], self.train_class[
                                                                                                                 train_size:]
        f = RandomForestClassifier(n_estimators=1000, n_jobs=-1, oob_score=True)
        f.fit(train_feat, train_class)
        test_results = f.predict(test_feat)
        accuracy = metrics.accuracy_score(test_class, test_results) * 100
        self.log.info('Current RFC Model Accuracy: %s' % ("{0:.0f}%".format(accuracy)))
        return f.fit(self.features, self.train_class)

    def create_training_features(self, headers, t_type='train'):
        if t_type == 'train':
            features = self.vectorizer.fit_transform(headers)
        elif t_type == 'predict':
            features = self.vectorizer.transform(headers)
        else:
            self.log.error('%s is not a valid t_type. Must be either train or predict.' % t_type)
        return features.toarray()

    def _init_predict_meta_data(self):
        predict_file_name = path_leaf(self.predict_path)
        predict_df = read_df(self.predict_path)
        headers = lower_head_values(predict_df.columns.values)
        p_features = self.create_training_features(headers, t_type='predict')
        return predict_file_name, predict_df, headers, p_features

    def predict(self, predict_path, obj):
        self.log.info("Attempting to predict header names for '%s' file." % predict_path)
        self.predict_path = predict_path
        self.obj = obj
        self.predict_file_name, self.p_df, self.p_headers, self.p_features = self._init_predict_meta_data()
        r = self.classifier.predict(self.p_features)
        r_prob = self.classifier.predict_proba(self.p_features)
        prob = [np.max(rp) / np.sum(rp) for rp in r_prob]
        self.predictions, self.probability = r, prob
