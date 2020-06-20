import os
import re
import datetime
from minutes_parse_utils import FORMATS, get_members_and_keyholders, get_attendance, add_to_db
from operations import add_attendance_record

# Path to minutes
minutes_path = '/afs/sipb.mit.edu/admin/minutes'
history_path = os.path.join(minutes_path, 'HISTORY')

# Only get attendance history back to 2010 for initial population of database
HISTORY_LIMIT = 2010

def dir_in_range(direc):
	"""
	Checks if a directory name is for minutes in 2010 or after
	
	direc: directory name
	
	returns: matches, year
		- matches: True if the directory is for 2010 or after
		- year: The year the directory represents, or None if it is not a valid minutes
				history directory
	"""

	directory_matcher = re.compile("(?P<year>\d{4})_minutes")
	dir_match = directory_matcher.match(direc)
	
	if dir_match:
		# Extract year from directory
		year = int(dir_match.groupdict()['year'])
		if year >= HISTORY_LIMIT:
			return True, year
		else:
			return False, year
	else:
		# Invalid minutes history directory name
		return False, None

def get_minutes_files():
	"""
	Get all minutes files back to the history limit

	returns: A dictionary mapping from minutes directories to lists of minutes files within those
			 directories
	"""
	files = {}
	# Get files under main minutes directory
	files[minutes_path] = [file for file in os.listdir(minutes_path) if os.path.isfile(os.path.join(minutes_path, file))]
	# Get all minutes history directories
	history_dirs = [direc for direc in os.listdir(history_path) if os.path.isdir(os.path.join(history_path, direc))]
	for history_dir in history_dirs:
		in_range, year = dir_in_range(history_dir)
		# Only consider history directories back to the history limit
		if in_range:
			# Get all files in this history directory, if it's past the history limit
			files[os.path.join(history_path, history_dir)] = [file for file in os.listdir(os.path.join(history_path, history_dir)) if os.path.isfile(os.path.join(history_path, history_dir, file))]

	return files;

if __name__ == "__main__":
	files = get_minutes_files()
	attendance = get_attendance(files)
	add_to_db(attendance)
