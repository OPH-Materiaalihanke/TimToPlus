
"""
Course specific info, FILL IN
"""
def lang():
    return "fi"

def course_open():
    return '2016-06-01'

def course_close():
    return '2020-06-06'

def project():
    return 'Lukiomateriaalit'

def author():
    return 'Milla Lohikainen'

def copyright():
    return  f'2019, {author()}'

def course_name():
    return "MAA3 - Geometria"


# Content ids are the TIMs ids for the documents, and the name of the file. Insert them here in correct order
# File name is the last section of the url of the tim page, or the first short name in manage view. ID can be found
# in the Translations and copies block. If you leave id as 0, the file won't be downloaded, and you have to make
# the filename.md file yourself
#
# If the content is in a separate file, but should be considered part of a chapter, put it in add_in list, at the
# appropriate spot. Keep both list equally long! Mulpiple files for the same chapter can be inserted in the inner []
# braces
#
def content_ids():
    return [
        ("maa3", 182247),
        ("kuvioiden-yhdenmuotoisuus", 186905),
        ("kolmioiden-geometriaa" ,187134),
        ("monikulmioiden-pinta-aloja", 187207),
        ("ympyra", 187208),
        ("avaruusgeometria", 187209)
    ]

def add_in_ids():
    return [
        [("",0),],
        [("kuvioiden-yhdenmuotoisuus-tehtavia",186907),],
        [("kolmioiden-geometriaa-tehtavia",187532),],
        [("monikulmioiden-pinta-aloja-tehtavia",187546),],
        [("ympyra-tehtavia",187540),],
        [("avaruusgeometriaa-tehtavia",187571),],
    ]

# The main folder of the course, where the main site is situated, without last '/'
view_folder = "https://tim.jyu.fi/view/tau/toisen-asteen-materiaalit/matematiikka/geometria"
