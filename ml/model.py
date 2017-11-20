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
import pickle

from ..utility.pandas_helper import read_df
from ..utility.gen_helper import path_leaf, lower_head_values

_acceptable_diagnostics = [True, False, 'only_diagnostics', ]


class HeaderPredictions:
    def __init__(self, log=None, use_saved=False, run_diagnostics=False):
        self.__loc_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
        self.use_saved = use_saved
        self.log = log
        self.log.info('Entering header prediction module.')
        self.brain = 'T:/Shared/FS2 Business Operations/Python Search Program/Training Data/Headers_Train.xlsx'
        self.predict_path = None
        self.obj = None
        self.predict_file_name = None
        self.p_df = None
        self.p_headers = None
        self.p_features = None
        self.model_pickle_loc, self.model_name_loc = '\\data\\hp_model.sav', '\\data\\model_name.txt'
        self.vectorizer = self._init_vectorizer()
        self.features, self.train_class = self.data_preprocessing()
        self.__handle_diagnostics(diagnostics=run_diagnostics)
        self.classifier = self._init_and_train_classifier()
        self.predictions, self.probability = None, None

    def data_preprocessing(self):
        self.log.info('Pre-processing header data for classification.')
        train_df = read_df(self.brain)
        train_df.rename(columns={'Header Value': 'headers'}, inplace=True)
        train_df.dropna(axis=0, inplace=True)
        headers = lower_head_values(train_df['headers'])
        train_class = train_df['Class']
        features = self.create_training_features(headers)
        return features, train_class

    def _init_vectorizer(self):
        return CountVectorizer(analyzer='char', tokenizer=None,
                               preprocessor=None, stop_words=None,
                               max_features=100)

    def _init_and_train_classifier(self):
        train_feat, test_feat, train_class, test_class = train_test_split(self.features, self.train_class,
                                                                          test_size=0.2)
        if not self.use_saved:
            f = RandomForestClassifier(n_estimators=1000, n_jobs=-1, oob_score=True)
            model = [f, 'Random Forest']
            hard_code_words = 'a stock'
        else:
            model = self.__read_saved_model()
            hard_code_words = 'the diagnostics selected'
        self.log.info('Training %s %s model.' % (hard_code_words, model[1]))
        model[0].fit(train_feat, train_class)
        test_results = model[0].predict(test_feat)
        accuracy = metrics.accuracy_score(test_class, test_results) * 100
        self.log.info('Current %s Model Accuracy: %s' % (model[1], "{0:.0f}%".format(accuracy)))
        return model[0].fit(self.features, self.train_class)

    def create_training_features(self, headers, t_type='train'):
        if t_type == 'train':
            features = self.vectorizer.fit_transform(headers)
        elif t_type == 'predict':
            features = self.vectorizer.transform(headers)
        else:
            self.log.error('%s is not a valid t_type. Must be either '
                           'train or predict.' % t_type)
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
        self.predict_file_name, self.p_df, self.p_headers, self.p_features = \
            self._init_predict_meta_data()
        r = self.classifier.predict(self.p_features)
        r_prob = self.classifier.predict_proba(self.p_features)
        prob = [np.max(rp) / np.sum(rp) for rp in r_prob]
        self.predictions, self.probability = r, prob

    def diagnostics(self, save=False):
        models = self.__init_diagnostic_models()
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
        winning_model = self.__model_selection(models, cv_scores)
        self.log.info('%s is the winning model.' % winning_model[1])
        if save:
            self.log.info('Will use %s in production.' % winning_model[1])
            pickle.dump(winning_model[0], open(self.__loc_dir + self.model_pickle_loc, mode='wb'))
            with open(self.__loc_dir + self.model_name_loc, mode='w') as name:
                name.write('%s' % winning_model[1])
        else:
            self.log.info('Will not use %s in production.\n'
                          'Exiting diagnostics module.' % winning_model[1])
            sys.exit()

    def __init_diagnostic_models(self):
        est, lrn_rate = 1000, 0.001
        return [
            [RandomForestClassifier(n_estimators=est, ), 'Random Forest'],
            [ExtraTreesClassifier(n_estimators=est, ), 'Extra Trees Classifier'],
            [KNeighborsClassifier(n_neighbors=20), '20-Nearest Neighbors'],
            [MLPClassifier(), 'MLP Neural Network']
        ]

    def __model_selection(self, models, scores):
        self.log.info('Comparing model scores.')
        return models[scores.index(max(scores))]

    def __read_saved_model(self):
        model = pickle.load(open(self.__loc_dir + self.model_pickle_loc, mode='rb'))
        with open(self.__loc_dir + self.model_name_loc, mode='r') as m_name:
            model_name = m_name.read()
        return [model, model_name]

    def __handle_diagnostics(self, diagnostics):
        if not diagnostics in _acceptable_diagnostics:
            raise ValueError('%s is not an accepted value. Must use\n %s.'
                             % ', '.join(_acceptable_diagnostics))

        elif diagnostics in [_acceptable_diagnostics[0], _acceptable_diagnostics[-1]]:
            self.diagnostics(save=True)
            if diagnostics == _acceptable_diagnostics[-1]:
                sys.exit()
