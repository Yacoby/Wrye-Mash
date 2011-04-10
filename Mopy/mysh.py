# -*- coding: cp1252 -*-
#
# mysh.py
#
# Extension for Wrye Mash 0.8.4
#
# (c) D.C.-G. < 15:56 2010-06-11 >
#
# Published under the exact same terms as the other files of Wrye Mash.
#
# The code in this module is quite brutal. It will be operative only with the modified version
# of 'Wrye Mash.html' ('content.html').
#
# The goal is to split this html file in several other file-like object, which can be send
# to masher.HelpPage via the Navigate function.
#
# In fact, I guess that this code can be operative for any html file built like 'content.html'.
# I mean that the 'a' tags named 'TableOfContent', 'TableOfContent_end', 'Pages' and 'Pages_end'
# are present, and the tags character case should be respected.
#
# Note that 'content.html' isn't generated with any of the genHtmt functions present in mash.
# 
#
# Imports ----------------------------------------------------------------------
import os


#------------------------------------------------------------------------------
# HTMLHelpPage
#
# file like object handling the conten of a help page
class HTMLHelpPage(file):
	"""Help page file-like class."""
	def __init__(self, data):
		"""data : str : html text"""
		self.data = data
		self._pos = 0
		self._lineNum = 0

	def read(self, *args):
		"""..."""
		if len(args) != 0: 
			sz = args[0]
			pos = int(self._pos)
			if self._pos == len(self.data) -1:
				return ""
			if sz <= len(self.data[pos:]):
				self._pos += sz
				return self.data[pos:self._pos]
			else:
				self._pos = len(self.data) -1
				return self.data[pos:]
		else:
			return self.data[self._pos:]
		return self.data

	def readline(self, *args):
		lines = self.data.splitlines()
		if self._lineNum < len(lines):
			line = lines[self._lineNum]
			self._lineNum += 1
			if len(args) != 0:
				sz = args[0]
				return line[:sz]
			else:
				return line
		else:
			return ""

	def write(self, *args, **kwargs):
		"""..."""
		pass


#------------------------------------------------------------------------------
# HTMLHelpParser
#
# This class is intended to parse an HTML file and retrieve some tags.
class HTMLHelpParser(file):
	"""Handling, parsing and hashing HTML files."""
	def __init__(self):
		"""..."""
		self.src = None # str : html file path + name
		self.raw_data = None # str : html file content
		self.content = None # str : html table of content
		self.pages = None # dict : keys :  str) : page name ; values : str : page html text

	def SetSrc(self, src):
		"""Set the html source path.

			src : str : html file path + name
		"""
		self.src = src

	def ReadData(self):
		"""Reads the html source file."""
		f = open(self.src, "r")
		self.raw_data = f.read()
		f.close()

	def Parse(self):
		"""Parses the raw data and fills up the content and the pages."""
		# the first line is assumed to starts with <!DOCTYPE
		preHead = self.raw_data.splitlines()[0]
		# retrieve the sections
		# head
		head = self.raw_data[self.raw_data.lower().find("<head>"):self.raw_data.lower().find("</head>") + len("</head>")]
		# body
		body = self.raw_data[self.raw_data.lower().find("<body>"):self.raw_data.lower().find("</body>") + len("</body>")]
		# table of content
		start = body.lower().find("""<a name="tableofcontent"></a>""") and body.lower().find("""<a name='tableofcontent'></a>""")
		end = min(len(body), (body.lower().find("""<a name="tableofcontent_end"></a>""") and body.lower().find("""<a name='tableofcontent_end'></a>""")) + (len("""<a name="tableofcontent_end"></a>""") and len("""<a name='tableofcontent_end'></a>""")))
		self.content = preHead + "<html>" + head + "<body>" + body[start:end] + "</body></html>"
		# pages
		rawPages = body[body.lower().find("""<a name="pages"></a>""") + len("""<a name="pages"></a>"""):body.lower().find("""<a name="pages_end"></a>""")]
		# parse the hrefs of the table of content and retrieve only the internal doc refs
		hrefIndex = self.content.lower().find("""<p class=list-1>&bull;&nbsp; <a href="#""")
		if hrefIndex == -1:
			raise "Empty TOC"
		endPrevPage = 0
		# build up the pages
		self.pages = {}
		while hrefIndex != -1:
			hrefEnd = self.content.find(">", hrefIndex + len("""<p class=list-1>&bull;&nbsp; <a href="#""") - 2)
			pageRef = self.content[hrefIndex + len("""<p class=list-1>&bull;&nbsp; <a href="#""") - 2:hrefEnd]
			pageName = pageRef.replace("#","")
			_rawPages = rawPages[endPrevPage:]
			pageIndex = _rawPages.find(pageName.strip(""" " ' """))
			hrefIndex = self.content.lower().find("""<p class=list-1>&bull;&nbsp; <a href="#""", hrefEnd)
			pageBegin = _rawPages.lower().find("<h2>")
			pageEnd =  _rawPages[pageBegin+ 4 :].lower().find("<h2>")
			if pageEnd != -1:
				pageEnd = _rawPages[pageBegin+ 4 :].lower().find("<h2>") + pageBegin + 4
			endPrevPage += pageEnd
			page = _rawPages[pageBegin:pageEnd]
			# correcting images addresses
			if "<img " in page:
				page = page.replace("""<img src="images/""", """<img src="%s\\"""%os.path.join(os.getcwd(), "images"))
			# add the header and footer to the page data
			self.pages[pageName] = HTMLHelpPage(preHead + "<html>" + head + "<body>" + page + "</body></html>")

	def read(self, *args, **kwargs):
		return self.content

	def write(self, *args, **kwargs):
		pass

	def GetPage(self, name):
		"""Returs the page data for 'name', or the page containing 'name'.
		If not found, returns the pair None, None."""
		n = '"%s"'%name
		N = "'%s'"%name
		page = None
		subpage = None
		if n in self.pages.keys():
			page = self.pages[n]
		else:
			for p, v in self.pages.iteritems():
				if (v.read().find("name=%s"%n) != -1 or v.read().find("name=%s"%N) != -1) == True:
					page =  self.GetPage(p[1:-1])
					subpage = name
		return page, subpage

if __name__ == "__main__":
	hhp = HTMLHelpParser()
	hhp.SetSrc("content.html")
	hhp.ReadData()
	hhp.Parse()
	a = ""
	for b in hhp.pages.keys():
		a += "\t%s\n"%b
	print "Pages names:\n\n%s"%a
	raw_input("Press ``Enter`` to quit.")

