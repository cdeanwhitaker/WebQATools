#!/usr/bin/python
import getopt, re, sys, urllib, zipfile
from datetime import datetime

class Website:
	content = None
	def __init__ (self, url, newDepth, newRoot=None):
		self.depth = newDepth
		self.root = newRoot
		self.protocol = re.compile ("https://").search (url) and "https" \
			or re.compile ("http://").search (url) and "http" \
			or None
		try:
			assert ( self.protocol or self.root )
		except AssertionError, ae:
			raise AssertionError ("URL must contain the protocol http or https")
		if self.protocol is None:
			self.protocol = self.root.protocol
			self.domain = self.root.domain
			self.subdomain = self.root.subdomain
			self.path = url
		else:
			urlParts = url.replace ("%s://" % (self.protocol), "").split ("/")
			self.domain, self.path = urlParts [0], "/".join (urlParts [1:])
			parts = self.domain.split (".")
			if len (parts) > 2:
				self.subdomain = parts [0]
				self.domain = ".".join (parts [1:])
			else:
				self.subdomain = ""
				self.domain = ".".join (parts)
		self.getHost = lambda: self.subdomain + "." + self.domain
		self.isExternal = lambda: (self.root is not None) and (self.getHost() != self.root.getHost())
		self.debug = lambda: map (lambda s: sys.stdout.write ("%s\n"%s), [
			"     depth: %d" % self.depth,
			"  protocol: %s" % self.protocol,
			" subdomain: %s" % self.subdomain,
			"    domain: %s" % self.domain,
			"      path: %s" % self.path,
			"      host: %s" % self.getHost(),
			"  external: %s" % self.isExternal() ])

	def genURL (self):
		""" Form a URL from the instance attributes """
		return "%s://%s.%s%s%s" \
			% (self.protocol, self.subdomain, self.domain, \
			self.path and "/" or "", self.path)

	def fetch (self):
		""" Return contents of page, also setting content attribute """
		pageURL = self.genURL()
		conn = urllib.urlopen (pageURL)
		self.content = conn.read()
		conn.close()
		return self.content

	def searchLinks (self, page):
		""" Return all href links in page """
		return re.findall ('href="(.*?)"', page)

	def crawl (self, websiteMap, maxDepth, rawurllist=[], depth=1):
		"""
			Read links from instance's page
			Recursively crawl links to maxDepth or until now NEW links are found
		"""
		list = self.searchLinks (self.fetch())
		list = map (lambda x: re.sub ("^/", "", x), list)
		list = map (lambda x: re.sub ("/$", "", x), list)
		self.excludePatterns = lambda: ["mailto:", "javascript:", "#", "^/$"]
		for p in self.excludePatterns():
			list = filter (lambda x: not re.compile (p).match (x), list)
		list = filter (lambda x: x not in rawurllist, list)
		newMap = {}
		# Create instances for each NEW link, adding them to map
		for link in list:
			rawurllist.append (link)
			linkWebsite = Website (link, depth, self)
			genLink = linkWebsite.genURL()
			if ( genLink not in websiteMap.keys() ) and ( genLink not in newMap.keys() ):
				if not linkWebsite.isExternal():
					newMap [genLink] = linkWebsite
		# Recursively crawl for each link if not at maxDepth
		for link in newMap.keys():
			linkWebsite = newMap [link]
			websiteMap [link] = linkWebsite
			if depth < maxDepth:
				linkWebsite.crawl (websiteMap, maxDepth, rawurllist, depth+1)


class PyArachnid:
	def __init__ (self):
		self.url = None
		self.maxDepth = None
		self.benchmark = False
		self.websiteMap = {}
		self.getTS = lambda ds: \
			("%s"%ds) [0:10].replace ("-", "") + "-" + ("%s"%ds) [11:19].replace (":", "")
		self.rootWebsite = None

	def processOpts (self, opts):
		""" Set attributes according to options """
		print opts
		for opt in opts:
			if opt [0] == "-u":
				self.url = opt [1]
			elif opt [0] == "-d":
				self.maxDepth = int (opt [1])
			elif opt [0] == "-b":
				self.benchmark = True
		try:
			assert self.url is not None
		except AssertionError, ae:
			raise AssertionError ("URL not set with -u option")
		if self.maxDepth is None:
			self.maxDepth = 10

	def crawlSite (self):
		""" Initialize the root node and crawl the site """
		self.rootWebsite = Website (self.url, 0)
		self.rootWebsite.debug()
		self.websiteMap [self.rootWebsite.genURL()] = self.rootWebsite
		self.rootWebsite.crawl (self.websiteMap, self.maxDepth)

	def getMeta (self):
		""" Contents of meta file """
		meta = []
		meta.append ("  root url: %s\n" % self.url)
		meta.append ("  maxdepth: %s\n" % self.maxDepth)
		meta.append (" timestamp: %s\n" % self.getTS (datetime.now()))
		return "".join (meta)

	def fetchMap (self):
		""" Display the site map and write a zipfile with the pages """
		columnize = lambda s, n: s[0:n] + " "*(n - len (s))
		list = self.websiteMap.values()
		siteSorter = lambda a,b: (a.depth > b.depth) and 1 \
			or (a.depth < b.depth) and -1 \
			or ((a.genURL() > b.genURL()) and 1 or (a.genURL() < b.genURL()) and -1)
		list.sort (siteSorter)
		i = 0
		zipfilename = self.rootWebsite.getHost()
		if self.benchmark:
			zipfilename = zipfilename + "-BENCHMARK"
		zipfilename = zipfilename + ".zip"
		zipArchive = zipfile.ZipFile (zipfilename, mode="w", compression=zipfile.ZIP_STORED)
		for site in list:
			i = i + 1
			url = site.genURL()
			url = self.url2Path (url)
			print "%s, %s, %s, %s" % ( \
				columnize ("%d"%i, 3), \
				columnize (url, 100), \
				columnize ("%d"%site.depth, 2), \
				(site.content and len (site.content) or "") )
			if site.content:
				zipArchive.writestr (url, site.content)
		zipArchive.writestr ("meta.txt", self.getMeta())
		zipArchive.close()

	def url2Path (self, url):
		""" Strip the protocol and hostname from the full URI path """
		path = url.replace ("   ", "")
		path = path.replace ("http://", "").replace ("https://", "")
		path = path.replace (self.rootWebsite.getHost(), "")
		path = path.replace ("/", "--")
		if path == "":
			path = self.rootWebsite.getHost()
		return path


def main():
	""" Process options, initialize spider, crawl, display, and generate zip """
	usage = lambda cmd: ("\n	Usage:  %s  {-b create as a new benchmark }" \
		+ " {-d depth_int}  [-u URL_str]\n") % cmd
	try:
		pa = PyArachnid()
		try:
			pa.processOpts ( getopt.getopt (sys.argv [1:], "bu:d:") [0] )
			pa.crawlSite()
			pa.fetchMap()
		except AssertionError, ae:
			print ae
	except getopt.GetoptError, goe:
		print usage (sys.argv [0])

if len (sys.argv) > 1:
	main()
