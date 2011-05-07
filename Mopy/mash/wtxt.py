"""This module provides a single function for converting wtxt text files to html 
files. 

Headings:
= XXXX >> H1 "XXX"
== XXXX >> H2 "XXX"
=== XXXX >> H3 "XXX"
==== XXXX >> H4 "XXX"
Notes:
* These must start at first character of line.
* The XXX text is compressed to form an anchor. E.g == Foo Bar gets anchored as" FooBar".
* If the line has trailing ='s, they are discarded. This is useful for making 
  text version of level 1 and 2 headings more readable.

Bullet Lists:
* Level 1
  * Level 2
    * Level 3
Notes:
* These must start at first character of line.
* Recognized bullet characters are: - ! ? . + * o The dot (.) produces an invisible
  bullet, and the * produces a bullet character.
  
Styles:
  __Text__
  ~~Italic~~
  **BoldItalic**
Notes:
* These can be anywhere on line, and effects can continue across lines.

Links:
 [[file]] produces <a href=file>file</a>
 [[file|text]] produces <a href=file>text</a>

Contents
{{CONTENTS=NN}} Where NN is the desired depth of contents (1 for single level, 
2 for two levels, etc.).
"""

# Imports ----------------------------------------------------------------------
#--Standard
import os
import re

# Data ------------------------------------------------------------------------
htmlHead = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
<HEAD>
<META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=iso-8859-1">
<TITLE>%s</TITLE>
<STYLE>%s</STYLE>
</HEAD>
<BODY>
"""
defaultCss = """
H1 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #c6c63c; font-family: "Arial", serif; font-size: 12pt; page-break-before: auto; page-break-after: auto }
H2 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #e6e64c; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
H3 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-size: 10pt; font-style: normal; page-break-before: auto; page-break-after: auto }
H4 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-style: italic; page-break-before: auto; page-break-after: auto }
P { margin-top: 0.01in; margin-bottom: 0.01in; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
P.empty {}
P.list-1 { margin-left: 0.15in; text-indent: -0.15in }
P.list-2 { margin-left: 0.3in; text-indent: -0.15in }
P.list-3 { margin-left: 0.45in; text-indent: -0.15in }
P.list-4 { margin-left: 0.6in; text-indent: -0.15in }
P.list-5 { margin-left: 0.75in; text-indent: -0.15in }
P.list-6 { margin-left: 1.00in; text-indent: -0.15in }
PRE { border: 1px solid; background: #FDF5E6; padding: 0.5em; margin-top: 0in; margin-bottom: 0in; margin-left: 0.25in}
CODE { background-color: #FDF5E6;}
BODY { background-color: #ffffcc; }
"""

# Conversion ------------------------------------------------------------------
def genHtml(srcFile,outFile=None,cssDir=''):
    """Generates an html file from a wtxt file. CssDir specifies a directory to search for css files."""
    if not outFile:
        import os
        outFile = os.path.splitext(srcFile)[0]+'.html'
    # Setup ---------------------------------------------------------
    #--Headers
    reHead = re.compile(r'(=+) *(.+)')
    headFormat = "<h%d><a name='%s'>%s</a></h%d>\n"
    #--List
    reList = re.compile(r'( *)([-!?\.\+\*o]) (.*)')
    #--Misc. text
    reHRule = re.compile(r'^\s*-{4,}\s*$')
    reEmpty = re.compile(r'\s+$')
    reMDash = re.compile(r'--')
    rePreBegin = re.compile('<pre>',re.I)
    rePreEnd = re.compile('</pre>',re.I)
    def anchorReplace(maObject):
        text = maObject.group(1)
        anchor = reWd.sub('',text)
        return "<a name='%s'>%s</a>" % (anchor,text)
    #--Bold, Italic, BoldItalic
    reBold = re.compile(r'__')
    reItalic = re.compile(r'~~')
    reBoldItalic = re.compile(r'\*\*')
    states = {'bold':False,'italic':False,'boldItalic':False}
    def boldReplace(maObject):
        state = states['bold'] = not states['bold']
        return ('</B>','<B>')[state]
    def italicReplace(maObject):
        state = states['italic'] = not states['italic']
        return ('</I>','<I>')[state]
    def boldItalicReplace(maObject):
        state = states['boldItalic'] = not states['boldItalic']
        return ('</I></B>','<B><I>')[state]
    #--Links
    reLink = re.compile(r'\[\[(.*?)\]\]')
    reHttp = re.compile(r' (http://[_~a-zA-Z0-9\./%-]+)')
    reWww = re.compile(r' (www\.[_~a-zA-Z0-9\./%-]+)')
    reWd = re.compile(r'(<[^>]+>|\[[^\]]+\]|\W+)')
    rePar = re.compile(r'^([a-zA-Z]|\*\*|~~|__)')
    reFullLink = re.compile(r'(:|#|\.[a-zA-Z0-9]{2,4}$)')
    def linkReplace(maObject):
        address = text = maObject.group(1).strip()
        if '|' in text:
            (address,text) = [chunk.strip() for chunk in text.split('|',1)]
            if address == '#': address += reWd.sub('',text) 
        if not reFullLink.search(address):
            address = address+'.html'
        return '<a href="%s">%s</a>' % (address,text)
    #--Tags
    reAnchorTag = re.compile('{{A:(.+?)}}')
    reContentsTag = re.compile(r'\s*{{CONTENTS=?(\d+)}}\s*$')
    reCssTag = re.compile('\s*{{CSS:(.+?)}}\s*$')
    #--Defaults ----------------------------------------------------------
    title = ''
    level = 1
    spaces = ''
    cssFile = None
    #--Open files
    inFileRoot = re.sub('\.[a-zA-Z]+$','',srcFile)
    #--Init
    outLines = []
    contents = []
    addContents = 0
    inPre = False
    isInParagraph = False
    #--Read source file --------------------------------------------------
    ins = file(srcFile)
    for line in ins:
        isInParagraph,wasInParagraph = False,isInParagraph
        #--Preformatted? -----------------------------
        maPreBegin = rePreBegin.search(line)
        maPreEnd = rePreEnd.search(line)
        if inPre or maPreBegin or maPreEnd:
            inPre = maPreBegin or (inPre and not maPreEnd)
            outLines.append(line)
            continue
        #--Re Matches -------------------------------
        maContents = reContentsTag.match(line)
        maCss = reCssTag.match(line)
        maHead = reHead.match(line)
        maList  = reList.match(line)
        maPar   = rePar.match(line)
        maHRule  = reHRule.match(line)
        maEmpty = reEmpty.match(line)
        #--Contents ----------------------------------
        if maContents:
            if maContents.group(1):
                addContents = int(maContents.group(1))
            else:
                addContents = 100
            inPar = False
        #--CSS 
        elif maCss:
            cssFile = maCss.group(1).strip()
            continue
        #--Headers
        elif maHead:
            lead,text = maHead.group(1,2)
            text = re.sub(' *=*#?$','',text.strip())
            anchor = reWd.sub('',text)
            level = len(lead)
            line = headFormat % (level,anchor,text,level)
            if addContents: contents.append((level,anchor,text))
            #--Title?
            if not title and level <= 2: title = text
        #--List item
        elif maList:
            spaces = maList.group(1)
            bullet = maList.group(2)
            text = maList.group(3)
            if bullet == '.': bullet = '&nbsp;'
            elif bullet == '*': bullet = '&bull;'
            level = len(spaces)/2 + 1
            line = spaces+'<p class=list-'+`level`+'>'+bullet+'&nbsp; '
            line = line + text + '\n'
        #--HRule
        elif maHRule:
            line = '<hr>\n'
        #--Paragraph
        elif maPar:
            if not wasInParagraph: line = '<p>'+line
            isInParagraph = True
        #--Empty line
        elif maEmpty:
            line = spaces+'<p class=empty>&nbsp;</p>\n'
        #--Misc. Text changes --------------------
        line = reMDash.sub('&#150',line)
        line = reMDash.sub('&#150',line)
        #--Bold/Italic subs
        line = reBold.sub(boldReplace,line)
        line = reItalic.sub(italicReplace,line)
        line = reBoldItalic.sub(boldItalicReplace,line)
        #--Wtxt Tags
        line = reAnchorTag.sub(anchorReplace,line)
        #--Hyperlinks
        line = reLink.sub(linkReplace,line)
        line = reHttp.sub(r' <a href="\1">\1</a>',line)
        line = reWww.sub(r' <a href="http://\1">\1</a>',line)
        #--Save line ------------------
        #print line,
        outLines.append(line)
    ins.close()
    #--Get Css -----------------------------------------------------------
    if not cssFile:
        css = defaultCss
    else:
        cssBaseName = os.path.basename(cssFile) #--Dir spec not allowed.
        cssSrcFile  = os.path.join(os.path.dirname(srcFile),cssBaseName)
        cssDirFile  = os.path.join(cssDir,cssBaseName)
        if os.path.splitext(cssBaseName)[-1].lower() != '.css':
            raise "Invalid Css file: "+cssFile
        elif os.path.exists(cssSrcFile):
            cssFile = cssSrcFile
        elif os.path.exists(cssDirFile):
            cssFile = cssDirFile
        else:
            raise 'Css file not found: '+cssFile
        css = ''.join(open(cssFile).readlines())
        if '<' in css:
            raise "Non css tag in css file: "+cssFile
    #--Write Output ------------------------------------------------------
    out = file(outFile,'w')
    out.write(htmlHead % (title,css))
    didContents = False
    for line in outLines:
        if reContentsTag.match(line):
            if not didContents:
                baseLevel = min([level for (level,name,text) in contents])
                for (level,name,text) in contents:
                    level = level - baseLevel + 1
                    if level <= addContents:
                        out.write('<p class=list-%d>&bull;&nbsp; <a href="#%s">%s</a></p>\n' % (level,name,text))
                didContents = True
        else:
            out.write(line)
    out.write('</body>\n</html>\n')
    out.close()

