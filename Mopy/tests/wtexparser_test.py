import unittest

from ..wtexparser import *

class TestHtml(unittest.TestCase):
    def testGenerate(self):
        wtex = "= The Name \n* Some Text"
        p = Parser()
        p.parseString(wtex)
        html = getHtmlFromHeadings(p.getHeading("The Name"))
        expected = ( '<p><a name="TheName"></a>'
                   + '<strong>The Name</strong><br>'
                   + 'Some Text<br></p>')
        self.assertEqual(expected, html)


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
        firstLine = p.getHeading("The Name").getTextLines().next().rawText()
        self.assertEquals("Some Text", firstLine)
        
    def test_parseSimpleTextWithAstrix(self):
        wtex = "= The Name \n* Some Text"
        p = Parser()
        p.parseString(wtex)
        firstLine = p.getHeading("The Name").getTextLines().next().rawText()
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
        inText = '[[a|b]]'
        result = Parser().parseText(inText)[0]
        self.assertEquals('b', result.text)
        self.assertEquals('a', result.href)

        inText = '[[#|Test]]'
        result = Parser().parseText(inText)[0]
        self.assertEquals('Test', result.text)
        self.assertEquals('#Test', result.href)

        inText = '[[Href]]'
        result = Parser().parseText(inText)[0]
        self.assertEquals('Href', result.text)
        self.assertEquals('Href', result.href)
