#!/usr/bin/python

import re, subprocess, sys
import MySQLdb

class URLTester (object):
	"""
	Created to supplement an existing system, this utility tests each web URL
	with ping and a DNS lookup.  Upon failure, it switches to a DNS server
	in a different locale.

	Options
		-t performs test from command line
		-d outputs debug info
		-n uses negative test cases
	"""

	_DB_NAME = "appmgr"
	_DB_HOST = "localhost"
	_DB_USER = "integrator"
	_DB_PASS = "rapid-shallow-breathing"

	_DNS_SERVERS = {
			"us": "72.3.128.240",
			"ca": "132.203.250.10",
			"mx": "201.144.5.43",
			"uk": "212.158.192.2",
			"eu": "195.129.12.122",
			"se": "194.237.142.26",
			"au": "139.134.2.189",
			"kr": "164.124.101.41",
			"tw": "61.220.4.100",
			"in": "202.153.32.3",
		}

	_NUM_PINGS = 2

	_pingFilter = lambda s: (s != "") and not re.match ("---", s)

	def __init__ (self, debugMode=0):
		self.getFlag = lambda success: success and "OK" or "FAIL"
		self.debug = debugMode
		if self.debug:
			print "In Debug Mode."

	def testDNS (self, thePath, useAlt=0):
		""" Use dig to test thePath """
		if self.debug or useAlt:
			digArg = "@%s" % (self._DNS_SERVERS [self._DNS_SERVERS.keys() [useAlt]])
			cmd = ["dig", digArg, "+short", thePath,]
		else:
			cmd = ["dig", "+short", thePath,]
		sp = subprocess.Popen (cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output = sp.communicate()
		if self.debug or useAlt:
			print "	" + reduce (lambda a,b: a+" "+b, cmd),
			print output
			print ""
		lines = output[0].split ("\n")
		success = 0
		for l in lines:
			if re.match (".*[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*.*", l) is not None:
				success = 1
				break
		return success, output

	def testPing (self, thePath, pingCount=5):
		""" Use ping to test thePath """
		cmd = ["ping", "-c", "%d"%pingCount, thePath]
		sp = subprocess.Popen (cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		output = sp.communicate()
		if self.debug:
			print "\n%s\n%s\n" % (cmd, output)
		lines = output[0].split ("\n")
		success = False
		for l in lines:
			if re.match (".* 0% packet loss.*", l):
				success = True
				break;
		return success, output

	def urlRows (self):
		"""
		Get the data from the database
		+---------+--------------+------+-----+---------+-------+
		| Field   | Type         | Null | Key | Default | Extra |
		+---------+--------------+------+-----+---------+-------+
		| path    | varchar(128) | YES  |     | NULL    |       |
		| title   | varchar(128) | YES  |     | NULL    |       |
		| auth    | varchar(128) | YES  |     | NULL    |       |
		| do_test | int(11)      | YES  |     | NULL    |       |
		+---------+--------------+------+-----+---------+-------+
		"""
		conn = MySQLdb.connect (host=self._DB_HOST, \
			user=self._DB_USER, passwd=self._DB_PASS, db=self._DB_NAME)
		cursor = conn.cursor()
		sql = "SELECT path AS domain, title, auth FROM websites_url WHERE do_test=1 ORDER BY domain"
		cursor.execute ( sql )
		rows = cursor.fetchall()
		cursor.close()
		conn.close()
		return rows

	def negativeTestArray (self):
		""" Contains a bad URL to test failure """
		return (
			('www.google.com', 'Google', None),
			('www.altavista.com', 'Alta Vista', None),
			('www.nonono.zz', 'no title', None),
			('www.yahoo.com', 'Yahoo', None),
		)

	def main (self, doNegativeTest=False):
		rows = self.urlRows()
		if self.debug:
			print rows
		if doNegativeTest:
			print "Negative Test Mode Entries:"
			rows = self.negativeTestArray()
			map (lambda s: sys.stdout.write ("	"+s[0]+"	"+s[1]+"\n"), rows)
		if self.debug:
			rows = rows [0:5]
		completedList = []
		for row in rows:
			testDomain, theTitle, theAuth, = re.sub ("/.*", "", row[0]), row[1], row[2]
			if testDomain in completedList:
				continue
			completedList.append (testDomain)
			counter = 0
			dnsSuccess = False
			while not dnsSuccess and counter < len (self._DNS_SERVERS):
				dnsSuccess, dnsOutput = self.testDNS (testDomain, useAlt=counter)
				print "DNS%s  %s	[ %s ]" % ((counter and "%d"%counter or " "),
					testDomain, nu.getFlag (dnsSuccess))
				counter = counter + 1
				if not dnsSuccess:
					print "\n	Failure for single DNS server: ",
					print dnsOutput
					print ""
			counter = 0
			pingSuccess, pingOutput = \
				self.testPing (testDomain, self._NUM_PINGS + counter)
			print "Ping %s	[ %s ]" % (testDomain, nu.getFlag (pingSuccess))
			while (not pingSuccess) and (counter < 3):
				sys.stdout.write ( "\n" )
				for lines in pingOutput:
					map ( lambda l: sys.stdout.write ("	%s\n" % (l)), \
						filter (self._pingFilter, lines.split ("\n")) )
				sys.stdout.write ( "\n" )
				counter = counter + 1
				pingSuccess, pingOutput = \
					self.testPing (testDomain, self._NUM_PINGS + counter)
				print "Ping %s	[ %s ]" % (testDomain, nu.getFlag (pingSuccess))
			sys.stdout.flush()
		result = dnsSuccess and pingSuccess
		if self.debug:
			print "Returning:", result
		return result


if "-t" in sys.argv:
	print "Test URLTester"
	if "-d" in sys.argv:
		nu = URLTester (debugMode=True)
	else:
		nu = URLTester (debugMode=False)
	if not nu.main ("-n" in sys.argv):
		sys.exit (1)
