

def lists_in_queue(var_list):
    '''
    determines if there are any lists in the queue.

    :param var_list: dictionary of list variables.
    :return: boolean TRUE / FALSE
    '''
    if var_list['Lists_In_Queue'] > 0:
        return True
    else:
        print('No lists to process. Will check back in 1 hour.')
        return False


def close_mailbox_connection(M):
    '''
    closes the mailbox connection

    :param M: mailbox object
    :return: dictionary of mailbox information.
    '''
    print('Closing email_handler connection.')
    M.close()
    M.logout()
    return {'Mailbox': None}


def craft_notification_email(items):
    """
    creates the actual text values of the email.

    :param items: dictionary items for stats processing
    :return: body of email.
    """
    body = """
%s,

Your list attached to %s has been processed. Below are the results of the program. All files generated by the search program that require further research, or that were requested, have been attached.

If you have questions, please reach out to:
%s
%s
%s

Search results:
Total Advisors: %s
Found in SF: %s
Updating Contact in SF or Adding to Campaign: %s
Contact Info Up-To-Date: %s
Creating: %s
Added to Campaign or BDG: %s
Updated in Campaign or Stayed in BDG: %s
Removed from Campaign or BDG: %s
Need Research: %s
Received: %s
Process Started: %s
Process Completed: %s
Processing Time: %s
\n%s
""" % (items[0], items[1],
       items[2], items[3],
       items[4], items[5],
       items[6], items[7],
       items[8], items[9],
       items[10], items[11],
       items[12], items[13],
       items[14], items[15],
       items[16], items[17],
       items[18])
    return body