import os
from minutes_parse_utils import FORMATS, get_attendance, add_to_db
from operations import get_meeting_dates
from logging import log

minutes_path = '/afs/sipb/admin/minutes'

def get_minutes_files():
	"""
	Get all minutes files that have not yet been processed, which are under the 
	main minutes directory (recent minutes only)
	"""
	
	# Get meeting dates which have records in the database
	existing_dates = get_meeting_dates()

	files = {}
	files[minutes_path] = []
	
	# Got through each minutes file in the minutes directory
	for file in os.listdir(minutes_path):
		if os.path.isfile(os.path.join(minutes_path, file)):
			for format in FORMATS:
				# Find format of minutes file
				if format.is_in_range(file):
					date = format.get_date(file)
					if date not in existing_dates:
						# Add to list if it has not been recorded yet
						files[minutes_path].append(file)
					break

	for file in files[minutes_path]:
		log("Found unread minutes file " + file)

	return files

if __name__ == "__main__":
	files = get_minutes_files()
	log("Updating attendance for " + str(len(files[minutes_path])) + " files...")
	attendance = get_attendance(files)
	add_to_db(attendance)
	log("Finished updating attendance")
