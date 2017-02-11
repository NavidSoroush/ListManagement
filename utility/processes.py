from gen_helpers import *
from email_helpers import craft_notification_email
from email_handler.email_wrapper import Email
from pandas_helper import read_df, save_df, determine_num_records


def parse_list_based_on_type(path, l_type=None, pre_or_post=None):
    """
    parses the list into new files based on the current biz dev, campaign, or account list.
    :param path: path to original list of advisors
    :param l_type: SFDC object (campaign or biz dev group)
    :param pre_or_post: if object is Campaign, pre or post
    :return: updated dictionary values for the main_module list processing.
    """
    dict_elements = {
        'cmp_upload': None, 'to_create': None, 'to_update': None, 'bdg_update': None,
        'no_update': None, 'n_cmp_upload': 0, 'n_to_create': 0, 'n_to_update': 0, 'n_bdg_update': 0,
        'n_no_update': 0, 'cmp_status': None, 'no_update_path': None, 'update_path': None,
        'to_create_path': None, 'cmp_upload_path': None, 'bdg_update_path': None, 'Next Step': 'Data prep.'
    }
    df = read_df(path=path)

    if l_type == 'Campaign':
        if pre_or_post == 'Post':
            dict_elements['cmp_status'] = 'Needs Follow-Up'
        else:
            dict_elements['cmp_status'] = 'Invited'

        dict_elements['to_create_path'] = create_path_name(path, 'cmp_to_create')
        dict_elements['cmp_upload_path'] = create_path_name(path, 'cmp_upload')

        cmp_upload_df = df[df['AccountId'].notnull()]
        to_create_df = df[df['AccountId'].isnull()]

        dict_elements['n_cmp_upload'] = len(cmp_upload_df.index)
        dict_elements['n_to_create'] = len(to_create_df.index)
        cmp_upload_df['Status'] = dict_elements['cmp_status']

        save_df(df=cmp_upload_df, path=dict_elements['cmp_upload_path'])
        save_df(df=to_create_df, path=dict_elements['to_create_path'])

    elif l_type == 'Account':
        dict_elements['no_update_path'] = create_path_name(path, 'no_updates')
        dict_elements['update_path'] = create_path_name(path, 'to_update')

        no_update_df = df[df['Needs Info Updated?'] == 'N']
        to_update_df = df[df['Needs Info Updated?'] != 'N']

        dict_elements['n_no_update'] = len(no_update_df.index)
        dict_elements['n_to_update'] = len(to_update_df.index)

        save_df(df=no_update_df, path=dict_elements['no_update_path'])
        save_df(df=to_update_df, path=dict_elements['update_path'])

    elif l_type == 'BizDev Group':
        dict_elements['no_update_path'] = create_path_name(path=path, new_name='no_updates')
        dict_elements['update_path'] = create_path_name(path=path, new_name='to_updates')
        dict_elements['to_create_path'] = create_path_name(path=path, new_name='to_create')
        dict_elements['bdg_update_path'] = create_path_name(path=path, new_name='bdg_update')

        no_update_df = df[(df['AccountId'].notnull()) & (df['Needs Info Updated?'] == 'N')]
        to_update_df = df[(df['AccountId'].notnull()) & (df['Needs Info Updated?'] != 'N')]
        to_create_df = df[df['AccountId'].isnull()]
        bdg_update_df = df[(df['AccountId'].notnull()) & (df['Licenses'].str.contains('Series 7|Series 22'))]

        dict_elements['n_no_update'] = len(no_update_df.index)
        dict_elements['n_to_update'] = len(to_update_df.index)
        dict_elements['n_to_create'] = len(to_create_df.index)
        dict_elements['n_bdg_update'] = len(bdg_update_df.index)

        save_df(df=no_update_df, path=dict_elements['no_update_path'])
        save_df(df=to_update_df, path=dict_elements['update_path'])
        save_df(df=to_create_df, path=dict_elements['to_create_path'])
        save_df(df=bdg_update_df, path=dict_elements['bdg_update_path'])

    return dict_elements


