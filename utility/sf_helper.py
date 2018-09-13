"""
sf_helper.py
====================================
Contains helper functions that are useful
when preparing data to upload to Salesforce.
"""


def remove_duplicates(mbr_list):
    """
    Helper function to 'uniqify' a list.
    Parameters
    ----------
    mbr_list
        A list of lists containing duplicates.

    Returns
    -------
        A unique set of lists.
    """
    unique_data = [list(x) for x in set(tuple(x) for x in mbr_list)]
    return unique_data


def split_list(id_in_obj, ids_from_search, obj_id, obj, col=None, remove=None, remove_unique=None):
    """
    Helper function to take two lists and parse them into 2 to 3 different lists.

    1) If any 'ids_from_search' aren't present in 'id_in_obj', add to insert.
    2) If any 'ids_from_search' are present in 'id_in_obj', add to update.
    3) If any 'id_in_obj' aren't present in 'ids_from_search', add to remove.
        (Only happens for BizDev Group Lists)

    Parameters
    ----------
    id_in_obj
        A list of unique identifiers present in a Salesforce object.
    ids_from_search
        A list of unique identifiers present in a 3rd party list.
    obj_id
        An 18-char string; Represents an Id of a Salesforce object.
    obj
        A string; Represents the name of a Salesforce object.
    col_num
        An integer; The column to use for when parsing a list.
    remove
        An empty list.
    remove_unique
        REMOVE AS NOT USED.
    Returns
    -------
        A tuple of lists (insert, update, remove)
    """
    if obj == 'Campaign':
        insert = [i for i in ids_from_search if i[0] not in id_in_obj]
        update = [i for i in ids_from_search if i[0] in id_in_obj]
        if len(update) > 0:
            update = cmp_mbr_id_for_contact_id(update, id_in_obj)
    else:
        insert = [i for i in ids_from_search if i[col] not in id_in_obj]
        update = [i for i in ids_from_search if i[col] in id_in_obj]
        if len(id_in_obj) > 0:
            remove = []
            new_list = [id_in_obj[i:i + 2] for i in range(0, len(id_in_obj), 2)]
            for srch in ids_from_search:
                for mbr in new_list:
                    if mbr[0] not in srch:
                        remove.append(mbr)
                        new_list.remove(mbr)
                        break
            for up in update:
                up[1] = obj_id
                for re in remove:
                    if up[:-1] == re:
                        remove.remove(re)

        for ins in insert:
            ins[1] = obj_id

    remove_unique = remove_duplicates(remove)
    update_unique = remove_duplicates(update)
    insert_unique = remove_duplicates(insert)

    return insert_unique, update_unique, remove_unique


def cmp_mbr_id_for_contact_id(update_list, obj_list):
    for up in range(len(update_list)):
        for u in range(len(update_list[up])):
            for l in range(len(obj_list)):
                if update_list[up][u] == obj_list[l]:
                    update_list[up][u] = str(obj_list[(l + 2)])
                    break
            break
    return update_list


def headers_clean_up(headers, to_remove='ContactID'):
    """
    Removes an element (or group of elements) from a list.

    Parameters
    ----------
    headers
        A list of column names.
    to_remove
        An element (or group of elements) to remove from a list.

    Returns
    -------
        A sliced list.
    """
    return headers.remove(to_remove)


def get_user_id(sf, obj_id, att, user_email):
    """
    Given an email address, returns a list of metadata to use when uploading to salesforce.
    Parameters
    ----------
    sf
        An authenticated Salesforce REST API session.
    obj_id
        An 18-char string; Represents an Id of a Salesforce object.
    att
        A string; Represents the name of an attachment.
    user_email
        A string; Represents a given user's email address.

    Returns
    -------
    A list of metadata to use when uploading to salesforce
    """
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
