# This file extracts the attendees (four different types) from a minutes file

import re
import os
import json
import datetime
from preprocessing_exceptions import process_exception
from operations import add_attendance_record
from logging import log

# File that lists members (keyholders) and prospectives (members)
members_path = '/afs/sipb.mit.edu/admin/text/members/members_and_prospectives'

# Indicators in an attendee list that should be removed as they are not attendee names/kerberoses
REMOVED_INDICATORS = ["(Google Hangouts)!","Hangouts:","'()","(by phone)", " -"]
# Characters that separate attendees in a list (other than the space character, which is considered automatically)
SEPARATION_INDICATORS = ["\n", ",", "|"]

# Different phrases that appear at the start of a meeting
START_MEETING_TITLES = [
	"MEETING_START",
	"Administrivia",
	"Officer Reports?",
	"Discussion",
	"Special Meeting",
	"General Introductions",
	"Propsective Introductions",
	"New Prospectives? Introductions",
	"ADMINISTRIVIA",
	"IT@MIT Presentation",
	"Table of Contents"
]

# Regex that finds the start of a meeting (the phrase must occur in a line with only whitespace before it)
# START_MEETING_STRING = "|".join("(^|\n)\s*" + title for title in START_MEETING_TITLES)
START_MEETING_STRING = "|".join(START_MEETING_TITLES)

# Seniority order of member types, used to determine which to mark an attendee as if they appear multiple times
SENIORITY_ORDER = ["associate_keyholders", "keyholders", "members", "guests"]


def split_list_by(lst, sepfunc, includesep):
	"""
	Splits a list based on separators

	lst: The list to split
	sepfunc: When applied to an element, should be True if it is a separator element
	includesep: True if the separator elements should be included in the returned blocks
	"""
	blocks = []
	block = []
	for elem in lst:
		if sepfunc(elem):
			if includesep:
				block.append(elem)
			blocks.append(block)
			block = []
		else:
			block.append(elem)
	if len(block):
		blocks.append(block)
	return blocks


# The end of an attendee block is marked by either:
# 	1) One of the known "meeting start" strings, OR
#	2) A double newline (which must not be followed by a token)
STOP_TOKEN = '\n\s*(' + START_MEETING_STRING + ')|(\n\n\s*\w+)'
# The start of an attendee block is marked by a line containing
# "Minutes of the [SIPB/SIPB Special/etc] Meeting"
START_TOKEN = '(^|\n)\s*Minutes of the [\w ]+ Meeting'

def token_generator(tokens, minutes):
	"""
	Generates blocks of attendee tokens.  Most minutes will only have one block, but there are 
	exceptions with multiple attendee blocks, such as a meeting within a meeting.

	tokens: A mapping of token types (keyholders, associate_keyholders, members, guests) to
			regexes which define where a list of that type of attendees starts.
	minutes: A string containing the meeting minutes to parse

	return: A list of tuples (token_type, start, end) where token_type is the type of attendee
			token, and start and end are the start and end positions of that token.  Each
			block returned by this generator will contain a final token with token_type 
			stop that indicates where the block ends.  Tokens are indicators of where attendee
			lists are, defined by the regex and the start/stop tokens above.
	"""
	# Cursor in the minutes, current position to search from
	current_index = 0
	# Stores the regex match to the start of the next block of attendee tokens,
	# which not exist (be None)
	next_block = True

	# Start the cursor after the first start token (which may be the start of the minutes,
	# if no such token is found
	first_block = re.search(START_TOKEN, minutes[current_index:])
	
	if first_block:
		current_index = first_block.end(0)

	# Continue yielding blocks while there are blocks found
	while next_block:
		# Find the next batch of tokens starting at the cursor
		matches = [ (token_type, re.search(tokens[token_type], minutes[current_index:])) for token_type in tokens]

		# Find the beginning of the next block
		next_block = re.search(START_TOKEN, minutes[current_index:])
		
		if next_block:
			next_block_index = next_block.start(0)
		else:
			next_block_index = len(minutes[current_index:])

		# Only consider tokens before the start of the next block
		tokens_in_block = [ (token_type, match.group(0), match.start(0), match.end(0)) \
							for token_type, match in matches if match and match.end(0) < next_block_index ]

		# Adjust the indices, taking into account the cursor position
		tokens_in_block = [ (token_type, match, start + current_index, end + current_index) \
							for token_type, match, start, end in tokens_in_block]

		# Remove whitespace from the matches
		tokens_in_block = [ (token_type, start + len(match)-len(match.lstrip()), end - (len(match) - len(match.rstrip()))) \
							for token_type, match, start, end in tokens_in_block ]

		# Sort the tokens by position
		tokens_in_block.sort(key=lambda t: (t[1], t[2]))

		if len(tokens_in_block):
			# Look for a stop codon after the last attendee token and before the start of the
			# next block
			last_token_index = tokens_in_block[-1][2]
			stop_match = re.search(STOP_TOKEN, minutes[last_token_index:next_block_index+current_index])
			
			if stop_match:
				# Append the stop token and return it
				tokens_in_block.append(('stop', \
										last_token_index + stop_match.start(0), \
										last_token_index + stop_match.end(0)))
				yield tokens_in_block
				
				if next_block:
					# Move the cursor to the start of the next block, after the start token 
					current_index += next_block.end(0)
					
			else:
				# There should always be a stop codon
				raise ValueError("Could not find end of attendee block")

		else:
			# No attendees found, move to the next block
			if next_block:
				current_index += next_block.end(0)