def source_channel(path, record_name, obj_id, obj, aid=None):
    '''
    prepares the list for SFDC /upload and contact creation.

    :param path: path of file to be processed
    :param record_name: SFDC object record name
    :param obj_id: SFDC object id
    :param obj: SFDC object type
    :param aid: SFDC account id if SFDC object is BizDev Group
    :return:
    '''
    move_to_bulk = False
    if obj == 'Campaign':
        print '\nStep 9. Data Prep (will be performed twice)'
    elif obj == 'BizDev Group':
        print '\nStep 9. Data Prep (will be performed thrice)'
    else:
        print '\nStep 9. Data Prep'
    list_df = read_df(path)

    if obj == 'Account':
        sc_to_add = 'firm_' + record_name + '_' + yyyy_mm
        list_df = drop_unneeded_columns(list_df, obj)
        new_contact_df = list_df[list_df['AccountId'].isnull()]
        crd_sc = new_contact_df[['CRDNumber', 'SourceChannel']]
        to_create = len(new_contact_df.index)
        list_df.loc[list_df['AccountId'].isnull(), 'AccountId'] = obj_id
        list_df.loc[list_df['AccountId'].notnull(), 'AccountId'] = obj_id
        list_df.loc[list_df['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add

        list_df = list_df.merge(crd_sc, how='left', on='CRDNumber')
        del list_df['SourceChannel_y']
        list_df.rename(columns={'SourceChannel_x': 'SourceChannel'}, inplace=True)
        move_to_bulk = determine_move_to_bulk_processing(list_df)
        del crd_sc
        del new_contact_df

    elif obj == 'Campaign':
        sc_to_add = 'conference_' + record_name + '_' + yyyy_mm
        if 'toCreate' in path:
            list_df = drop_unneeded_columns(list_df, obj)
            to_create = 0
            list_df.loc[list_df['AccountId'].isnull(), 'AccountId'] = obj_id
            list_df.loc[list_df['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
            move_to_bulk = determine_move_to_bulk_processing(list_df)
        else:
            list_df = drop_unneeded_columns(list_df, obj, create=False)
            to_create = 0
            list_df['CampaignId'] = obj_id

    elif obj == 'BizDev Group':
        sc_to_add = 'bdg_' + record_name + '_' + yyyy_mm
        if 'toCreate' in path:
            list_df = drop_unneeded_columns(list_df, obj)
            to_create = len(list_df.index)
            list_df.loc[list_df['AccountId'].isnull(), 'AccountId'] = aid
            list_df.loc[list_df['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
        elif 'bdgUpdate' in path:
            list_df = drop_unneeded_columns(list_df, obj, bdg=True)
            to_create = 0
            list_df['BizDev Group'] = obj_id
        else:
            list_df = drop_unneeded_columns(list_df, obj)
            to_create = 0
            list_df['AccountId'] = aid
            list_df['BizDev Group'] = obj_id

        move_to_bulk = determine_move_to_bulk_processing(list_df)

    n_head = ['Phone', 'Fax']
    for ph in n_head:
        if ph in list_df.columns.values:
            try:
                list_df[ph].astype(str)
                for index, row in list_df.iterrows():
                    list_df.loc[index, ph] = clean_phone_number(row[ph])
            except:
                print "Can't clean up %s numbers due to %s." % (ph, Exception.message)

    save_df(df=list_df, path=path)
    return {
        'Next Step': 'Parse Out Advisors Updates'
        , 'Create': to_create
        , 'Move To Bulk': move_to_bulk
    }


def extract_dictionary_values(dict_data):
    '''
    from all values created by list processing, creates email
    to send by to list requester.

    :param dict_data: dictionary of values created by list program processing.
    :return: stats for record keeping
    '''
    if dict_data['Object'] == 'Campaign':
        to_update = dict_data['n_cmp_upload']
        to_create = dict_data['n_to_create']
        obj_to_add = dict_data['Num Adding']
        obj_to_remove = dict_data['Num Removing']
        obj_to_update = dict_data['Num Updating/Staying']

    else:
        to_update = dict_data['n_to_update']
        to_create = dict_data['n_to_create']
        obj_to_add = dict_data['Num Adding']
        obj_to_remove = dict_data['Num Removing']
        obj_to_update = dict_data['Num Updating/Staying']

    if not dict_data['Move To Bulk']:
        create_advisors_note = 'Contacts will not be created. Not enough information provided.'
    else:
        create_advisors_note = ''

    obj = dict_data['Object']
    if obj == 'BizDev Group':
        if not dict_data['FINRA?']:
            att_paths = [dict_data['File Path'], dict_data['Review Path'], dict_data['BDG Remove'],
                         dict_data['BDG Add'], dict_data['BDG Stay']]
        else:
            att_paths = [dict_data['No CRD'], dict_data['FINRA Ambiguous'],
                         dict_data['Review Path'], dict_data['BDG Remove'],
                         dict_data['BDG Add'], dict_data['BDG Stay']]
    elif dict_data['FINRA?']:
        att_paths = [dict_data['File Path'], dict_data['No CRD'], dict_data['FINRA Ambiguous'],
                     dict_data['Review Path']]
    else:
        att_paths = [dict_data['File Path'], dict_data['Review Path']]

    total = dict_data['Total Records']
    file_name = split_name(dict_data['File Path'])
    # num_found_in_sfdc = dictValues['Found in SFDC Search #2'] + dictValues['SFDC_Found'] - toCreate
    num_found_in_sfdc = determine_num_records(dict_data['Found Path'])
    need_research = total - num_found_in_sfdc - to_create
    received = clean_date_values(dict_data['Received Date'])
    ts_received = date_to_string(received)
    process_start = dict_data['process_start']

    completed = time_now
    processing_time = clean_date_values(completed) - clean_date_values(process_start)
    processing_string = timedelta_to_processing_str(processing_time)
    obj_name = dict_data['Record Name']
    obj = dict_data['Object']
    num_not_updating = dict_data['n_no_update']
    sender_name = dict_data['Sender Name']
    sender_email = dict_data['Sender Email']
    match_rate = (num_found_in_sfdc + to_create) / float(total)
    items_to_email = [sender_name, obj_name, userName, userPhone,
                      userEmail, total, num_found_in_sfdc, to_update,
                      num_not_updating, to_create, obj_to_add, obj_to_update,
                      obj_to_remove, need_research, received, process_start,
                      completed, processing_string, create_advisors_note]
    body_string = craft_notification_email(items_to_email)

    items_for_stats = {
        'File Name': file_name, 'Received Date': ts_received, 'Received From': sender_name
        , 'Created By': userName, 'File Type': obj, 'Advisors on List': total
        , 'Advisors w/CID': num_found_in_sfdc, 'Advisors w/CID old Contact Info': num_not_updating
        , 'CRD Found Not in SFDC': to_create, 'Creating': to_create
        , 'Unable to Find': need_research, 'Last Search Date': completed
        , 'Match Rate': match_rate, 'Processing Time': processing_string
    }

    subject = "ALM Notification: %s list processed." % obj_name

    Email(subject=subject, to=sender_email, body=body_string, attachment_path=att_paths)
    return {'Next Step': 'Record Stats',
            'Stats Data': items_for_stats}