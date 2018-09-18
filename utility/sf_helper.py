def remove_duplicates(mbr_list):
    if mbr_list is None:
        return mbr_list
    else:
        unique_data = [list(x) for x in set(tuple(x) for x in mbr_list)]
        return unique_data


def split_list(id_in_obj, ids_from_search, obj_id, obj, col=None, remove=None, remove_unique=None):
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
