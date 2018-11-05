import os
import sys
import inspect
import numpy as np
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn import metrics
from sklearn.externals import joblib

from PythonUtilities.PyDBA import PyDBA

from ListManagement.utils.general import path_leaf, lower_head_values

_acceptable_diagnostics = [True, False, 'only_diagnostics', ]

_base_path = os.path.join(os.path.dirname(__file__))
_saved_model = os.path.join(_base_path, 'data\\hp_model.sav')
_saved_name = os.path.join(_base_path, 'data\\model_name.txt')


class LM_Model:
    def __init__(self, log=None, use_saved=False):
        self.__loc_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
        self.use_saved = use_saved
        self.log = log
        self.trained = False
        self.dba = PyDBA(self.log)
        self.conn = self.dba.init_new_connection(server='DPHL-PROPSCORE', database='ListManagement')
        self.model_pickle_loc, self.model_name_loc = _saved_model, _saved_name
        self.brain_sql = 'TrainingData'
        self.features, self.train_class = self.data_preprocessing()
        self.vectorizer = None
        self.classifier = None

    @staticmethod
    def _init_vectorizer():
        return CountVectorizer(analyzer='char', tokenizer=None,
                               preprocessor=None, stop_words=None,
                               max_features=100)

    @staticmethod
    def _init_diagnostic_models():
        est, lrn_rate = 1000, 0.001
        return [
            [RandomForestClassifier(n_estimators=est, ), 'Random Forest'],
            [ExtraTreesClassifier(n_estimators=est, ), 'Extra Trees Classifier'],
            [KNeighborsClassifier(n_neighbors=20), '20-Nearest Neighbors'],
            [MLPClassifier(), 'MLP Neural Network']
        ]

    def _model_selection(self, models, scores):
        self.log.info('Comparing model scores.')
        return models[scores.index(max(scores))]

    def run_diagnostics(self, save=False):
        models = self._init_diagnostic_models()
        cv_scores = list()
        self.log.info('\nRunning 7 Fold Cross Validation diagnostics.')
        kfold = KFold(n_splits=7, random_state=123)
        for model in models:
            self.log.info(' -> Assessing %s model.' % model[1])
            cv_score = cross_val_score(model[0], self.features,
                                       self.train_class,
                                       scoring='accuracy',
                                       cv=kfold)
            self.log.info(
                '   --> Median CV-Accuracy Score: %s\n'
                '   --> Raw Scores: %s' % (np.median(cv_score), cv_score))
            cv_scores.append(np.median(cv_score))
        winning_model = self._model_selection(models, cv_scores)
        self.log.info('%s is the winning model.' % winning_model[1])
        if save:
            self.log.info('Will use %s in production.' % winning_model[1])
            winning_model[0] = winning_model[0].fit(self.features, self.train_class)
            joblib.dump(winning_model[0], self.model_pickle_loc)
            with open(self.model_name_loc, mode='w') as name:
                name.write('%s' % winning_model[1])
        else:
            self.log.info('Will not use %s in production.\n'
                          'Exiting diagnostics module.' % winning_model[1])
            sys.exit()

    def data_preprocessing(self):
        self.log.info('Pre-processing header data for classification.')
        train_df = self.dba.read_df('TrainingData', self.conn)
        self.dba.df_to_sql(train_df, self.conn, 'TrainingData_backup')
        train_df.rename(columns={'Header Value': 'headers'}, inplace=True)
        train_df.dropna(axis=0, inplace=True)
        headers = lower_head_values(train_df['headers'])
        train_class = train_df['Class']
        features = self.create_training_features(headers)
        return features, train_class

    def create_training_features(self, headers, t_type='train'):
        if t_type == 'train':
            features = self.vectorizer.fit_transform(headers)
        elif t_type == 'predict':
            features = self.vectorizer.transform(headers)
        else:
            self.log.error('%s is not a valid t_type. Must be either '
                           'train or predict.' % t_type)
        return features.toarray()

    def _init_predict_meta_data(self, frame):
        headers = lower_head_values(frame.columns.values)
        p_features = self.create_training_features(headers, t_type='predict')
        return headers, p_features

    def _init_and_train_classifier(self):
        if not self.trained:
            if not self.use_saved:
                train_feat, test_feat, train_class, test_class = train_test_split(self.features, self.train_class,
                                                                                  test_size=0.2)
                f = RandomForestClassifier(n_estimators=1000, n_jobs=-1, oob_score=True)
                model = [f, 'Random Forest']
                hard_code_words = 'a stock'

                self.log.info('Training %s %s model.' % (hard_code_words, model[1]))
                model[0].fit(train_feat, train_class)
                test_results = model[0].predict(test_feat)
                accuracy = metrics.accuracy_score(test_class, test_results) * 100
                self.log.info('Current %s Model Accuracy: %s' % (model[1], "{0:.0f}%".format(accuracy)))
                self.trained = True
                return model[0].fit(self.features, self.train_class)
            else:
                model = joblib.load(self.model_pickle_loc)
                with open(self.model_name_loc, mode='r') as m_name:
                    model_name = m_name.read()
                self.log.info('Loaded diagnostics selected %s model.' % model_name)
                self.trained = True
                return model
        else:
            self.log.info('The classifier is already trained.')
            return self.classifier

    def predict(self, _vars):
        self.vectorizer = self._init_vectorizer()
        self.classifier = self._init_and_train_classifier()
        frame = _vars.list_source['frame']
        headers, features = self._init_predict_meta_data(frame)
        r = self.classifier.predict(features)
        r_prob = self.classifier.predict_proba(features)
        prob = [np.max(rp) / np.sum(rp) for rp in r_prob]
        return frame, r, prob

    def save_new_training_data(self, new_data):
        self.dba.df_to_sql(new_data, self.conn, 'TrainingData', if_exists='append')
