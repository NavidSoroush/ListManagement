complete_subject = "ALM Notification: {0} list processed."
complete_message = """{requestor},

Your list attached to {object_name} has been processed. Below are the results of 
the program. All files generated by the search program that require 
further research, or that were requested, have been attached. Additionally, refer to the list 
link below for the same stats and attachments. 

{object} link: https://fsinvestments.my.salesforce.com/{object_id}
List link: https://fsinvestments.my.salesforce.com/{list_id}

If you have questions, please reach out to:
{team}
{email}

Search results:
Total Advisors: {total}
Found in SF: {found}
Updating Contact in SF or Adding to Campaign: {updating}
Contact Info Up-To-Date: {not_updating}
Creating: {creating}
Added to {object}: {adding}
Updated in {object}: {stayed} 
Would remove from {object}: {remove}
Need research: {research}
Received: {received}
Process Started: {started}\n
Process Completed: {ended}\n
Processing Time: {duration}\n\n
"""

unable_to_process_subject = "'ALM: Unable to Process List Attached to {object_name}'"
unable_to_process_message = """{requestor},

The list attached to {object_name} has a file extension of {extension} which is unable to be processed. 

Please re-upload the list in one of the following accepted formats below.

Accepted formats: {formats}"""
