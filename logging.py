import datetime
LOG = True
PRINTTIME = True

data = {}

def log(string=None, addto=None, addval=None, clear=None, logsum=None):
	if LOG:
		prefix = ""
		if PRINTTIME:
			prefix = str(datetime.datetime.now())

		if addto is not None and addval is not None:
			if addto in data:
				data[addto] += addval
			else:
				data[addto] = addval

		if clear is not None:
			if clear in data:
				del data[clear]

		if logsum is not None:
			if logsum in data:
				s = data[logsum]
			else:
				s = 0
			print(prefix + ": [TOTAL] " + logsum + " = " + str(s))

		if string is not None:
			s = str(string)
			print(prefix + ": " + s)

