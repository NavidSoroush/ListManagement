import shutil
from functions import splitname

def copy_toBulkProcessing(srcPath):
    print '\nStep 10. Dropping in bulk processing path.'
    destPath='//sc12-fsphl-01/BulkImports/'
    startPath=srcPath
    fname=splitname(srcPath)
    newPath=destPath+fname
    
    shutil.copy(srcPath,newPath)


def detExt(fname):
    filename, file_ext=os.path.splitext(fname)
    if file_ext=='.csv' or file_ext=='.pdf' or file_ext=='.xls':
        shortLen=4
    if file_ext=='.xlsx':
        shortLen=5

    del filename   
    return shortLen


##for testing
##sPath='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/campaign_list_test_ALM/campaign_list_test_ALM_cmp_toCreate.xlsx'
##copy_toBulkProcessing(sPath)
