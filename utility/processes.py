try:
    from ListManagement.utility.gen_helper import *
    from ListManagement.utility.email_helper import craft_notification_email
    from ListManagement.utility.email_wrapper import Email
    from ListManagement.utility.pandas_helper import read_df, save_df, make_df, determine_num_records
    from ListManagement.utility.sf_helper import *
except:
    from utility.gen_helper import *
    from utility.email_helper import craft_notification_email
    from utility.email_wrapper import Email
    from utility.pandas_helper import read_df, save_df, make_df, determine_num_records
    from utility.sf_helper import *


def parse_list_based_on_type(path, l_type=None, pre_or_post=None, log=None):
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
        files_created = ['cmp_upload_path', 'to_create_path']

    elif l_type == 'Account':
        dict_elements['no_update_path'] = create_path_name(path, 'no_updates')
        dict_elements['update_path'] = create_path_name(path, 'to_update')

        no_update_df = df[df['Needs Info Updated?'] == 'N']
        to_update_df = df[df['Needs Info Updated?'] != 'N']

        dict_elements['n_no_update'] = len(no_update_df.index)
        dict_elements['n_to_update'] = len(to_update_df.index)

        save_df(df=no_update_df, path=dict_elements['no_update_path'])
        save_df(df=to_update_df, path=dict_elements['update_path'])
        files_created = ['no_update_path', 'update_path']

    elif l_type == 'BizDev Group':
        dict_elements['no_update_path'] = create_path_name(path=path, new_name='no_updates')
        dict_elements['update_path'] = create_path_name(path=path, new_name='to_update')
        dict_elements['to_create_path'] = create_path_name(path=path, new_name='to_create')
        dict_elements['bdg_update_path'] = create_path_name(path=path, new_name='bdg_update')

        no_update_df = df[(df['AccountId'].notnull()) & (df['Needs Info Updated?'] == 'N')]
        to_update_df = df[(df['AccountId'].notnull()) & (df['Needs Info Updated?'] != 'N')]
        to_create_df = df[df['AccountId'].isnull()]
        bdg_update_df = df[(df['AccountId'].notnull()) & (df['Licenses'].str.contains('Series 7') or df['Licenses'].str.contains('Series 22'))]

        dict_elements['n_no_update'] = len(no_update_df.index)
        dict_elements['n_to_update'] = len(to_update_df.index)
        dict_elements['n_to_create'] = len(to_create_df.index)
        dict_elements['n_bdg_update'] = len(bdg_update_df.index)

        save_df(df=no_update_df, path=dict_elements['no_update_path'])
        save_df(df=to_update_df, path=dict_elements['update_path'])
        save_df(df=to_create_df, path=dict_elements['to_create_path'])
        save_df(df=bdg_update_df, path=dict_elements['bdg_update_path'])
        files_created = ['no_update_path', 'update_path', 'to_create_path', 'bdg_update_path']

    log.info('Parsed the %s list in to the the below files: %s' % (l_type, '\n'.join(files_created)))
    return dict_elements


