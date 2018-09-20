def remove_duplicates(mbr_list):
    if mbr_list is None:
        return mbr_list
    else:
        unique_data = [list(x) for x in set(tuple(x) for x in mbr_list)]
        return unique_data


def headers_clean_up(headers, to_remove='ContactID'):
    return headers.remove(to_remove)


def get_user_id(sf, obj_id, att, user_email):
    import os
    user_results = sf.query(sfdc_object='User', fields=['Email', 'Id'], where="Email='%s'" % user_email)
    user_results = user_results.to_dict(orient='list')

    attch_results = sf.query(sfdc_object='Attachment', fields=['Name', 'Id', 'ParentId']
                             , where="ParentId='%s'" % obj_id)
    att_name = os.path.basename(att)
    print(attch_results.head())
    print(att_name)
    attch_results = attch_results[attch_results['Name'] == att_name].to_dict(orient='list')

    assert len(attch_results['Name']) == 1
    assert len(user_results['Email']) == 1 and user_results['Email'][0] == user_email

    return [attch_results['Id'][0], user_results['Id'][0], user_results['Id'][0]]
