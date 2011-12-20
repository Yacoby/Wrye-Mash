'''
Mash uses cPickle to store data. This means that whenever the code changes
much then it breaks backwards compatiblity. The sane solution would be to
convert everything to use json. However for my sanity, this file
provides a workaround to enable the renaming of files


(This is not a nice solution)
'''

import sys
import cPickle

def findClass(module, name):
    '''
    Find class implementation. The same as pickle.Unpickler.find_class but
    translates module names
    '''
    if module in ('bolt', 'masher', 'balt', 'mash', 'mosh', 'mush', 'mysh'):
        module = 'mash.' + module

    __import__(module)
    mod = sys.modules[module]
    klass = getattr(mod, name)
    return klass

def uncpickle(f):
    '''
    Same as cPickle.loads(f) but does module name translation
    '''
    pickleObj = cPickle.Unpickler(f)
    pickleObj.find_global = findClass
    return pickleObj.load()
