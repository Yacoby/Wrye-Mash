# Imports ---------------------------------------------------------------------
import sys
#--Force wxversion for Python 2.4
if sys.version[:3] == '2.4':
    import wxversion
    wxversion.select("2.5.3.1")
import masher

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) > 1:
        stdOutCode = int(sys.argv[1])
    else:
        stdOutCode = -1
    masher.InitSettings()
    masher.InitLinks()
    masher.InitImages()
    if stdOutCode >= 0:
        app = masher.MashApp(stdOutCode)
    else:
        app = masher.MashApp()
    app.MainLoop()
