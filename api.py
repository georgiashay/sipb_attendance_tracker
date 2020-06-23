#!/usr/bin/python3
import operations
import datetime
import json
from enum import Enum
from abc import abstractmethod
import re
import os
import json

endpoints = {}

class PathPart:
	@abstractmethod
	def matches(self, pathpart):
		pass

	@abstractmethod
	def parameters(self, string):
		pass

class PathVar:
	def __init__(self, var):
		self.var = var[1:-1]
	
	def matches(self, string):
		return True

	def parameters(self, string):
		return { self.var: string }
	
	def __eq__(self, other):
		return self.var == other.var

	def __hash__(self):
		return hash(self.var)

class PathConst:
	def __init__(self, const):
		self.const = const

	def matches(self, string):
		return self.const == string
	
	def parameters(self, string):
		return {}

	def __eq__(self, other):
		return self.const == other.const

	def __hash__(self):
		return hash(self.const)

class Endpoint:
	var_matcher = re.compile("<[^>]+>")

	def __init__(self, endpoint_string):
		path_parts = endpoint_string.split("/")[1:]
		self.path = []
		for path_part in path_parts:
			if self.is_path_var(path_part):
				self.path.append(PathVar(path_part))
			else:
				self.path.append(PathConst(path_part))

	@staticmethod
	def is_path_var(pathpart):
		return Endpoint.var_matcher.match(pathpart) is not None

	def matches(self, path):
		path_parts = path.split("/")[1:]
		
		if len(self.path) !=  len(path_parts):
			return False

		return all(self.path[i].matches(path_parts[i]) for i in range(len(self.path)))

	def parameters(self, string):
		params = {}
		path_parts = string.split("/")[1:]
		
		for sub_path, path_part in zip(self.path, path_parts):
			params.update(sub_path.parameters(path_part))

		return params

	def __eq__(self, other):
		if len(self.path) != len(other.path):
			return False

		else:
			return all(self.path[i] == other.path[i] for i in range(len(self.path)))
	
	def __hash__(self):
		return sum(hash(path_part) for path_part in self.path)

def register_endpoint(path, content_type):
	def wrap(f):
		endpoint = Endpoint(path)
		endpoints[endpoint] = (f, content_type)

		return f
	
	return wrap

def get_academic_year(meeting_date):
	if meeting_date.month >= 6:
		return (meeting_date.year, meeting_date.year+1)
	else:
		return (meeting_date.year-1, meeting_date.year)	

def split_by_academic_year(attendance):
	years = {}
	year = []
	last_academic_year = None
	
	for meeting_date, attended in attendance:
		this_academic_year = get_academic_year(meeting_date)
		if this_academic_year != last_academic_year:
			if year:
				years[last_academic_year] = year
			year = [(meeting_date, attended)]
		else:
			year.append((meeting_date, attended))

		last_academic_year = this_academic_year

	if year:
		years[last_academic_year] = year
	
	return years

class Marker(Enum):
	SUMMER_START = 0
	SUMMER_END = 1
	FALL_START = 2
	FALL_END = 3
	IAP_START = 4
	IAP_END = 5
	SPRING_START = 6
	SPRING_END = 7

def insert_marker_before(records, date, marker):
	try:
		marker_pos = next(i for i, record in enumerate(records) if isinstance(record, tuple) and record[0] >= date)
		records.insert(marker_pos, marker)
	except:
		records.append(marker)

def insert_marker_after(records, date, marker):
	try:
		marker_pos = next(i for i, record in enumerate(records) if isinstance(record, tuple) and record[0] > date)
		records.insert(marker_pos, marker)
	except:
		records.append(marker)

def add_semester_markers(records, year):
	january = [datetime.date(year[1], 1, n) for n in range(1, 32)]
	first_monday = next(day for day in january if day.weekday() == 0)
	start_of_spring = first_monday + datetime.timedelta(weeks=4)
	end_of_iap = start_of_spring - datetime.timedelta(days=3)
	
	records.insert(0, Marker.SUMMER_START)
	insert_marker_after(records, datetime.date(year[0], 8, 20), Marker.SUMMER_END)
	insert_marker_before(records, datetime.date(year[0], 9, 1), Marker.FALL_START)
	insert_marker_after(records, datetime.date(year[0], 12, 20), Marker.FALL_END)
	insert_marker_before(records, datetime.date(year[1], 1, 1), Marker.IAP_START)
	insert_marker_after(records, end_of_iap, Marker.IAP_END)
	insert_marker_before(records, start_of_spring, Marker.SPRING_START)
	insert_marker_after(records, datetime.date(year[1], 5, 20), Marker.SPRING_END)

	return records