class AttendeeExtractor:
	"""
	Extracts attendees from a minutes string
	"""
	def __init__(self, keyholders, associate_keyholders, members, guests):
		# Initialize regex for token types
		self.attendee_types = {
			'keyholders': keyholders,
			'associate_keyholders': associate_keyholders,
			'members': members,
			'guests': guests
		}

	def get_attendees(self, minutes, f):
		"""
		Parse a minutes file to extract the attendees based on the attendee regexes

		minutes: A minutes string to parse
		f: the name of the minutes file, for logging purposes
		"""

		# Get the blocks of attendee tokens
		block_generator = token_generator(self.attendee_types, minutes)
		blocks = [block for block in block_generator]

		# Initialize the attendees
		attendees = {
			'keyholders': set(),
			'associate_keyholders': set(),
			'members': set(),
			'guests': set()
		}

		for block in blocks:
			# Only extract attendee lists after attendee tokens, not stop tokens
			for i, (token_type, start_pos, end_pos) in enumerate(block[:-1]):
				# Extract attendee string between the end of the current token 
				# (e.g., after "Student keyholders:") and the start of the 
				# next token
				attendee_string = minutes[end_pos:block[i+1][1]]
				
				# Remove extraneous indicators that are not attendees
				for indicator in REMOVED_INDICATORS:
					attendee_string = attendee_string.replace(indicator, "")

				# Turn all separation indicators (",", " ", "|", etc) into spaces
				for indicator in SEPARATION_INDICATORS:
					attendee_string = attendee_string.replace(indicator, " ")
			
				# Split into attendees on spaces
				these_attendees = attendee_string.split()
				attendees[token_type] |= set(these_attendees)
		
		# If an attendee is in multiple attendee lists, choose the oldest type
		for member in [member for attendee_type in attendees for member in attendees[attendee_type]]:
			in_group = [member in attendees[attendee_type] for attendee_type in SENIORITY_ORDER]
			first_type_index = in_group.index(True)
			for i in range(first_type_index + 1, len(in_group)):
				if in_group[i]:
					attendees[SENIORITY_ORDER[i]].remove(member)

		return attendees

class Format:
	"""
	Represents a minutes format - i.e. the format for the minutes file name 
	and for the attendee indicators (e.g. "Associate keyholders:")
	"""

	def __init__(self, startdate, enddate, dateformat, attendees):
		"""
		Construct a new format
		
		startdate: The date which the format first started being used
		enddate: The last date which the format was used; can be None to indicate the format 
					is still in use
		dateformat: A regex with the date format for the minutes filename; contains named
					capturing groups for year, month and day
		attendees: A dictionary mapping attendee types (keyholders, associate_keyholders,
					members, guests) to regex expressions that match before the
					start of the associated attendee lists
		"""
		self.startdate = startdate
		self.enddate = enddate
		self.dateformat = re.compile(dateformat)
		self.attendees = attendees

	def get_date(self, file):
		match = self.dateformat.fullmatch(file)
		if match:
			# Extract date parameters from filename
			date_dict = match.groupdict()
			year = int(date_dict['year'])
			month = int(date_dict['month'])
			day = int(date_dict['day'])
			date = datetime.date(year, month, day)
			return date
		else:
			return None

	def is_in_range(self, file):
		date = self.get_date(file)
		if date:
			if self.enddate is not None:
				# Check if date is in range
				return self.startdate <= date <= self.enddate
			else:
				# Format still in use, check if format is in use yet
				return self.startdate <= date
		else:
			return False

	def get_attendees(self, file):
		with open(file, 'r', encoding="latin-1") as f:
			# Read minutes
			minutes = f.read()
			# Process any exceptions first
			minutes = process_exception(os.path.basename(file), minutes)
			# Extract attendees
			return self.attendees.get_attendees(minutes, file)

