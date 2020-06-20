import json
import mysql.connector
from logging import log

# Flag to disable writing to database (for debugging purposes)
NO_WRITE_DB = True

# Load in database authentication
# Contains values:
#	- user
#	- password
with open("db_auth.json", "r") as f:
	db_auth = json.load(f)

# Connect to database
connection = mysql.connector.connect(
		host="sql.mit.edu",
		user=db_auth["user"],
		password=db_auth["password"],
		charset="utf8",
		database="gshay+sipb_attendance")

log("Connected to database")

def get_data(query, data):
	"""
	Get data from the database

	query: A string query, containing %s for any parameters (or %(<param name>)s)
	data: A tuple of parameters, if using %s, or a dictionary of parameters if using %(<param name>)s

	returns: rows matching the query, which come as tuples containing the requested data
	"""
	# Execute query
	cur = connection.cursor()
	cur.execute(query, data)
	# Get rows
	rows = cur.fetchall()
	# Close cursor
	cur.close()
	return rows

def set_data(query, data):
	"""
	Insert data into the database
	"""
	if not NO_WRITE_DB:
		# Only if writing to the database is not disabled
		cur = connection.cursor()
		cur.execute(query, data)
		# Commit the executed query
		connection.commit()
		# Close the cursor
		cur.close()

def add_attendance_record(meeting_date, attendee, attendee_type, inspection_required):
	"""
	Add an attendance record to the database

	meeting_date: The date of the meeting
	attendee: The name/kerberos of the attendee
	attendee_type: The database enum attendee type
	inspection_required: The database enum type indicating whether manual inspection
						is required for this entry
	"""

	data = (meeting_date, attendee, attendee_type, inspection_required)
	query = ("INSERT INTO attendance "
			"(meeting_date, attendee, attendee_type, inspection_required) "
			"VALUES (%s, %s, %s, %s)")

	set_data(query, data)

def get_attendance_records(options):
	"""
	Get attendance records based on a dictionary of options

	Supported options:
	- attendee: query for only this attendee
	- start_date: query for meetings on this date or after
	- end_date: query for meetings on this date or before
	- attendee_type: query for only this type of attendee
	- inspection_required: query for only this type of inspection required
	"""
	query = "SELECT * FROM attendance "
	selectors = []
	values = {}

	# Construct where clause and values list from options
	if "attendee" in options:
		selectors.append("attendee = %s")
		values["attendee"] = options["attendee"]
	if "start_date" in options:
		selectors.append("meeting_date >= %s")
		values.append(options["start_date"])
	if "end_date" in options:
		selectors.append("meeting_date <= %s")
		values.append(options["end_date"])
	if "attendee_type" in options:
		selectors.append("attendee_type = %s")
		values.append(options["attendee_type"])
	if "inspection_required" in options:
		selectors.append("inspection_required = %s")
		values.append(options["inspection_required"])

	# AND together the where clauses
	query_where = " AND ".join(["(" + selector + ")" for selector in selectors])
	
	# Add where clause if it exists
	if query_where:
		query += "WHERE " + query_where

	# Get data from database
	return get_data(query, tuple(values))


def get_meeting_dates():
	"""
	Get list of meeting dates
	"""

	# Select meeting date from database
	query = "SELECT meeting_date FROM attendance"
	data = tuple()
	rows = get_data(query, data)
	# Meeting date is first value in tuple returned from database
	return set([row[0] for row in rows])