@register_endpoint("/attendance_record/<attendee>", "json")
def get_attendance_information(attendee):
	options = {
		"attendee": attendee
	}

	clauses = [
		"ORDER BY meeting_date ASC"
	]

	meeting_dates = operations.get_meeting_dates()
	attendance_records = operations.get_attendance_records(clauses=clauses, options=options)

	attendance = []

	i = 0
	for meeting_date in meeting_dates:
		if i < len(attendance_records) and meeting_date == attendance_records[i]['meeting_date']:
			attendance.append((meeting_date, True))
			i += 1
		else:
			attendance.append((meeting_date, False))	

	records_by_year = split_by_academic_year(attendance)
	years = sorted(list(records_by_year.keys()))

	for year in years:
		if any(attended for _, attended in records_by_year[year]):
			break
		else:
			del records_by_year[year]
	
	records_by_year = { year: add_semester_markers(records_by_year[year], year) for year in records_by_year }
	
	json_records = {}
	for year in records_by_year:
		year_string = str(year[0]) + "-" + str(year[1])
		json_records[year_string] = []
		for record in records_by_year[year]:
			if isinstance(record, Marker):
				json_records[year_string].append({
					'type': 'marker',
					'name': record.name
				})
			else:
				json_records[year_string].append({
					'type': 'meeting',
					'date': str(record[0]),
					'attended': record[1]
				})

	return json_records

term_names = ["SUMMER", "FALL", "IAP", "SPRING"]

def attendance_percent(attendance_list):
	total_meetings = len(attendance_list)
	attended = sum(record["attended"] for record in attendance_list)
	if total_meetings != 0:
		percent = str(round((attended*100)/total_meetings, 1)) + "%"
	else:
		percent = "N/A%"
	return (attended, total_meetings, percent)

def percent_string(percent_tuple):
	return str(percent_tuple[0]) + "/" + str(percent_tuple[1]) + " (" + percent_tuple[2] + ")"

def combine_percents(pt1, pt2):
	total_meetings = pt1[1] + pt2[1]
	attended = pt1[0] + pt2[0]
	if total_meetings != 0:
		percent = str(round((attended * 100)/total_meetings, 1)) + "%"
	else:
		percent = "N/A%"
	return (attended, total_meetings, percent)

def attendance_summary(attendance_information):
	summary = {}
	for year in attendance_information:
		records = attendance_information[year]
		whole_year = [record for record in records if record["type"] == "meeting"]
		terms = { 'all': whole_year }
		current_term = None
		for record in records:
			if record["type"] == "marker":
				name = record["name"].split("_")
				if current_term is None and name[1] == "START":
					current_term = name[0]
					terms[current_term] = []
				elif current_term is not None and name[1] == "END":
					current_term = None
			elif current_term is not None:
				terms[current_term].append(record)
		
		by_term = { term: attendance_percent(terms[term]) for term in terms }
		summary[year] = by_term
	return summary

semester_colors = {
	"SUMMER": ("lemonchiffon", "gold"),
	"FALL": ("navajowhite", "coral"),
	"IAP": ("thistle", "mediumslateblue"),
	"SPRING": ("#C7E884", "limegreen")
}

@register_endpoint("/attendance_record/pretty/<attendee>", "html")
def get_pretty_attendance_record(attendee):
	attendance_record = get_attendance_information(attendee)
	summary = attendance_summary(attendance_record)
	years = sorted(list(attendance_record.keys()))
	
	response = "<html>\n"
	for year in years:
		response += "<h3>" + year + "</h3>\n"
		response += "<p>Overall: " + percent_string(summary[year]["all"]) + "</p>"
		response += "<p>Academic Year: " + percent_string(combine_percents(summary[year]["FALL"], summary[year]["SPRING"])) + "</p>"
		response += "<p>Summer: " + percent_string(summary[year]["SUMMER"]) + "</p>"
		response += "<p>Fall: " + percent_string(summary[year]["FALL"]) + "</p>"
		response += "<p>IAP: " + percent_string(summary[year]["IAP"]) + "</p>"
		response += "<p>Spring: " + percent_string(summary[year]["SPRING"]) + "</p>"
		response += "<table border='1'>\n"
		response += "<tr>\n"
		color = ("lightgray", "gray")
		for record in attendance_record[year]:
			if record["type"] == "marker":
				sem, marker_type = record["name"].split("_")
				if marker_type == "END": 
					color = ("lightgray", "gray")
				else:
					color = semester_colors[sem]
			else:
				response += "<td width='16' bgcolor='" + color[record["attended"]] + "'>\n"
				if record["attended"]:
					response += "P\n"
				else:
					response += "A\n"
				response += "</td>\n"
		response += "</tr>\n"
		response += "</table>\n"
	response += "</html>"
	return response


if "PATH_INFO" in os.environ:
	path = os.environ["PATH_INFO"]
else:
	path = "/attendance_record/pretty/gshay"


for endpoint in endpoints:
	if endpoint.matches(path):
		params = endpoint.parameters(path)
		func, content_type = endpoints[endpoint]
		response = func(**params)
		if content_type == "json":
			print("Content-type: application/json\n")
			print(json.dumps(response))
		elif content_type == "html":
			print("Content-type: text/html\n")
			print(response)
		break



#if __name__ == "__main__":
#	r = get_attendance_information("gshay")
