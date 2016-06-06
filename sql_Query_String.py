list_SQL = '''
        SELECT
	c.FirstName AS 'First Name'
	, c.LastName as 'Last Name'
	, c.Name as 'Contact Name'
	, replace(a.Name, ',', '') as 'Account Name'
	, a.Id as 'AccountId'
	, c.AMPF_MBR_ID__c as 'AMPF MBR ID'
	, replace(c.Office_Name__c,',','') as 'Office Name'
	, c.BizDev_Group__c as 'BizDev Group'
	, c.Email as 'Email'
	, replace(c.MailingStreet, ',', '') as 'Mailing Address Line 1'
	, c.MailingCity as 'Mailing City'
	, c.MailingState as 'Mailing State/Province'
	, c.MailingPostalCode as 'Mailing Zip/Postal Code'
	, c.Phone as 'Phone'
	, c.CRD_Number__c as 'CRD Number'
	, c.Id as 'ContactID'
	, c.Last_Meeting_Event__c as 'Last Meeting/Event'
	, c.Rating__c as 'Rating'
	, c.Products_Used__c as 'Products Used'
	, c.Licenses__c as 'Licenses'
	, c.Source_Channel__c as 'SourceChannel'
	, c.Last_Call_or_Meeting__c as 'Last Meeting or Call'
	, c.Chg_Date_Email__c as 'Chg Date - Email'
	, c.Chg_Date_Mailing_Address__c as 'Chg Date - Mailing Address'
	, c.Chg_Date_Phone__c as 'Chg Date - Phone'
	, c.Chg_Date_Broker_Dealer__c as 'chg Date - Broker Dealer'



FROM
	[SalesForce Backups].dbo.Account a

LEFT JOIN [SalesForce Backups].dbo.Contact c ON
	a.Id = c.AccountId

WHERE
	c.DST_Contact_Type__c = 'Single'
	And c.Name NOT LIKE '%/%'
	AND c.Territory_Override__c IS NULL

ORDER BY
        c.CRD_Number__c desc
	'''