def source_channel(path, record_name, obj_id, obj, aid=None, log=None):
    '''
    prepares the list for SFDC /upload and contact creation.

    :param path: path of file to be processed
    :param record_name: SFDC object record name
    :param obj_id: SFDC object id
    :param obj: SFDC object type
    :param aid: SFDC account id if SFDC object is BizDev Group
    :param log: logging object, passed from main processing
    :return:
    '''
    move_to_bulk = False
    if obj == 'Campaign':
        msg = 'Will be performed twice.'
    elif obj == 'BizDev Group':
        msg = 'Will be performed thrice.'
    else:
        msg = ''
    log.info("Preparing data prep for the %s list's action files, based list type. %s" % (obj, msg))
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
        if 'to_create_path' in path:
            list_df = drop_unneeded_columns(list_df, obj)
            to_create = 0
            list_df.loc[list_df['AccountId'].isnull(), 'AccountId'] = obj_id
            list_df.loc[list_df['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
            move_to_bulk = determine_move_to_bulk_processing(list_df)
            if move_to_bulk:
                save_conf_creation_meta(sc=sc_to_add, objid=obj_id, status=list_df.iloc[0, 0])
        else:
            list_df = drop_unneeded_columns(list_df, obj, create=False)
            to_create = 0
            list_df['CampaignId'] = obj_id

    elif obj == 'BizDev Group':
        sc_to_add = 'bdg_' + record_name + '_' + yyyy_mm
        if 'to_create_path' in path:
            list_df = drop_unneeded_columns(list_df, obj)
            to_create = len(list_df.index)
            list_df.loc[list_df['AccountId'].isnull(), 'AccountId'] = aid
            list_df.loc[list_df['SourceChannel'].isnull(), 'SourceChannel'] = sc_to_add
        elif 'bdg_update_path' in path:
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
                log.info("Can't clean up %s numbers due to %s." % (ph, Exception.message))

    save_df(df=list_df, path=path)
    return {
        'Next Step': 'Parse Out Advisors Updates'
        , 'Create': to_create
        , 'Move To Bulk': move_to_bulk
    }


def extract_dictionary_values(dict_data, log=None):
    '''
    from all values created by list processing, creates email
    to send by to list requester.

    :param dict_data: dictionary of values created by list program processing.
    :param log: logging object, passed from main processing
    :return: stats for record keeping
    '''
    log.info('Extracting stats from the %s data dictionary.' % dict_data['Object'])
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
            att_paths = [dict_data['Review Path'], dict_data['BDG Remove'],
                         dict_data['BDG Add'], dict_data['BDG Stay'], dict_data['Current Members']]
        else:
            att_paths = [dict_data['No CRD'], dict_data['FINRA Ambiguous'],
                         dict_data['BDG Remove'], dict_data['BDG Add'],
                         dict_data['BDG Stay'], dict_data['Current Members']]
    elif dict_data['FINRA?']:
        att_paths = [dict_data['No CRD'], dict_data['FINRA Ambiguous']]
    else:
        att_paths = [dict_data['Review Path']]

    total = dict_data['Total Records']
    file_name = split_name(dict_data['File Path'])
    # num_found_in_sfdc = dictValues['Found in SFDC Search #2'] + dictValues['SFDC_Found'] - toCreate
    num_found_in_sfdc = determine_num_records(dict_data['Found Path'])
    need_research = total - num_found_in_sfdc - to_create
    received = clean_date_values(dict_data['Received Date'])
    ts_received = date_to_string(received)
    process_start = dict_data['process_start']

    completed = time_now
    processing_completed = datetime.datetime.utcnow().isoformat()
    processing_time = clean_date_values(process_start) - clean_date_values(completed)
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
    try:
        log.info(
            'Processed Vars Dictionary: \n\n%s' % '\n'.join(['{}:{}'.format(k, v) for k, v in dict_data.iteritems()]))
    except:
        #Python3
        log.info(
            'Processed Vars Dictionary: \n\n%s' % '\n'.join(['{}:{}'.format(k, v) for k, v in dict_data.items()]))

    items_for_stats = {
        'File Name': file_name, 'Received Date': ts_received, 'Received From': sender_name
        , 'Created By': userName, 'File Type': obj, 'Advisors on List': total
        , 'Advisors w/CID': num_found_in_sfdc, 'Advisors w/CID old Contact Info': num_not_updating
        , 'CRD Found Not in SFDC': to_create, 'Creating': to_create
        , 'Unable to Find': need_research, 'Last Search Date': completed
        , 'Match Rate': match_rate, 'Processing Time': processing_string
    }

    listobj_cols = ['Id', 'Status__c', 'Advisors_on_List__c', 'Contacts_Added_to_Related_Record__c',
                    'Contacts_Created__c', 'Contacts_Found_in_SF__c', 'Contacts_Not_Found__c',
                    'Contacts_to_Research__c', 'Contacts_Updated__c', 'Match_Rate__c', 'List_Process_Completed_At__c',
                    'Processed_By__c']

    listobj_data = [dict_data['ListObjId'], 'Process Completed', total, obj_to_add, to_create, num_found_in_sfdc,
                    need_research, need_research, to_update, match_rate * 100, processing_completed, sf_uid]

    log.info('Updating the List record for Id: %s' % dict_data['ListObjId'])
    dict_data['SFDC Session'].update_records(obj='List__c', fields=listobj_cols, upload_data=[listobj_data])
    if len(att_paths) > 0:
        log.info('Attempting to attach %s files to the List record.' % len(att_paths))
        dict_data['SFDC Session'].upload_attachments(obj_id=dict_data['ListObjId'], attachments=att_paths)


    subject = "ALM Notification: %s list processed." % obj_name

    log.info('Sending notification email to requestor to notify of completion.')
    Email(subject=subject, to=[sender_email,userEmail], body=body_string, attachment_path=att_paths)
    return {'Next Step': 'Record Stats',
            'Stats Data': items_for_stats}


def sfdc_upload(path, obj, obj_id, session, log=None):
    paths = ['', '', '', '']
    stats = ['', '', '']
    col_nums = []
    df = read_df(path=path)
    if obj == 'BizDev Group':
        df.rename(columns={'BizDev Group': 'BizDev_Group__c', 'Licenses': 'Licenses__c'}, inplace=True)
        df = df[['ContactID', 'BizDev_Group__c', 'Licenses__c']]
        col_nums.append(df.columns.get_loc('BizDev_Group__c'))
        col_nums.append(df.columns.get_loc('ContactID'))
        col_nums.append(df.columns.get_loc('Licenses__c'))
    df_values = df.values.tolist()
    df_headers = df.columns.values.tolist()

    log.info('Attempting to upload data to SalesForce for the %s object.' % obj)
    try:
        if obj == 'Campaign':
            paths, stats = upload(session, df_headers, df_values, obj_id, obj)

        elif obj == 'BizDev Group':
            paths, stats = upload(session, df_headers, df_values, obj_id, obj, col_nums, path)
    except:
        if len(df_values) > 0:
            sub = 'LMA: %s upload fail for %s' % (path, obj)
            body = 'Experienced an error upload the %s file to the %s object in SFDC. Please' \
                   'manually upload this file at your earliest convenience.' % (path, obj)
            log.error(body)
            Email(subject=sub, to=['ricky.schools@fsinvestments.com', 'max.charles@fsinvestments.com'],
                  body=body, attachment_path=[path])
        else:
            log.info('There is no data to upload to the %s object.' % obj)

    return {'Next Step': 'Send Email',
            'BDG Remove': paths[0],
            'BDG Add': paths[1],
            'BDG Stay': paths[2],
            'Current Members': paths[3],
            'Num Removing': stats[0],
            'Num Adding': stats[1],
            'Num Updating/Staying': stats[2]}


def upload(session, headers, data, obj_id, obj, col_num=None, df_path=None):
    if len(data) > 0:
        if obj == 'Campaign':
            paths, stats = cmp_upload(session, data, obj_id, obj)
            print(data)
            if data[0][2] == 'Needs Follow-Up':
                session.update_records(obj='Campaign', fields=['Post_Event_Leads_Uploaded__c'],
                                       upload_data=[[data[0][1], 'true']])
        elif obj == 'BizDev Group':
            headers = headers_clean_up(headers)
            paths, stats = bdg_upload(session, data, obj_id, obj, col_num, df_path)
        return paths, stats
    else:
        return


def cmp_upload(session, data, obj_id, obj, n_re=0, n_added=0, n_uptd=0):
    print('\nStep 10. Salesforce Campaign Upload.')
    where = "Id='%s' AND Contact.Territory_Manager__c!='Max Prown'" % obj_id
    sf_c_cmp_members = session.query('CampaignMember', ['ContactId', 'Status', 'Id'], where)
    to_insert, to_update, to_remove = split_list(sf_c_cmp_members.values.tolist(), data, obj_id, obj)
    n_add = len(to_insert)
    n_up = len(to_update)
    while n_added < n_add:
        n_added = session.create_records(obj='CampaignMember', fields=['ContactId', 'Status', 'CampaignId'],
                                         upload_data=to_insert)

    if n_uptd < n_up:
        n_uptd = session.update_records(obj='CampaignMember', fields=['Id', 'Status', 'CampaignId'],
                                        upload_data=to_update)
    return ['', '', '', ''], [n_re, n_add, n_up]


def bdg_upload(session, data, obj_id, obj, col_num, df_path, remove_path=None, add_path=None, update_path=None,
               curr_memb=None, n_add=0, n_up=0, n_re=0):
    print('\nStep 10. Salesforce BizDev Group Upload.')
    where = "BizDev_Group__c='%s'" % obj_id
    sf_bdg_members = session.query('Contact', ['Id', 'BizDev_Group__c '], where)
    to_insert, to_update, to_remove = split_list(sf_bdg_members.values.tolist(), data, obj_id, obj, col_num[1])
    curr_memb = create_path_name(df_path, 'current_bdg_members')
    sf_bdg_members = [sf_bdg_members[i:i + 2] for i in range(0, len(sf_bdg_members), 2)]
    save_df(df=make_df(data=sf_bdg_members, columns=['Id', 'BizDev_Group__c']), path=curr_memb)
    print('Attempting to associate %s to the BizDev Group.' % len(to_insert))
    if len(to_insert) > 0:
        df_add = make_df(to_insert, columns=['ContactID', 'BizDevGroupID', 'Licenses'])
        add_path = create_path_name(df_path, 'toAdd')
        save_df(df=df_add, path=add_path)
        n_add = session.update_records('Contact', ['BizDev_Group__c', 'Licenses__c'], to_insert)

    if len(to_update) > 0:
        print('Attempting to update Licenses for %s advisors staying in the BizDevGroup.' % len(to_update))
        df_update = make_df(to_update, columns=['ContactID', 'BizDevGroupID', 'Licenses'])
        update_path = create_path_name(df_path, 'bdg_toStay')
        save_df(df=df_update, path=update_path)
        n_up = session.update_records('Contact', ['BizDev_Group__c', 'Licenses__c'], to_update)

    if to_remove is not None:
        print('We are not removing contacts by request of Krista Bono.')
        df_remove = make_df(data=to_remove, columns=['ContactID', 'Previous BizDevGroupID'])
        remove_path = create_path_name(df_path, 'to_remove')
        save_df(df=df_remove, path=remove_path)
        n_re = len(to_remove)

    session.last_list_uploaded(obj_id=obj_id, obj=obj)

    return [remove_path, add_path, update_path, curr_memb], [n_re, n_add, n_up]


def id_preprocessing_needs(path):
    # should be comprised of three steps.
    # 1. Evaluate path extension type.
    # 2. If file is of appropriate type - check if:
    # a. top row is blank
    # b. remove any random blank rows
    # c. identify if there is a bad header row
    # 3. Notify user of needs / actions performed

    _accepted_file_ext = ['.xlsx', '.xls', '.csv']
    has_bad_file_ext = False
    needs_manual_intervention = False
    has_malformed_header_row = False
    has_blank_rows = False

    extension = os.path.splitext(path)[1]
    if extension not in _accepted_file_ext:
        has_bad_file_ext = True

    if not has_bad_file_ext:
        df = read_df(path)

        if df.shape[0] - df.dropna().shape[0] > 0:
            has_blank_rows = True

    if has_bad_file_ext or has_malformed_header_row or has_blank_rows:
        needs_manual_intervention = True

    print({'needs_intervention': needs_manual_intervention,
           'bad_ext': has_bad_file_ext,
           'blank_rows': has_blank_rows,
           'malformed_header': has_malformed_header_row})
