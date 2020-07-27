import os
import json
import mysql.connector
from .logging import log

# Flag to disable writing to database (for debugging purposes)
NO_WRITE_DB = False

# Load in database authentication
# Contains values:
#	- user
#	- password
db_auth_file = "db_auth.json"
db_auth_file = os.path.join(os.path.dirname(__file__), db_auth_file)
with open(db_auth_file, "r") as f:
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

	returns: rows matching the query, which are dictionaries containing the requested data fields
	"""
	# Execute query
	cur = connection.cursor(dictionary=True)
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

def construct_where_clause(options):
	"""
	Constructs a where clause for the attendance table based on a dictionary
	of options

	Supported options:

	attendance table
	================
	- attendee: query for only this attendee (or a list of attendees)
	- start_date: query for meetings on this date or after
	- end_date: query for meetings on this date or before
	- attendee_type: query for only this type of attendee
	- inspection_required: query for only this type of inspection required

	contribution table
	==================
	- contributor: query for only this contributor (or a list of contributors)
	- submitter: query for only this submitter (or a list of submitters)
	"""
	if options is None:
		return "", {}

	selectors = []
	values = {}

	def one_value_or_list(key):
		if isinstance(options[key], list):
			selectors.append(key + " IN (" + ", ".join(["%(" + key + "_" + str(n) + ")s" for n in range(len(options[key]))]) + ")")
			for i, attendee in enumerate(options[key]):
				values[key + "_" + str(i)] = attendee
		elif isinstance(options[key], str):
			selectors.append(key + " = %(" + key + ")s")
			values[key] = options[key]

	# Construct where clause and values list from options
	if "attendee" in options:
		one_value_or_list("attendee")
	if "start_date" in options:
		selectors.append("meeting_date >= %(start_date)s")
		values["start_date"] = str(options["start_date"])
	if "end_date" in options:
		selectors.append("meeting_date <= %(end_date)s")
		values["end_date"] = str(options["end_date"])
	if "attendee_type" in options:
		selectors.append("attendee_type = %(attendee_type)s")
		values["attendee_type"] = options["attendee_type"]
	if "inspection_required" in options:
		selectors.append("inspection_required = %(inspection_required)s")
		values["inspection_required"] = options["inspection_required"]

	if "contributor" in options:
		one_value_or_list("contributor")
	if "submitter" in options:
		one_value_or_list("submitter")

	if "project_name" in options:
		selectors.append("project_name = %(project_name)s")
		values["project_name"] = options["project_name"]

	# AND together the where clauses
	query_where = "(" +  " AND ".join(["(" + selector + ")" for selector in selectors]) + ")"

	# Add where clause if it exists
	if query_where:
		return "WHERE " + query_where, values
	else:
		return "", values

def get_attendance_records(fields=None, clauses=None, options=None):
	"""
	Get attendance records based on a dictionary of options
	
	fields: List of fields to return, all if None
	clauses: A list of additional clauses, such as ORDER BY
	options: Dictionary of options as described above to fiter the search
	"""

	field_string = "*"
	if fields is not None:
		field_string = ", ".join(fields)

	query = "SELECT " + field_string + " FROM attendance "
	
	where_clause, values = construct_where_clause(options)
	query += where_clause

	if clauses is not None:
		query += " " + " ".join(clauses)

	query += ";"
	# Get data from database
	return get_data(query, values)


def get_meeting_dates(options=None):
	"""
	Get list of meeting dates based on a dictionary of options
	"""
	# Select meeting date from database
	query = "SELECT meeting_date FROM attendance "
	where_clause, values = construct_where_clause(options)
	query += where_clause
	query += " GROUP BY meeting_date"
	
	rows = get_data(query, values)
	
	# Meeting date is first value in tuple returned from database
	return [row["meeting_date"] for row in rows]

def get_attendees(options=None):
	"""
	Get list of attendees based on a dictionary of options
	"""

	# Selects attendees from databse
	query = "SELECT attendee FROM attendance GROUP BY attendee;"
	where_clause, values = construct_where_clause(options)
	query += where_clause

	rows = get_data(query, values)
	return [row["attendee"] for row in rows]

def get_contributions(options=None, fields=None, clauses=None):
	"""
	Get list of contributions based on a dictionary of options
	"""	
	field_string = "*"
	if fields is not None:
		field_string = ", ".join(fields)

	query = "SELECT " + field_string + " FROM contributions "
	
	where_clause, values = construct_where_clause(options)
	query += where_clause

	if clauses is not None:
		query += " " + " ".join(clauses)

	query += ";"
	# Get data from database
	return get_data(query, values)

def add_contribution(contributor, project, contribution, submitter):
	values = (contributor, project, contribution, submitter)
	query = ("INSERT INTO contributions"
			 "(contributor, project, contribution, submitter) "
			 "values (%s, %s, %s, %s)")
	
	set_data(query, values)

def get_projects(options=None, fields=None, clauses=None):
	"""
	Get projects from a list of options
	"""
	field_string = "*"
	if fields is not None:
		field_string = ", ".join(fields)

	query = "SELECT " + field_string + " FROM projects "
	
	where_clause, values = construct_where_clause(options)
	query += where_clause

	if clauses is not None:
		query += " " + " ".join(clauses)

	query += ";"
	# Get data from database
	return get_data(query, values)

def add_project(name):
	"""
	Add a project with a given name
	"""
	values = (name,)
	query = ("INSERT INTO projects"
				"(project_name) "
				"values (%s)")
	
	set_data(query, values)
