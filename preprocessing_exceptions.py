# This file replaces text in order to preprocess minutes that don't follow the standard format,
# or have typos

# Replace all instances of text with a replacement
REPLACE = 0
# Start meeting prior to a specific text
START_MEETING = 1

EXCEPTIONS = {
    'minutes.2013-06-17': [
        (REPLACE, 'Full members:', 'Voting members:')
    ],
    'minutes.2013-09-23': [
        (REPLACE, 'Prospective:', 'Prospectives:')
    ],
    'minutes.2013-09-30': [
        (REPLACE, 'Prospective:', 'Prospectives:')
    ],
    'minutes.2014-10-13': [
        (REPLACE, 'Prospective members:', 'Prospectives:'),
		(REPLACE, 'vasilvv: Today we\'ll have membership election for dzaefn.', '')
	],
    'minutes.2014-10-20': [
        (REPLACE, 'Members:', 'Voting members:')
    ],
    'minutes.2017-06-06': [
        (REPLACE, 'Prospectives:', 'Members:')
    ],
    'minutes.2019-10-14': [
        (REPLACE, 'Members:,', 'Members:')
    ],
    'minutes.2010-04-14': [
        (START_MEETING, 'jhamrick: I move')
    ],
    'minutes.2010-06-28': [
        (START_MEETING, 'jhamrick: \nToday')
    ],
    'minutes.2011-08-29': [
        (REPLACE, 'Adminstrivia', 'Administrivia')
    ],
    'minutes.2011-09-05': [
        (REPLACE, 'Adminstrivia', 'Administrivia')
    ],
    'minutes.2018-12-24': [
        (START_MEETING, 'mtheng: Welcome')
    ],
    'minutes.2018-12-31': [
        (START_MEETING, 'dzaefn: Welcome')
    ],
    'minutes.2020-02-24': [
        (REPLACE, 'asadeno', 'asedeno')
    ],
    'minutes.2020-01-06': [
        (REPLACE, 'mwtheng', 'mtheng')
    ],
    'minutes.2019-12-09': [
        (REPLACE, 'amanti', 'amanit')
    ],
    'minutes.2019-11-25': [
        (REPLACE, 'amanti', 'amanit'),
        (REPLACE, 'valentin', 'vchuravy')
    ],
    'minutes.2019-10-28': [
        (REPLACE, 'amanti', 'amanit')
    ],
    'minutes.2019-10-21': [
        (REPLACE, 'aglasgal', 'glasgall')
    ],
    'minutes.2019-10-07': [
        (REPLACE, 'amanti', 'amanit')
    ],
    'minutes.2019-09-16': [
        (REPLACE, 'rdhin', 'rihn'),
        (REPLACE, 'mosimo', 'maximo')
    ],
    'minutes.2019-09-16': [
        (REPLACE, 'mosimo', 'maximo')
    ],
    'minutes.2019-09-09': [
        (REPLACE, 'mosimo', 'maximo')
    ],
    'minutes.2019-09-02': [
        (REPLACE, 'nambranth', 'nambrath')
    ],
    'minutes.2019-04-01': [
        (REPLACE, 'zachpi', 'zackpi')
    ],
    'minutes.2019-03-11': [
        (REPLACE, 'mnguyen', 'mwnguyen')
    ],
    'minutes.2019-02-25': [
        (REPLACE, 'aathyle', 'aathalye')
    ],
    'minutes.2019-02-04': [
        (REPLACE, 'merolith', 'merolish')
    ],
    'minutes.2019-01-07': [
        (REPLACE, 'capslock', 'rsthomp')
    ],
    'minutes.2018-08-13': [
        (REPLACE, 'anderssk', 'andersk')
    ],
    'minutes.2018-08-06': [
        (REPLACE, 'wqian', 'wqian94')
    ],
	'minutes.2014-08-18': [
		(REPLACE, '(late)', '')
	],
	'minutes.2014-08-25': [
		(REPLACE, 'jhawk)', 'jhawk')
	],
	'minutes.2016-08-29': [
		(REPLACE, 'Prospective Members', 'Prospectives')
	],
	'minutes.2017-06-12': [
		(REPLACE, 'Associate Keyholders', 'Associate keyholders')
	],
	'minutes.2013-10-07': [
		(REPLACE, 'Prosepective Prospective', '')
	],
	'minutes.2013-06-03': [
		(START_MEETING, 'Motion to recess until')
	],
	'minutes.2013-06-24': [
		(START_MEETING, 'dzaefn: Hi, I am Ray Hua')
	],
	'minutes.2014-11-17': [
		(START_MEETING, 'vasilvv: today we\'ll have elections')
	],
	'minutes.2016-10-10': [
		(START_MEETING, '[Secretary halt]')
	]
    # There are further mispellings; only cataloged through 2018
}

def process_exception(file, minutes):
    """
    Modifies lines for preprocessing if the file
    requires it
    """
    if file in EXCEPTIONS:
        for exception in EXCEPTIONS[file]:
            if exception[0] == REPLACE:
                minutes = minutes.replace(exception[1], exception[2])
            elif exception[0] == START_MEETING:
                minutes = minutes.replace(exception[1], "MEETING_START\n" + exception[1])
        return minutes
    else:
        return minutes
