import re

def dfFlattenNodeTree(heading, maxLevel=0):
    """Flattens a node, and all decendents into a generator"""
    if maxLevel != 0 and heading.level > maxLevel:
        return
    for child in heading.children:
        yield child 
        for decendent in dfFlattenNodeTree(child, maxLevel):
            yield decendent



def getHtmlFromHeadings(headings):
    """Generates HTML for a heading and all decendents based on Wrye's format"""

    def htmlDecorator(obj,  prop, val, text):
        """ This function is passed into the text to decorate it depening on text properties """
        mapping = {
            'bold'   : lambda: text if val == False else '<strong>' + text + '</strong>', 
            'italic' : lambda: text if val == False else '<em>' + text + '</em>', 
            'href'   : lambda: '<a href="' + obj.href + '">' + text + '</a>', 
        }
        if prop in mapping:
            return mapping[prop]()
        return text

    def getHtmlFromLine(line):
        html = ''
        for text in line:
            html += text.decorate(htmlDecorator)
        return html

    def getHtmlFromHeading(heading):
        html = '<strong>' + heading.title + '</strong><br>'
        for line in heading.getTextLines():
            html += '&nbsp;'*(line.level-1)*2 + getHtmlFromLine(line.text) + '<br>'
        return html

    html = '<p>' +  getHtmlFromHeading(headings) + '</p>'
    for heading in dfFlattenNodeTree(headings):
        html += '<p>' + getHtmlFromHeading(heading) + '</p>'
    return html
   
class Text:
    """
        A class that holds properties of an text, and can merge with other Text objects
    """
    def __init__(self, text):
        self.text   = text
        self.bold   = False
        self.italic = False

    def mergeWith(self, text):
        """ This merges two Text classes, however, if a property exists in the object the function belongs to
            it won't be overwitten by text unless it is False. (This is to account for properties such as bold)
        """
        for name, val in text.__dict__.iteritems():
            if name in self.__dict__:
                self.__dict__[name] = self.__dict__[name] or val
            else:
                self.__dict__[name] = val

    def decorate(self, function):
        """ 
        Decorates the text by passing each property through the given function.
        The function should be of the form
            function(textObject, propertyName, propertyValue, currentTextToModify)
        """
        html = self.text
        for name,value in vars(self).iteritems():
            html = function(self,name,value,html)

        return html

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

        #The root node for all text stemming from this heading
        self.textNode     = None 

    def getTextLines(self):
        """
            returns a generator contain all the text in this node
        """
        if self.textNode == None:
            return
        for n in dfFlattenNodeTree(self.textNode):
            yield n


class TextNode(Node):
    def __init__(self, parent, level, text):
        """
            parent: the parent node
            level : the distance down the tree, assuming the root is 0
            text  : a list of Text objects
        """
        Node.__init__(self, parent, level)
        self.text = text

    def rawText(self):
        """Returns text without formatting information"""
        result = ""
        for n in self.text:
            result += n.text
        return result

class Parser:
    """A rough parser for Wrye's wtex format. It doesn't handle it as quite as well as his converter
    
    It parses headings into a tree of nodes. Each heading can contain a tree of text nodes below 
    it (not connected to the heading node tree).

    Each text node contains the parsed text, where each node corisponds to a line
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

        #we have stopped parsing text, so flag this. This will cause the
        #text to be added to the new current node rather than the old one
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
        elif level > currentNode.level:
            #we don't really know how to move down the tree, but we shal cheat and add it at the best possible level
            newNode       = creator(currentNode)
            newNode.level = currentNode.level + 1 
            currentNode.children.append(newNode)
            return newNode
        else:
            raise Exception("This shouldn't have happend, but once it did so is always worth checking for :P")

    
    def parseText(self, text):
        """This seperates text into bold, italic, links etc and returns it as a list. It supports nested formatting"""
        origanalText = text
        result       = []

        #matches bold, italic and both
        formattingRegex = '__(.*)__'                \
                        + '|'                       \
                        + '~~(.*)~~'                \
                        + '|'                       \
                        +  '\\*\\*(.*)\\*\\*'                  

        #matches a url in the form [[href|text]]
        linkRegex       = '\\[\\['                  \
                        +   '([^\\|]*)\\|([^\\]]*)' \
                        + '\\]\\]'

        #the last line of this matches anything, that isn't
        #assumed to be the start of some of the above formatting
        regex           = formattingRegex               \
                        + '|'                           \
                        + linkRegex                     \
                        + '|'                           \
                        + '(.*?(?=\\*\\*|__|~~|\\[\\[|$))'

        #while we can keep making matches. the text variable is reduced with every match and
        #then just the remained considered.
        while len(text):
            match = re.match(regex, text)
            if match == None:
                return result

            bold, italic, both, linkHref, linkText, otherwise = match.groups()
            matchText = bold or italic or both or linkText or otherwise or None
            if matchText != None:
                t = Text(matchText)

                t.bold   = bold   != None 
                t.italic = italic != None 
                if not (t.bold or t.italic):
                    t.bold = t.italic = both != None 

                if linkHref != None:
                    t.href = linkHref

                result.append(t)

            #could happen, and it would lock the program if it did
            matchLength = len(match.group(0))
            if matchLength == 0:
                break
            text = text[matchLength:]

        #our base case, if the matched text result is exactly the same as the input, then 
        #we assume that there is nothing more to parse
        if len(result) == 1 and result[0].text == origanalText:
            return result

        #at all the text, look down a level at the text within each match and merge if required
        mergedResults = []
        for r in result:
            newResults = self.parseText(r.text)
            #copy the things from this level downwards
            for newResult in newResults:
                newResult.mergeWith(r) #copy properties down from this level to the one below
                mergedResults.append(newResult)

        return mergedResults 

    def parseTextLine(self, line):
        """ Parses a line of text that is either text, or starts "   * TEXT", where the number of spaces before the * indicates
            the indentation level
        """
        match = re.match('([\\s]*)\\* (.+)', line)

        if self.currentHeading.textNode == None or self.currentText == None:
            self.currentText = self.currentHeading.textNode = Node(None, 0)

        if match == None:
            node = TextNode(self.currentText,
                            1,
                            self.parseText(line))
            self.currentText.children.append(node)
        else:
            #given that the lowest level is 0, we need to add one to this
            #as else it runs into problems.
            level = len(match.group(1)) + 1 
            text  = self.parseText(match.group(2))


            self.currentText = self.insert(self.currentText,
                                           level,
                                           lambda p: TextNode(p, level, text))

import unittest
class TestHtml(unittest.TestCase):
    def testGenerate(self):
        wtex = "= The Name \n* Some Text"
        p = Parser()
        p.parseString(wtex)
        html = getHtmlFromHeadings(p.getHeading("The Name"))
        self.assertEqual('<p><strong>The Name</strong><br>Some Text<br></p>', html)


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
        self.textHelper('__Text__', True, False, 'Text')
        self.textHelper('~~Text~~', False, True, 'Text')
        self.textHelper('**Text**', True, True, 'Text')

    def test_parseTextEx(self):
        inText = 'Hello **World**'
        result = Parser().parseText(inText)
        self.assertEquals(2, len(result))

    def test_parseLink(self):
        inText = '[[#|Test]]'
        result = Parser().parseText(inText)[0]
        self.assertEquals('Test', result.text)
        self.assertEquals('#', result.href)


if __name__ == '__main__':
    unittest.main()
