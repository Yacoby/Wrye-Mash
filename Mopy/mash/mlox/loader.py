import cPickle
import os
import fnmatch
import imp

def findMlox(start):
    """ 
    Attempts to find mlox in the give path. It avoids serching Data Files
    """
    for root, dirnames, filenames in os.walk(start):
        try:
            dirnames.remove('Data Files')
        except ValueError:
            pass
        try:
            dirnames.remove('Installers')
        except ValueError:
            pass

        for filename in fnmatch.filter(filenames, 'mlox.py'):
            return root
    return None

def mloxFromCfg():
    try:
        pk = open('startup.settings.pkl', 'rb');
        mloxPath = cPickle.load(pk)
        pk.close()
        if os.path.exists( os.path.join(mloxPath, 'mlox.py') ):
            return mloxPath
    except (IOError, EOFError):
        pass
    return None

def saveMloxCfg(path):
    pk = open('startup.settings.pkl', 'wb');
    mloxPath = cPickle.dump(path, pk)
    pk.close()

def importMlox():
    wd = os.getcwd()
    mloxPath = mloxFromCfg() or findMlox(os.path.dirname(wd))

    if mloxPath:
        #ugly hack to get around some mlox data loading issues
        os.chdir(mloxPath)
        mlox = imp.load_source('mlox', os.path.join(mloxPath, 'mlox.py'))
        os.chdir(wd)

        saveMloxCfg(mloxPath)
        return mlox
    else:
        from . import fakemlox
        return fakemlox
