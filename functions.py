#this is for random functions that the list program will use

def splitname(pathtosplit):
    import os
    name = os.path.split(os.path.abspath(pathtosplit))
    return name[1]


def shorten_filename_to95char(fname):
    extensionLength,file_ext=determineExtensionType(fname)
    fname=fname[:-extensionLength]
    max_fname_chars=95-extensionLength
    
    if len(fname)>max_fname_chars:
        fname = fname[:max_fname_chars]+file_ext
        
    return fname


def determineExtensionType(fname):
    filename, file_ext=os.path.splitext(fname)
    if file_ext=='.csv' or file_ext=='.pdf' or file_ext=='.xls':
        shortLen=4
    if file_ext=='.xlsx':
        shortLen=5

    del filename   
    return shortLen, file_ext
