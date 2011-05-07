"""
File exists to move the exception MashError out of masher.py so that it can be
used by other files that masher.py imports
"""

import mosh

class MashError(mosh.MoshError):
    pass
