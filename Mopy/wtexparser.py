import re

def dfFlattenNodeTree(heading, maxLevel=0):
    """Flattens a node, and all decendents into a generator"""
    if maxLevel != 0 and heading.level > maxLevel:
        return
    for child in heading.children:
        yield child 
        for decendent in dfFlattenNodeTree(child, maxLevel):
            yield decendent


def getHtmlFromLine(line):
    html = ''
    for text in line:
        html += text.getAsHtml()
    return html

def getHtmlFromHeading(heading):
    html = ''
    for line in heading.getTextLines():
        html += '&nbsp;'*(line.level-1) + getHtmlFromLine(line.text) + '<br>'
    return html

def getHtmlFromHeadings(headings):
    html = ''
    for heading in dfFlattenNodeTree(headings):
        html += '<p>' + getHtmlFromHeading(heading) + '<p>'
    return html
   
class Text:
    """Base type for a stream of characters

    This is used in that a string of text is broken up into an array of objects
    of this base type to represent bold etc
    """
    def __init__(self, text):
        self.text   = text
        self.bold   = False
        self.italic = False

    def getAsHtml(self):
        """ 
        Gets the text in html, with the current formatting settings taken into account
        
        I don't like this being here, but the other solution is much wose. The question is why does 
        this have anything to do with the class. If we followed this aproch and wanted it in 20 diffrent
        formats then we would mess this class up with 20 diffrent methods
        """
        html = self.text
        if self.bold:
            html = '<strong>' + html + '</strong>'
        if self.italic:
            html = '<em>' + html + '</em>'
        return html


class Link(Text):
    """Holds a link"""
    def __init__(self, text, href):
        Text.__init__(self, text)
        self.href = href

    def getAsHtml(self):
        html = Link.getAsHtml(self)
        return '<a href=' + self.href + '>' + html + '</a>'

class Node:
    def __init__(self, parent, level):
        self.level    = level
        self.children = []
        self.parent   = parent


class HeadingNode(Node):
    """
    This is a bit confusing. However, for my sanity
    this can contain children OR a text node which
    should be an array of TextNode which is the 
    text for those.
    """
        
    def __init__(self, parent, level, title):
        Node.__init__(self, parent, level)
        self.title = title 

        self.textNode     = None 

    def getTextLines(self):
        if self.textNode == None:
            return
        for n in dfFlattenNodeTree(self.textNode):
            yield n


class TextNode(Node):
    def __init__(self, parent, level, text):
        Node.__init__(self, parent, level)
        self.text = text

    def rawText(self):
        """Returns text without formatting information"""
        result = ""
        for n in self.text:
            result += n.text
        return result

