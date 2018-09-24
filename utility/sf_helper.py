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
