import pandas as pd

statsPath = 'T:/Shared/FS2 Business Operations/Python Search Program/Search Program Stats2.xlsx'


def init_stats_file(statsPath):
    '''
    instantiates stats file object by reading into dataframe.

    :return: stats dataframe
    '''
    return pd.read_excel(statsPath)


def save_stats_file(df):
    '''
    saves the states dataframe

    :param df:
    :return: N/A
    '''
    df.to_excel(statsPath, index=False)


def new_stat_line(value_dict):
    '''
    writes the new line of data to the stats dataframe

    :param value_dict: values to add to stats
    :return: dataframe of stats to record.
    '''
    df2 = pd.DataFrame(value_dict.values(), index=value_dict.keys())
    df2 = df2.transpose()
    return df2


def recordStats(values):
    '''
    processes stats data files

    :param values: data to record in stats dataframe
    :return: dictionary items for list processing
    '''
    df = init_stats_file(statsPath)
    print('\nStep 11. Recording stats from processing.')
    df2 = new_stat_line(values)
    df = df.append(df2, ignore_index=True)
    save_stats_file(df)
    del df
    del df2
    return {'Next Step': 'Done.'}

#
# class Stats():
#     def __init__(self):
#         self._stats_path = 'T:/Shared/FS2 Business Operations/Python Search Program/' \
#                            'Search Program Stats2.xlsx'
#         self._num_creating = 0
#         self._num_found_in_SFDC = 0
#         self._num_needing_research = 0
#         self._num_finra_ambiguous = 0
#         self._num_no_crd = 0
#         self._num_not_found = 0
#         self._num_to_review = 0
#         self._num_updating_info = 0
#         self._num_with_correct_info = 0
#         self._adding_to_cmp = 0
#         self._updating_in_cmp = 0
#         self._num_adding_to_bdg = 0
#         self._num_removing_from_bdg = 0
#
#     def __open_path_get_numbers(self, path, list_type):
#         df = init_stats_file(path)
#         if 'found' in path:
#             self._num_creating = len(df[df['ContactID'] == ''])
#             self._num_found_in_SFDC = len(df[df['ContactID' != '']])
#             if list_type != 'Campaign':
#                 self._num_updating_info = len(df[(df['ContactID'] != '') &
#                                                  (df['Needs Info Updated?'] == 'Y')])
#                 self._num_with_correct_info = self._num_found_in_SFDC - \
#                                               self._num_updating_info
#
#         if 'ambiguous' in path:
#             self._num_finra_ambiguous = len(df.values)
#
#         if 'review' in path:
#             self._num_to_review = len(df.values)
#
#         if 'remove' in path:
#             self._num_removing_from_bdg = len(df.values)
#
#         if 'add' in path:
#             self._num_adding_to_bdg = len(df.values)
#         del df
#         return self
#
#     def __open_files(self, dict_data):
#         list_type = dict_data['Object']
#         if list_type == 'Campaign':
#             self._updating_in_cmp = dict_data['Num Updating/Staying']
#             self._adding_to_cmp = dict_data['Num Adding']
#
#         files = [dict_data['Found Path'], dict_data['File Name'],
#                  dict_data['Review Path'], dict_data['No_CRD'],
#                  dict_data['FINRA Ambiguous'], dict_data['BDG Remove'],
#                  dict_data['BDG Add']]
#
#         files = [files.remove(f) for f in files if (f is None or f == '')]
#         [self.__open_path_get_numbers(f, list_type) for f in files]
#         return self
#
#     def __init_stats_data_frame(self):
#         return pd.read_excel(self._stats_path)
#
#     def process_stats(self, dict_data):
#         self.__open_files(dict_data)
#         df = self.__init_stats_data_frame()
#
#
#     def gather_and_write_stats(self, ):
#         stats_df = init_stats_file(self._stats_path)
#
#         return {'Next Step': 'Done.'}

# for testing
# statsData = {'Received Date': '1/1/2016', 'CRD Found Not in SFDC': 3,
#              'File Type': 'Campaign', 'Last Search Date': '2016-04-18 15:20:30',
#              'Created By': 'Ricky Schools', 'Match Rate': 0,
#              'Received From': u'Ricky Schools', 'Creating': 3,
#              'Advisors w/CID': 62, 'File Name': u'campaign_list_test_ALM.xlsx',
#              'Processing Time': '1 minute', 'Advisors w/CID old Contact Info': 0,
#              'Unable to Find': 32, 'Advisors on List': 94}
# recordStats(statsData)
#
# statsData
