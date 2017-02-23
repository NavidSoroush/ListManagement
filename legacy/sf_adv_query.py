list_SQL = """
SELECT
c.FirstName AS 'First Name'
, c.LastName as 'Last Name'
, c.Name as 'Contact Name'
, replace(c.SFDC_Account_Name_Test__c, ',', '') as 'Account Name'
, c.AccountId
, c.AMPF_MBR_ID__c as 'AMPF MBR ID'
, replace(c.Office_Name__c,',','') as 'Office Name'
, c.BizDev_Group__c as 'BizDev Group'
, c.Email as 'Email'
, c.MailingStreet as 'Mailing Address Line 1'
, c.MailingCity as 'Mailing City'
, c.MailingState as 'Mailing State/Province'
, c.MailingPostalCode as 'Mailing Zip/Postal Code'
, c.Phone as 'Phone'
, c.CRD_Number__c as 'CRD Number'
, c.Id as 'ContactID'
, c.Rating__c as 'Rating'
, c.Products_Used__c as 'Products Used'
, c.Licenses__c as 'Licenses'
, c.Source_Channel__c as 'SourceChannel'
, c.Last_Meeting_Event__c as 'Last Meeting/Event'
, c.Last_Sales_Presentation_Date__c as 'Last SP'
, c.Most_Recent_Sale_New__c as 'Most Recent Sale'

FROM [SalesForce Backups].dbo.Contact c

WHERE
c.DST_Contact_Type__c = 'Single'
And c.Name NOT LIKE '%/%'
--AND c.Territory_Override__c IS NULL

ORDER BY
c.CRD_Number__c desc
"""

