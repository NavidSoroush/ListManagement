import pandas as pd
import os
import shutil

networkPath='//sc12-fsphl-01/BulkImports/'



def drop_forBulkProcessing(f_path):
    print '\nStep 10. Dropping in bulk processing path.'
    list_df=pd.read_excel(f_path)
    list_df['RecordType']=''
    for index, row in list_df.iterrows():
        if list_df.loc[index,'SourceChannel']=='':
            list_df.loc[index,'RecordType']='IBD'

    list_df.to_excel(f_path, index=False)

##    shutil.copy(f_path,networkPath)


##below line(s) for testing
##fileName='C:/Users/rschools/Dropbox/Python Search Program/New Lists/AMPF Update Rep List_ALPTest/AMPF Update Rep List_ALPTest_toUpdate.xlsx'
##drop_forBulkProcessing(fileName)
