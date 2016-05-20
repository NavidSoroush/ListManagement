#this is for random functions that the list program will use

def splitname(pathtosplit):
    import os
    name = os.path.split(os.path.abspath(pathtosplit))
    return name[1]


