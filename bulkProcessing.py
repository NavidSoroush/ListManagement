import shutil
from functions import splitname, shorten_filename_to95char
import os

def copy_toBulkProcessing(srcPath):
    print '\nStep 10. Dropping in bulk processing path.'
    destPath='//sc12-fsphl-01/BulkImports/'
    startPath=srcPath
    fname=splitname(srcPath)
    fname=shorten_filename_to95char(fname)
    newPath=destPath+fname
    
    shutil.copy(srcPath,newPath)


##for testing
##sPath='T:/Shared/FS2 Business Operations/Python Search Program/New Lists/June Rep-Advisor List/June Rep-Advisor List_toUpdate.xlsx'
##copy_toBulkProcessing(sPath)
