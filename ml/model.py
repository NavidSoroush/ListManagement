from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier
from utility.pandas_helper import read_df
from utility.gen_helpers import path_leaf
import numpy as np


class HeaderPredictions:
    def __init__(self, predict_path, obj):
        self.brain = 'T:/Shared/FS2 Business Operations/Python Search Program/Training Data/Headers_Train.xlsx'
        self.predict_path = predict_path
        self.obj = obj
        self.vectorizer = self._init_vecotrizer()
        self.features, self.train_class = self.data_preprocessing()
        self.classifier = self._init_and_train_classifier()
        self.predict_file_name, self.p_df, self.p_headers, self.p_features = self._init_predict_meta_data()
        self.predictions, self.probability = self.predict()

    def data_preprocessing(self):
        train_df = read_df(self.brain)
        train_df.rename(columns={'Header Value': 'headers'})
        headers = train_df['headers'].str.lower()
        train_class = train_df['Class']
        features = self.create_training_features(headers)
        return features, train_class

    def _init_vectorizer(self):
        return CountVectorizer(analyzer='char', tokenizer=None, preprocessor=None, stop_words=None, max_features=100)

    def _init_and_train_classifier(self):
        f = RandomForestClassifier(n_estimators=1000, n_jobs=-1, oob_score=True)
        return f.fit(self.features, self.train_class)

    def create_training_features(self, headers, t_type='train'):
        if t_type == 'train':
            features = self.vectorizer.fit_transform(headers)
        elif t_type == 'predict':
            features = self.vectorizer.transform(headers)
        else:
            raise TypeError('%s is not a valid t_type. Must be either train or predict.' % t_type)
        return features.toarray()

    def _init_predict_meta_data(self):
        predict_file_name = path_leaf(self.predict_path)
        predict_df = read_df(self.predict_path)
        headers = map(str.lower, predict_df.columns.values)
        p_features = self.create_training_features(headers, t_type='predict')
        return predict_file_name, predict_df, headers, p_features

    def predict(self):
        r = self.classifier.predict(self.p_features)
        r_prob = self.classifier.predict_proba(self.p_features)
        prob = [np.max(rp) / np.sum(rp) for rp in r_prob]
        return r, prob