class Parser:
    """A rough parser for Wrye's wtex format. It doesn't handle it as well as his converter
    
    Really, it is a bit of a mess. It parses headings into a tree of nodes. Each heading
    can contain a tree of text nodes below it (not connected to the heading node tree).

    Each text node contains the parsed text
    """
    def __init__(self):
        self.root = self.currentHeading = Node(None, 0);
        self.currentText    = None

    def getHeading(self, title):
        """Gets the first heading with the given title or None if no heading can be found. This is O(n)"""
        for h in self.getHeadings():
            if h.title == title:
                return h
        return None

    def getHeadings(self, maxLevel=0):
        """Gives a generator of all headings"""
        for h in dfFlattenNodeTree(self.root, maxLevel):
            yield h

    def parseFile(self, wtex):
        wtexFile = open(wtex)
        for line in wtex.readlines():
            self.parseLine(line)

    def parseString(self, wtex):
        for line in wtex.split('\n'):
            self.parseLine(line)
            
    def parseLine(self, line):
        """Decides what type of line it is and then parses it"""
        #some sort of heading
        if line[:1] == '=':
            self.parseHeading(line)
        else:
            self.parseTextLine(line)

    def parseHeading(self,line):
        match = re.match('([=]+)([^=]+)',line)
        level = len(match.group(1))
        text  = match.group(2).strip()

        self.currentHeading = self.insert(self.currentHeading,
                                          level,
                                          lambda p: HeadingNode(p, level, text))
        assert self.currentHeading!=None, "The current heading shouldn't be None"

        #we have stopped parsing text, so flag this 
        self.currentText = None

    def insert(self, currentNode, level, creator):
        """Slots a Node into another node at the correct level
        
        currentNode: The node that was the last to be parsed
        level      : the level of the node to insert
        creator    : a function which given a parent creates a new node

        returns    : the new node
        """

        #correct depth to add it as a child
        if level - 1 == currentNode.level: 
            newNode = creator(currentNode)
            currentNode.children.append(newNode)
            return newNode
        #we need to move up the tree, so try doing it by one
        #and recheck everything
        elif level <= currentNode.level:
            assert currentNode.parent != None, "At " + str(currentNode.level) + ", there was no parent when searching for level " + str(level-1)
            return self.insert(currentNode.parent, level, creator)
        #we don't know how to move down the tree, so we can't do this
        elif level > currentNode.level:
            #raise Exception("Failed as " + str(level) + " was less than the current level of " + str(currentNode.level))
            #we don't really know how to move down the tree, but we shal cheat and add it at the best possible level
            newNode       = creator(currentNode)
            newNode.level = currentNode.level + 1 
            currentNode.children.append(newNode)
            return newNode
        else:
            raise Exception("This shouldn't have happend, but once it did so is always worth checking for :P")

    
    def parseText(self, text):
        """This seperates text into bold, italic, links etc and returns it as a list
        
        TODO this doesn't cope with bold inside link text
        """
        result = []

        formattingRegex = '\\*\\*(.*?)\\*\\*'           \
                        + '|'                           \
                        + '__(.*?)__'                   \
                        + '|'                           \
                        +  '~~(.*?)~~'                  

        linkRegex       = '\\[\\['              \
                        +   '([^\\|])\\|([^\\]])' \
                        + '\\]\\]'  

        regex           = formattingRegex               \
                        + '|'                           \
                        + linkRegex                     \
                        + '|'                           \
                        + '(.+)'

        matches = re.findall(regex, text.strip())
        if len(matches) == 0:
            return result
        match   = matches[0] #TODO fix, this is a bit ugly

        bold, italic, both, linkHref, linkText, otherwise = match
        text = bold or italic or both or otherwise or None
        if text != None:
            t = Text(text)

            t.bold   = bold != ''

            t.italic = italic != '' 
            if not (t.bold or t.italic):
                t.bold = t.italic = both != ''
            result.append(t)
        else:
            assert False, "Doesn't handle links yet"
            #todo link formatting
            pass

        return result

    def parseTextLine(self, line):
        match = re.match('([\\s]*)\\*(.+)', line)

        if self.currentHeading.textNode == None or self.currentText == None:
            self.currentText = self.currentHeading.textNode = Node(None, 0)

        if match == None:
            node = TextNode(self.currentText,
                            1,
                            self.parseText(line))
            self.currentText.children.append(node)
        else:
            #given that the lowest level is 0, we need to add one to this
            #as else it runs into problems. This should have thrown an error. TODO
            level = len(match.group(1)) + 1 
            text  = self.parseText(match.group(2))


            self.currentText = self.insert(self.currentText,
                                           level,
                                           lambda p: TextNode(p, level, text))

import unittest
class TestParser(unittest.TestCase):
    def test_parseSimpleHeading(self):
        wtex = "= The Name "
        p = Parser()
        p.parseString(wtex)
        self.assertNotEqual(None, p.getHeading("The Name"))

    def test_parseSubHeading(self):
        wtex = "= The Name\n== Sub "
        p = Parser()
        p.parseString(wtex)
        self.assertNotEqual(None, p.getHeading("Sub"))
        self.assertEqual("The Name", p.getHeading("Sub").parent.title)
        self.assertEqual(2, p.getHeading("Sub").level)

    def test_parseSimpleText(self):
        wtex = "= The Name \nSome Text"
        p = Parser()
        p.parseString(wtex)
        firstLine = p.getHeading("The Name").getTextLines().next().rawText();
        self.assertEquals("Some Text", firstLine)
        
    def test_parseSimpleTextWithAstrix(self):
        wtex = "= The Name \n* Some Text"
        p = Parser()
        p.parseString(wtex)
        firstLine = p.getHeading("The Name").getTextLines().next().rawText();
        self.assertEquals("Some Text", firstLine)

    def test_parseSubText(self):
        wtex = "= The Name \n* Some Text\n * Sub"
        p = Parser()
        p.parseString(wtex)
        g = p.getHeading("The Name").getTextLines()
        g.next()
        sndNode = g.next()
        self.assertEquals(2, sndNode.level)
        sndLine = sndNode.rawText()
        self.assertEquals("Sub", sndLine)

    def test_parseSeveralHeadings(self):
        wtex = "=Main1\n==Sub1\n=Main2"
        p = Parser()
        p.parseString(wtex)
        self.assertEquals(1, p.getHeading("Main1").level)
        self.assertEquals(1, p.getHeading("Main2").level)

    def textHelper(self, inText, bold, italic, text):
        result = Parser().parseText(inText)[0]
        self.assertEquals(text, result.text)
        self.assertEquals(italic, result.italic)
        self.assertEquals(bold, result.bold)

    def test_parseText(self):
        self.textHelper('**Text**', True, False, 'Text')
        self.textHelper('*Text**', False, False, '*Text**')
        self.textHelper('__Text__', False, True, 'Text')
        self.textHelper('~~Text~~', True, True, 'Text')



if __name__ == '__main__':
    unittest.main()
