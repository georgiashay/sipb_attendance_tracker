#!/usr/bin/python3
from . import operations
from .minutes_parse_utils import get_members_and_keyholders
import datetime
import json
from enum import Enum
import re
import os
import json

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

def get_attendance_information(attendee):
	members, keyholders, aliases = get_members_and_keyholders()
	attendee_names = [attendee]
	if attendee in aliases:
		attendee_names.append(aliases[attendee])
	elif attendee in aliases.values():
		attendee_names.extend(alias for alias in aliases if aliases[alias] == attendee)
	
	options = {
		"attendee": attendee_names
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

	return {
		"record": json_records,
		"summary": attendance_summary(json_records),
		"by_month": split_by_month(json_records),
		"active": is_active(json_records),
		"total_attended": get_num_meetings_attended(json_records),
		"attendee_type": get_attendee_type(attendee)
	}

term_names = ["SUMMER", "FALL", "IAP", "SPRING"]

def attendance_percent(attendance_list):
	total_meetings = len(attendance_list)
	attended = sum(record["attended"] for record in attendance_list)
	if total_meetings != 0:
		percent = str(round((attended*100)/total_meetings, 1)) + "%"
	else:
		percent = "N/A"
	return (attended, total_meetings, percent)

def percent_string(percent_tuple):
	return str(percent_tuple[0]) + "/" + str(percent_tuple[1]) + " (" + percent_tuple[2] + ")"

def combine_percents(pt1, pt2):
	total_meetings = pt1[1] + pt2[1]
	attended = pt1[0] + pt2[0]
	if total_meetings != 0:
		percent = str(round((attended * 100)/total_meetings, 1)) + "%"
	else:
		percent = "N/A"
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

def split_by_month(attendance_record):
	term = "NONE"
	years = {}
	for year in attendance_record:
		months = {}
		for record in attendance_record[year]:
			if record["type"] == "marker":
				sem, marker_type = record["name"].split("_")
				if marker_type == "END":
					term = "NONE"
				else:
					term = sem
			else:
				month = datetime.datetime.strptime(record["date"], "%Y-%m-%d").date().month
				if month in months:
					months[month].append({**record, "term": term})
				else:
					months[month] = [{**record, "term": term}]
		years[year] = months
	return years


def is_active(attendance_record):
	all_attendance = [record for year in attendance_record for record in attendance_record[year] if record["type"] == "meeting"]
	active_cutoff = datetime.date.today() - datetime.timedelta(days=30)
	attendance_after_cutoff = [record for record in all_attendance if datetime.datetime.strptime(record["date"], "%Y-%m-%d").date() >= active_cutoff and record["attended"]]
	if len(attendance_after_cutoff):
		return True
	else:
		return False

def get_num_meetings_attended(attendance_record):
	all_attendance = [record for year in attendance_record for record in attendance_record[year] if record["type"] == "meeting" and record["attended"]]
	return len(all_attendance)

def get_attendee_type(attendee):
	members, keyholders, aliases = get_members_and_keyholders()
	if attendee in keyholders:
		return "keyholder"
	elif attendee in aliases:
		if aliases[attendee] in keyholders:
			return "keyholder"
		elif aliases[attendee] in members:
			return "member"
	elif attendee in members:
		return "member"
	return "guest"

def get_all_attendance_records():
	members, keyholders, aliases = get_members_and_keyholders()
	attendees = operations.get_attendees()
	records = {}
	for attendee in attendees:
		if attendee not in aliases:
			records[attendee] = get_attendance_information(attendee)
	for alias in aliases:
		if aliases[alias] in records:
			records[alias] = records[aliases[alias]]
	return [{'attendee': attendee, **records[attendee]} for attendee in records]
	