# Two formats in use since 2010
FORMATS = [
	Format(datetime.date(2010,1,4), \
			datetime.date(2017,5,22), \
			'minutes\.(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})', \
			AttendeeExtractor('Voting members:', \
			 					'Associate members:', \
								'Prospectives:', \
								'Guests:')),
	Format(datetime.date(2017,5,29), \
			None, \
			'minutes\.(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})', \
			AttendeeExtractor('Student keyholders:', \
								'Associate keyholders:', \
								'Members:', \
								'Guests:'))
]

def get_members_and_keyholders():
	"""
	Read the members_and_prospectives file to extract members and keyholders
	"""

	# Read members and prospectives file
	with open(members_path) as f:
		lines = f.readlines()

	# Get non-commented lines
	real_lines = [line for line in lines if len(line.strip()) and line.strip()[0] != '#']

	members = set()
	keyholders = set()
	# Maps aliases to kerberoses 
	aliases = {}

	# Read lines and add to relevant structure
	for line in real_lines:
		parts = line.split()
		if parts[1] == 'member':
			keyholders.add(parts[0])
		elif parts[1] == 'prospective' or parts[1] == 'propsective':
			members.add(parts[0])
		elif len(parts) == 2:
			aliases[parts[0]] = parts[1]

	return members, keyholders, aliases


def get_attendance(files):
	"""
	Get attendance from a list of files

	files: mapping of directories to filenames in those directories which contain minutes to
	get the attendance from
	"""

	# Mapping of dates to attendance dictionaries, which map attendee types to sets of attendees
	attendance = {}

	# Loop over all files
	for direc in files:
		for file in files[direc]:
			# Loop over all formats to see which one the file falls under
			for format in FORMATS:
				if format.is_in_range(file):
					# Get attendees for this file
					attendees = format.get_attendees(os.path.join(direc, file))
					date = format.get_date(file)
					attendance[date] = attendees
					# Don't check other formats
					break

	# Uncomment to send attendance results to attendance.json file
	# j = { str(date) : { mem_type: list(attendance[date][mem_type]) for mem_type in attendance[date]} for date in attendance }
	# with open('attendance.json', 'w') as f:
	# 	json.dump(j, f, indent=4)

	return attendance

# Mapping of attendee types so their database values
ATTENDEE_TYPES = {
        "associate_keyholders": "ASSOCIATE_KEYHOLDER",
        "keyholders": "STUDENT_KEYHOLDER",
        "members": "MEMBER",
        "guests": "GUEST"
}

def add_to_db(attendance):
	"""
	Add attendance information to the database
	
	attendance: Dictionary of dates mapping to attendance information for the meeting on that date,
				which are dictionaries mapping attendee types to sets of attendees
	"""

	# Get list of members and keyholderes
	members, keyholders, aliases = get_members_and_keyholders()
	
	# Go through each attendee
	for date in attendance:
		log("Adding attendance for " + str(date))
		for member_type in attendance[date]:
			log("Adding attendance for " + str(len(attendance[date][member_type])) + " " + member_type)
			for member in attendance[date][member_type]:
				# By default, no manual inspection is required
				inspection_required = "NONE"
				
				# True if the attendee is an alias to a kerberos listed as a keyholder
				aliased_keyholder = member in aliases and aliases[member] in keyholders

				if member_type == "associate_keyholders" or member_type == "keyholders":
					if member not in keyholders and not aliased_keyholder:
						if member in members:
							# Attendee is a member, but was listed as a keyholder
							inspection_required = "WRONG_TYPE"
						else:
							# Attendee not found in file, but was listed as a keyholder
							inspection_required = "NOT_FOUND"
                
				elif member_type == "members":
					# Inspection not required if listed as member but are actually a keyholder, since
					# minutes could be from prior to keyholdership
					if member not in members and member not in keyholders and not aliased_keyholder:
						# Attendee not found in file, but was listed as a member
						inspection_required = "NOT_FOUND"
                
				# Add to the database
				add_attendance_record(date, member, ATTENDEE_TYPES[member_type], inspection_required)
				log(addto="attendance records added", addval=1)
	
	log(logsum="attendance records added")
