# This program will download and modificate TIMs markdown files to multiple rst files for A/TUNI+ LMS. Also any
# neccessary new libraries will be downloaded, and changes made to the original coursetemplate from A+.
# User should not have to make any extraneous changes to the template.
#
# All markdowns will create a new module in +, and each 1. and 2. level heading will create a new chapter. All
# downloaded markdowns will be stored in Source folder, and each module to its respective folder.
#
# Before running, ensure that courseinfo.py has correct info and especially the data about the pages in TIM.
# Then copy a cookie from TIM to eväste function below, so curl has permissions to download all texts and images
# from TIM.

# Running this program may take some time, because pandoc will take exponentially longer time with longer markdowns
#
# Author: Valtteri Laaksonen
# email: valtteri.laaksonen@tuni.fi

"""
Used libraries
"""
import os
import re
import shutil
import subprocess
from courseinfo import *
from constructs import *

import time


"""
Check these before running
"""
update = False  # Download all files even if they already exists

publish = False # Wether to translate for local testing, or inputting to the intterwebs. Doesn't really do much,
                # maybe just check the end of file for manually changing few lines instead of full rerun.


# evaste (cookie) is needed to download files and images from TIM.
# In Firefox, this is acquired by enabling Tools->Web Developer->Network, then go to a TIM page you have rights to,
# right click on an element in the list and go to Copy->Copy as cURL. Then paste it to return function and make it a
# single string. Remove the first two "words", until the first '-H'
evaste = (
#        r"ex:copytexthere"
r"-H 'Host: tim.jyu.fi' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Referer: https://tim.jyu.fi/view/tau/toisen-asteen-materiaalit/matematiikka/geometria' -H 'Cookie: session=.eJyNjksOwjAMRO-SdVHpD0o3HCVykkmJ2iRV6sICcXdSISGxY2HZ48_4PYVckDwFBBYDpw2FoKBvMYlBiEJo8pA2RZ9leXd4lExbydGtCAdaGTl5YiRHNDsuFxga4-jcNNFXhJ-l6267Jis5TgjZt6tM012MgSVY1EpXVJszOqVM317a6qRU21t7zHdzfilN1H_S7HWOD82I6MF5lNvU7BTbiiSdEUNftfXrDUXFXWE.XVpzRA.qXW6Mi0Sruj6aGpGz8Gw9OFUbxg; _ga=GA1.2.1762882191.1563259360; XSRF-TOKEN=IjUxZDM1OWRkZWZhZWZlMmJjMWEyZDdlNWJiZDg0OTQxNmJiNDhmZjAi.XVpzRA.gJU9M6fYiQkzxc5D2UkjIXhAWU8' -H 'DNT: 1' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1' -H 'Cache-Control: max-age=0'"
)


"""
Helper functions
"""

plugin_lib = {}

"""Function for translating markdown parts inside plugins, that otherwise wouldn't go through pandoc as-is"""
def do_pandoc(txt, to="rst"):

    txt = check_image(txt)
    txt = re.sub("^'","",re.sub("'$","",txt))
    if txt.startswith("md:"):
        txt = re.sub("md: *", "", txt)
    txt = re.sub("\"", "'", txt)
    txt = txt.replace("\\\\","\\")
    if txt:
        pandc = subprocess.run(["pandoc" ,"-f", "markdown", "-t", to, "--wrap=preserve", "--reference-links"], input=txt, text=True, stdout=subprocess.PIPE)
        txt = pandc.stdout

    return txt


"""Simple calculations for randomised variables, mostly found in mathcheck questions"""
def do_math(line):

    if re.search(r"\[.+,.+\]", line):
        nums = re.findall(r"\d+", line)
        ret = []
        for num in nums:
            ret.append(do_math(num))
            return ret

    line = line.lstrip().rstrip()

    if re.match("^'.*'$", line):
        return line

    if re.search(r"\(.*\)", line):
        line = do_math(re.search(r"\((.*)\)", line).group(1))

    while re.search(r"[\d.]+\*[\d.]+", line):
        line = re.sub(r"([\d.]+)\*([\d.]+)", lambda mtch: str(float(mtch.group(1))*float(mtch.group(2))), line,1)
    while re.search(r"[\d.]+/[\d.]+", line):
        line = re.sub(r"([\d.]+)/([\d.]+)", lambda mtch: str(float(mtch.group(1))/float(mtch.group(2))), line,1)
    while re.search(r"[\d.]+\+[\d.]+", line):
        line = re.sub(r"([\d.]+)\+([\d.]+)", lambda mtch: str(float(mtch.group(1))+float(mtch.group(2))), line,1)
    while re.search(r"[\d.]+-[\d.]+", line):
        line = re.sub(r"([\d.]+)-([\d.]+)", lambda mtch: str(float(mtch.group(1))-float(mtch.group(2))), line,1)

    return round(float(line),1)




exercise_names = []

"""Create a mathcheck question"""
def create_mathcheck(lines):

    global exercise_names
    global plugin_lib

    ex_name = ""
    sets = dict()

    attributes = re.match(r"``` {(.+)}$", lines, re.MULTILINE).group(1).split(" ")

    for attr in attributes:
        if attr.startswith("#"): # Get the name for the exercise, or substitute with id if not unique
            ex_name = re.sub("#","",attr)
            if ex_name in exercise_names:
                ex_name = ""
        else:
            split_attr = attr.split("=")
            if split_attr[0] == "id":
                id_name = split_attr[1]
            elif split_attr[0] != "plugin": # Get all initial parameters (possibly only rnd)
                rnd_numbs = re.findall(r"\[(\d+)[,\d]*\]", split_attr[1])
                sets[split_attr[0]]=rnd_numbs
                # Currently no actual randomisation is implemented, TODO

    params = re.findall(r"{% *set *([a-zA-Z]\w*) *= *(\w+) *%}$",lines, re.MULTILINE) # get all following parameters
    for p_name, param in params:
        #find all cariable names and calculate them as neccessary
        subs = re.sub(r"([a-zA-Z]\w*)\[(\d+)\]", lambda mtch: sets[mtch.group(1)][int(mtch.group(2))],param)
        subs = re.sub(r"([a-zA-Z]\w*)", lambda mtch: sets[mtch.group(1)],subs)

        sets[p_name] = do_math(subs)


    if not ex_name:
        number = 1
        ex_name = "exercise1"
        while ex_name in exercise_names:
            number += 1
            ex_name = f"exercise{number}"

    exercise_names.append(ex_name)

    # insert (randomised and calculated) numbers to variables
    lines = re.sub(r"%%(\w+)\[(\d+)\]%%", lambda mtch: sets[mtch.group(1)][int(mtch.group(2))],lines)

    teach_input = re.search(r"fullprogram: \|!!(.*)!!", lines, re.DOTALL).group(1)
 #   teach_input = re.sub("// BYCODE.*$", "", teach_input, re.MULTILINE)

    os.makedirs(f"../exercises/{ex_name}", exist_ok=True)
    with open(f"../exercises/{ex_name}/teacher-input.txt", 'w') as trgt:
        trgt.write(teach_input)

    with open(f"../exercises/{ex_name}/run.sh", 'w') as trgt:
        trgt.write(MC_RUN())

    instructions = ""
    if re.search("stem: '.*'",lines, re.DOTALL):
        instructions = re.search("stem: '(.*)'",lines, re.DOTALL).group(1)

        instructions = do_pandoc(instructions, "html")
        instruct_list = instructions.split('\n')
        instructions = ""
        for inst in instruct_list:
            instructions += f"  {inst}\n"

    with open(f"../exercises/{ex_name}/config.yaml", 'w') as trgt:
        trgt.write( "---\n"
                    f"title: {ex_name}\n"
                    "max_points: 1\n"
                    "instructions: |\n"
                    f"{instructions}"
                    f"{MC_CONF()}")

    plugin_lib[ex_name]=f".. submit:: mathcheck_{ex_name} 1\n  :config: exercises/{ex_name}/config.yaml\n  \n"

    return f"PLUGIN_INSERT({ex_name})\n"


"""Create a geogebra plugin"""
def create_geogebra(lines): # UNDER CONSTRUCTION

    global exercise_names
    global plugin_lib

    ex_name = ""
    sets = dict()

    attributes = re.match(r"``` {(.+)}$", lines, re.MULTILINE).group(1).split(" ")

    for attr in attributes:
        if attr.startswith("#"): # Get the name for the exercise, or substitute with id if not unique
            ex_name = re.sub("#","",attr)
            if ex_name in exercise_names:
                ex_name = ""
        else:
            split_attr = attr.split("=")
            if split_attr[0] == "id":
                id_name = split_attr[1]
            elif split_attr[0] != "plugin": # Get all initial parameters (possibly only rnd)
                rnd_numbs = re.findall(r"\[(\d+)[,\d]*\]", split_attr[1])
                sets[split_attr[0]]=rnd_numbs
                # Currently no actual randomisation is implemented, TODO satunnaistaminen

    params = re.findall(r"{% *set *([a-zA-Z]\w*) *= *(\w+) *%}$",lines, re.MULTILINE) # get all following parameters
    for p_name, param in params:
        #find all cariable names and calculate them as neccessary
        subs = re.sub(r"([a-zA-Z]\w*)\[(\d+)\]", lambda mtch: sets[mtch.group(1)][int(mtch.group(2))],param)
        subs = re.sub(r"([a-zA-Z]\w*)", lambda mtch: sets[mtch.group(1)],subs)

        sets[p_name] = do_math(subs)


    if not ex_name:
        number = 1
        ex_name = "exercise1"
        while ex_name in exercise_names:
            number += 1
            ex_name = f"exercise{number}"

    exercise_names.append(ex_name)

    # insert (randomised and calculated) numbers to variables
    lines = re.sub(r"%%(\w+)\[(\d+)\]%%", lambda mtch: sets[mtch.group(1)][int(mtch.group(2))],lines)


    found_script = re.findall(r"javascript: \|!!\n(.*)\n!!", lines, re.DOTALL)
    test_script = ""
    par_script = "{"
    found_id = re.search('material_id: *(".+")', lines)
    if found_id:
        material_id = found_id.group(1)
        par_script += f'"material_id" : {material_id}, '

    width = re.search('width:(.*)', lines)
#    if width:
 #       par_script += f'"width":{width.group(1)}, '
    height = re.search('height:(.*)', lines)
    if not height:
#        par_script += f'"height":{height.group(1)}, '
 #   else:
        height = re.match("(.*)","200")


    for scrpt in found_script:
        if scrpt.isspace():
            pass
        funcs = re.findall(r"P\.(.+?)= *function *\(.*?\) *{(.*?)}\n", scrpt, re.DOTALL)
        for one in funcs:
            funcnam = one[0].rstrip()
            funcval = one[1].lstrip()
            if funcnam == "getData":
                test_script = funcval
                test_script.replace("return","return_values =")
            else:
                pass # Muita funktioita ei tarvittane, jos niitä on muita kuin setDataInit, joka kaiketi vain alustaa

        par_split = re.findall(r"P\.(.+)=(.+);", scrpt)
        for one in par_split:
            parnam = one[0].rstrip()
            parval = one[1].lstrip()
            par_script += f"\"{parnam}\" : {parval}, "

    par_script = par_script.rstrip(", ")
    par_script += "}" # par_scirpt config-yamlin par kohtaan tai ggscriptille

    found_commands = re.search(r"commands: \|!!\n(.*?)\n!!", lines, re.DOTALL)
    commands = ""
    if found_commands:
        commands = found_commands.group(1)
        commands = re.sub("\\n", " \\\\n ", commands)
    #        commands = f"\"{commands}\""
        # commands config-yamlin cmd kohtaan

    if not test_script:
        return (
        f'  <div id="ggbFrame_{ex_name}" style="height:{height.group(1)}">Tuo hiiri tähän ladataksesi Geagebra Appin<hr></div>\n'
        '  <script>\n'
        f'    var para = document.getElementById("ggbFrame_{ex_name}");\n'
        '    para.addEventListener("mouseover", swap );\n'
        '    function swap(){\n'
        '      para.innerHTML = "";\n'
        '      para.removeEventListener("mouseover", swap );\n'
        f'      var ggbApp = new GGBApplet({par_script}, true);\n'
        f'      ggbApp.evalCommand("{commands}");\n'
        f"      ggbApp.inject('ggbFrame_{ex_name}');\n"
        '    }\n'
        '  </script>\n'
        )

    os.makedirs(f"../exercises/{ex_name}", exist_ok=True)

    with open(f"../exercises/{ex_name}/run.sh", 'w') as trgt:
        trgt.write(GG_RUN())

    instructions = ""
    if re.search("stem: '.*'",lines, re.DOTALL):
        instructions = re.search("stem: '(.*)'",lines, re.DOTALL).group(1)

        instructions = do_pandoc(instructions, "html")
        instruct_list = instructions.split('\n')
        instructions = ""
        for inst in instruct_list:
            instructions += f"  {inst}\n"
    # Mikäli stem kohtaa ei ole, poimittaneen kaikki teksti tähän edellisen "Tehtävä"otsikon alusta...

    with open(f"../exercises/{ex_name}/config.yaml", 'w') as trgt:
        trgt.write( GG_CONF(ex_name, instructions, commands, par_script))


    with open(f"../exercises/tests.js", 'w') as trgt:
        trgt.write(GG_TEST(test_script))

    plugin_lib[ex_name]=f".. submit:: geogebra_{ex_name} 1\n  :config: exercises/{ex_name}/config.yaml\n  \n"

    return f"PLUGIN_INSERT({ex_name})\n"


#TODO acosista löytynee parempi vaihtoehto
"""Create multiplequestions questionnaire"""
def create_mcq(lines):

    global exercise_names
    global plugin_lib

    ex_name = ""
    sets = {}

    attributes = re.match(r"``` {(.+)}$", lines, re.MULTILINE).group(1).split(" ")

    for attr in attributes:
        if attr.startswith("#"):  # Get the name for the exercise, or substitute with id if not unique
            ex_name = re.sub("#", "", attr)
            if ex_name in exercise_names:
                ex_name = ""
        else:
            split_attr = attr.split("=")
            if split_attr[0] == "id":
                id_name = split_attr[1]
            elif split_attr[0] != "plugin":  # Get all initial parameters (possibly only rnd)
                rnd_numbs = re.search(r"\[(\d+),.*\]", split_attr[1]).groups()
                sets[split_attr[0]] = rnd_numbs

    params = re.findall(r"\{% *set *(.+) *= *(.*) *%\}$", lines, re.MULTILINE)  # get all following parameters
    for p_name, param in params:
        subs = re.sub(r"(\w+)\[(\d+)\]", lambda mtch: sets[mtch.group(1)][mtch.group(2)], param)
        sets[p_name] = do_math(subs)

    if not ex_name:
#        if not id_name:
        number = 1
        ex_name = "exercise1"
        while ex_name in exercise_names:
            number += 1
            ex_name = f"exercise{number}"
#        else:
#            ex_name = id_name
    exercise_names.append(ex_name)

    lines = re.sub(r"%%(\w+)\[(\d+)\]%%", lambda mtch: sets[mtch.group(1)][mtch.group(2)], lines)

    instructions = re.search("stem: (.*)$", lines, re.MULTILINE).group(1)
    instructions = do_pandoc(instructions)

    instruct_list = instructions.split('\n')
    instructions = ""
    for inst in instruct_list:
        instructions += f"    {inst}\n"

    title = re.search("headerText: (.*)$", lines, re.MULTILINE).group(1)
    title = do_pandoc(title)

    line = f".. questionnaire:: {ex_name} 1\n\n"
    if title:
        line += f"  :title: {title}\n\n"

    line += ("  .. pick-any:: 1\n\n"
            f"{instructions}\n")

    choices = re.search("choices:\n(.*)", lines, re.DOTALL).group(1).split("  -")

    alphanum = ord('a')

    for choice in choices:
        if (not choice) or choice.isspace():
            continue
        alpha = chr(alphanum)
        alphanum += 1
        text = re.search("text: (.*)", choice).group(1)
        text = do_pandoc(text)

        if not line.startswith(alpha):
            text = f"{alpha}. {text}"

        if re.search("correct: true", choice):
            text = f"*{text}"

        line += f"    {text}"
        if not text.endswith('\n'):
            line += '\n'

    line += "\n"

    alphanum = ord('a')

    for choice in choices:
        if (not choice) or choice.isspace():
            continue
        alpha = chr(alphanum)
        alphanum += 1
        if re.search("reason: '.*'", lines, re.MULTILINE):
            text = re.search("reason: '(.*)'$", lines, re.MULTILINE).group(1)
            if text and not text.isspace():
                text = do_pandoc(text)
                line += f"    {alpha} § {text}"

    line += "\n"

    plugin_lib[ex_name]=line

    return f"PLUGIN_INSERT({ex_name})\n"




def create_iframe(lines):
    filename = re.search(r"file: (.*)$",lines,re.MULTILINE).group(1)
    filename = re.sub(r"youtu.be/(.+)", r"youtube.com/embed/\1?feature=youtu.be", filename)
    filename = re.sub(r"watch\?v=", "embed/", filename)
    ret = f"<iframe src={filename}"

    attr = re.search(r"height: (.*)$",lines,re.MULTILINE).group(1)
    if attr:
        ret += f" height=\"{attr}\""

    attr = re.search(r"width: (.*)$", lines, re.MULTILINE).group(1)
    if attr:
        ret += f" width=\"{attr}\""

    ret += ">"

    attr = re.search(r"(?:videoname)|(?:footer): \"(.*)\"$", lines, re.MULTILINE).group(1)
    if attr:
        ret += f"{attr}"

    ret += "</iframe>\n"
    return ret




def create_video(lines):

    ret = f"<video "

    attr = re.search(r"height: (.*)$",lines,re.MULTILINE).group(1)
    if attr:
        ret += f" height=\"{attr}\""

    attr = re.search(r"width: (.*)$", lines, re.MULTILINE).group(1)
    if attr:
        ret += f" width=\"{attr}\""

    filename = re.search(r"file: (.*)$", lines, re.MULTILINE).group(1)
    ret += f"><source src={filename}>"

    attr = re.search(r"(?:videoname)|(?:footer): (.*)$", lines, re.MULTILINE).group(1)
    ret += f"{attr}"

    ret += "</video>\n"
    return ret



atom_skip = False
collapsing = []


"""Admonitions are written asis, pandoc will not care. Intendations though must be manually inserted after
translation"""
def create_admonition(src):
    adline = f".. admonition:: "
    line = src.readline()
    if line.lstrip().rstrip() == '\\':
        line = '\n'
    while line and line.isspace():
        line = src.readline()
        if line.lstrip().rstrip() == '\\':
            line = '\n'
    line = clean_line(line, src)
    if not line.startswith("*"):
        adline = f"{adline}-\n:::+\n"

    else:
        while line and not line.rstrip().endswith("*"):
            adline = f"{adline}{line}"
            line = clean_line(src.readline(), src)

        adline = f"{adline}{line}:::+\n"
        line = clean_line(src.readline(), src)

    pos = src.tell()
    while line and not line.startswith("#"):
        line = clean_line(line, src)
        pos = src.tell()
        adline = f"{adline}{line}"
        line = src.readline()
        if line.startswith("---"):
            adline += ":::-\n\n"
            adline += create_admonition(src)
            return adline

    src.seek(pos)

    return f"{adline}:::-\n\n"


def check_image(line):

    if re.search(r"!\[.*\]\(/images/", line):   #images must be downloaded from TIMs storage, here it's done
                                                #with curl, like it was done with the markdowns
        img = re.search(r"/images/(.*)\)", line).group(1)
        trgtimg = f"../images/{img.replace('/', '_')}"

        os.makedirs("../images", exist_ok=True)

        if update or not os.path.isfile(trgtimg):
            ### ERROR checking
            os.system(f"curl 'https://tim.jyu.fi/images/{img}' "
                      f"-o {trgtimg} {evaste}")
        line = re.sub(r"https://tim\.jyu\.fi/", "", line)
        trgtimg = f"../images/{img.replace('/', '_')}"
        line = re.sub(r"\(.*\)", f"({trgtimg})", line)

    return line

def check_plugin(line,src):

    global atom_skip

    if line.startswith(r"```"):  # Most code blocks are TIM plugins

        if atom_skip:   #see last enty in current 'if'
            line = "\n"
            atom_skip = False

        elif re.search(r"plugin=\"showVideo\"", line):  # video or old format geogebra, to html iframe
            line = src.readline()
            text = ""
            while not line.startswith(r"```"):
                text += line
                line = src.readline()
            line = create_iframe(text)

        elif re.search(r"plugin=\"m{1,2}cq", line):  # (Multi)MultipleChoiceQuestion
            block = line
            line = src.readline()
            while not line.startswith(r"```"):
                block += line
                line = src.readline()
            line = create_mcq(block)

        elif re.search(r"plugin=\"csPlugin\"", line):  # otherplugins, type specified later
            block = line
            line = src.readline()
            while not line.startswith(r"```"):
                block += line
                line = src.readline()
            if re.search("type: mathcheck", block):
                line = create_mathcheck(block)
            elif re.search("type: geogebra", block):
                line = create_geogebra(block)
            else:
                line = "\n"

        elif re.search(r"atom=\"true\"", line): # 'Atom' combines different blocks under a single block,
                                                # making it undivisible.
                                                # As A+ dosnt't handle blocks the same way, this will be ignored.
                                                # Closing code block will stop atom_skipping(/ignoring)
            line = "\n"
            atom_skip = True

    return line


"""Function for parsing the lines of TIMs markdown, and do neccessary modifications before pandocs translation"""
def clean_line(line, src):

    global collapsing

    if line.lstrip().rstrip().endswith(' \\'):  #Single backslashes at the end of line are overlooked in TIM,
                                                #but confuse pandoc
        line = line.replace(' \\', '')

    if re.search(r"\[.*?\]\(https://tim\.jyu\.fi/view", line): #link to other file in TIM,
        # we're not in TIM anymore, Toto

        #TODO sisöinen linkki osoittamaan tiedostoon
        line = re.sub(f"{view_folder}(.*?)\)", r"..\1/\1.rst", line)
#        line = re.sub(r"\)$", ")", line)

    line = check_image(line)

    line = check_plugin(line,src)

    if line.startswith("#"):    # Markdowns heading, with possible options between { }

        link = re.search(r"(#.*) {.*(#.*)[ }].*", line) # '#' is markdowns internal link, and should be conserved
        admon = re.search(r"{.*\.huomautus.*", line)    # .huomautus class will be changed to admonition directive
        collapse = re.search(r"{.*area=\"(.*)\".*collapse=\"true\".*", line) # collapse means a hideable part,
        stop_collapse = re.search(r"{.*area_end=\"(.*)\".*", line)           # and will become a toggle-header

        if link:
            line = (f"{link.group(1)} "
                        "{"
                        f"{link.group(2)}"
                        "}")
        else:
            line = re.sub(r" {.*}", "", line)

        if admon:
            line = create_admonition(src)

        if collapse:
            collapsing.append(collapse.group(1))
            if line.startswith("#-"):
                line = '\n'
            while line and line.isspace():
                line = src.readline()
                if line.lstrip().rstrip() == '\\':
                    line = '\n'

            line = re.sub(r"\*","",line)
            line = re.sub("^#+ ", "", line).rstrip()

            line = f".. toggle-header::\n:::+:header: {line} **{showhide()}**\n"

        elif stop_collapse and (stop_collapse.group(1) in collapsing):
            line = "\n:::-\n"
            collapsing.remove(stop_collapse.group(1))


    if re.search(r"^#-", line, re.MULTILINE):  # TIMs chapter break, may freely be removed
            line = re.sub("#- *", "", line, 1)

    if re.search(r"^---", line, re.MULTILINE):  # Splitting the original markdown to smaller rsts may leave
                                                # hanging transitions at the end of files, that sphinx
                                                # won't appreciate
        pos = src.tell()
        peek = src.readline()
        while peek and (peek.isspace() or peek.startswith("#-")):
            peek = src.readline()
        if not peek or re.match("#{1,2} ",peek): # 1. and 2. class headings start a new file, so if a transtition
                                                # is not followed by normal text, it should be omitted
            line = "\n"
        src.seek(pos)

    return line


"""Function to translate the modded .md files to .rst files, and instert the plugins that were stored for
protection"""
def md_to_rst(fileName):

    global plugin_lib

    start = time.time()

    newRSTName = fileName.replace("_mod.md", "_unmod.rst")
    foldName = fileName.replace("_mod.md", "").rsplit("/", 1)[0]
    rSTName = fileName.replace("_mod.md", ".rst")
    print(f"pandoc '{fileName}'")
    os.system(
        f"pandoc '{fileName}' -f markdown -t rst -o '{newRSTName}' --wrap=preserve --resource-path='{os.getcwd()}'")
    print(f"pandoc end {time.time()-start}")

    with open(f"./{newRSTName}", 'r') as src:

        os.makedirs(f"../{foldName}", exist_ok=True)

        with open(f"../{rSTName}", 'w') as trgt:

            line = " "
            tabs = 0

            while line:

                line = src.readline()

                if re.match("PLUGIN_INSERT", line):
                    ex_name = re.search(r"PLUGIN_INSERT\((.*)\)", line).group(1)
                    line = plugin_lib.pop(ex_name)

 #               line = re.sub("raw-latex", "math", line)

                if re.search(r":::\+", line):
                    line = line.replace(":::+", "")
                    tabs += 1

                if re.search(":::-", line):
                    line = line.replace(":::-", "")
                    tabs -= 1

                ttp = "  "*tabs
                trgt.write(f"{ttp}{line}")

    return



"""
The actual work begins
"""

os.chdir("CourseData")

DEP_contentui()
DEP_ggstatic()

if update and os.path.exists("Source"):
    shutil.rmtree("Source")

if not os.path.exists("Source"):
    os.mkdir("Source")


txtDirEntries = []
addtxtDirEntries = []

with open("./index.rst", 'w') as trgt:
    trgt.write( f"{course_name()}\n"
                f"{'='*len(course_name())}\n"
                "\n"
                ".. sectnum::\n\n"
                ".. toctree::\n"
                "  :maxdepth: 2\n"
                "\n"
               )

    os.chdir("Source")

    for i in range(len(content_ids())):
        con_nm, con_id = content_ids()[i]
        add_ins = add_in_ids()[i]
        trgt.write(f"  {con_nm}/index\n")
        filename = f"{con_nm}.md"
        txtDirEntries.append(filename)
        if update or not os.path.isfile(f"./{filename}"):
            if con_id == 0:
                print(f"{con_nm} file not found")
            else:
                print(f"downloading ./{filename}")
                os.system(f"curl 'https://tim.jyu.fi/download/{con_id}' "
                          f"{evaste} -o './{filename}'")
                with open(filename) as check:
                    if check.readline().startswith("<!DOCTYPE html>"):
                        raise RuntimeError("Download denied. Have you updated the eväste in courseinfo?")
        else:
            print(f"{con_nm} file exist, no need to download")

        add_in_entries = []
        if add_ins[0]:
            for add_con_nm, add_con_id in add_ins:
                if add_con_nm :
                    filename = f"{add_con_nm}.md"
                    add_in_entries.append(filename)
                    if update or not os.path.isfile(f"./{filename}"):
                        if add_con_id == 0:
                            print(f"{add_con_nm} file not found")
                        else:
                            print(f"downloading ./{filename}")
                            os.system(f"curl 'https://tim.jyu.fi/download/{add_con_id}' "
                                      f"{evaste} -o './{filename}'")
                            with open(filename) as check:
                                checkline = check.readline()
                                if checkline.startswith("<!DOCTYPE html>"):
                                    raise RuntimeError("Download denied. Have you updated the eväste in courseinfo?")
                    else:
                        print(f"{add_con_nm} file exist, no need to download")
        addtxtDirEntries.append(add_in_entries)

"""
Reading the source md files
"""

if len(txtDirEntries) == 0:
    raise ValueError("Make sure that the Source directory is not empty."
                     "It should contain at least one source file.")

print("Modifying files. Pandoc may work slowly for big files, so this might take some time")

chapterdict = dict()


for FileName, add_ins in zip(txtDirEntries, addtxtDirEntries):

    chapters = ""
    modulen = ""

    with open(f"{FileName}", 'r') as src:

        NamewoExt = FileName.replace(".md", "")
        os.makedirs(NamewoExt,exist_ok=True)

        line = src.readline()
        """
        TIM-specific settings at the beginning
        """
        if line.startswith(r"```") and re.search("settings=", line):
            line = src.readline()
            while not (line.startswith(r"```")):
                #if line.startswith("math_preamble:"):
                #    preamble = line.replace("math_preamble: ", "").rstrip()
                #    if preamble and not latex_preambles.count(preamble):
                #        latex_preambles.append(preamble)
                line = src.readline()

        else:
            src.seek(0)

        intro = ""
        while line:

            line = clean_line(src.readline(), src)

            if line.startswith("# "):
                modulen = re.sub("{.+}", "", line)
                modulen = modulen.replace("#", "").lstrip().rstrip().replace(" ", "_")
                modulen = re.sub("[/:.,]", "-", modulen)
                break

#        line = clean_line(src.readline(), src)

#        while line and not line.startswith("##"):

#            intro += line

#            line = clean_line(src.readline(), src)

        while line:

            chapter = re.sub("{.+}", "", line)
            chapter = chapter.replace("#","").lstrip().rstrip().replace(" ","_")
            chapter = re.sub("[/:.,]", "-", chapter)

            origchapter = chapter
            number = 1
            while chapter in chapterdict:
                number += 1
                chapter = origchapter + f"_{number}"
            chapterpath = f"{NamewoExt}/{chapter}"

            chapterdict[chapter] = NamewoExt

            chapters = f"{chapters}  {chapter}\n"

            with open(f"{chapterpath}_mod.md", 'w') as trgt:

                headinglevel = len(re.match("(#+) ",line).group(1))

                trgt.write(line)

                line = clean_line(src.readline(), src)

                while line and not re.match("#{1,2} ",line):

                    if re.match("#+",line):
                        newheadinglevel = len(re.match("(#+) ",line).group(1))
                        while newheadinglevel > headinglevel+1:
                            trgt.write(f"\n\n{'#'*(headinglevel+1)}" " THIS SHOULD BE HIDDEN! \n:::+:hiddenhead:}\n:::-\n")
                            headinglevel += 1
                        if newheadinglevel > headinglevel:
                            headinglevel = newheadinglevel

                    trgt.write(line)

                    line = clean_line(src.readline(), src)

            md_to_rst(f"{chapterpath}_mod.md")

    for addFileName in add_ins:

        addchapters = ""
        addmodulen = ""

        with open(f"{addFileName}", 'r') as src:


            # Edellinen versio, missä tehtävät tulivat yhdeksi kappaleeksi muiden perään,
            # pandoc ei pystynyt kääntämään isoja tehtävätiedostoja järkevässä ajassa
            # (en jäänyt odottamaan yli 15 min), joten jaan ne kuten peruskappaleetkin
            """
            
            line = src.readline()

            if line.startswith(r"```") and re.search("settings=", line):
                line = src.readline()
                while not (line.startswith(r"```")):
                    if line.startswith("math_preamble:"):
                        preamble = line.replace("math_preamble: ", "").rstrip()
                        if preamble and not latex_preambles.count(preamble):
                            latex_preambles.append(preamble)
                    line = src.readline()

            else:
                src.seek(0)

            while line and not line.startswith("#"):

                line = clean_line(src.readline(),src)

            while line:

                chapter = line.replace("#","").lstrip().replace(" ","_").rstrip()
                chapter = re.sub("[/:.,]", "-", chapter)

                origchapterpath = f"{NamewoExt}/{chapter}"
                chapterpath = origchapterpath
                number = 1
                if chapterpath in chapterdict:
                    while chapterpath in chapterdict:
                        number += 1
                        chapterpath = origchapterpath + f"_{number}"
                    chapter += f"_{number}"

                chapterdict[chapterpath] = NamewoExt

                chapters = f"{chapters}  {chapter}\n"

                with open(f"{chapterpath}_mod.md", 'w') as trgt:

                    trgt.write(line)

                    line = clean_line(src.readline(), src)

                    while line:# and not re.match("#{1,2} ",line):

                        trgt.write(line)

                        line = clean_line(src.readline(), src)

                md_to_rst(f"{chapterpath}_mod.md")
            """


            addNamewoExt = addFileName.replace(".md", "")
            os.makedirs(addNamewoExt,exist_ok=True)

            line = src.readline()
            """
            TIM-specific settings at the beginning
            """
            if line.startswith(r"```") and re.search("settings=", line):
                line = src.readline()
                while not (line.startswith(r"```")):
                    #if line.startswith("math_preamble:"):
                    #    preamble = line.replace("math_preamble: ", "").rstrip()
                    #    if preamble and not latex_preambles.count(preamble):
                    #        latex_preambles.append(preamble)
                    line = src.readline()

            else:
                src.seek(0)

            """
            Read the First heading as title, and until the next heading as intro
            """

            addintro = ""
            while line:

                line = clean_line(src.readline(),src)

                if line.startswith("# "):
                    addmodulen = re.sub("{.+}", "", line)
                    addmodulen = addmodulen.replace("#", "").lstrip().rstrip().replace(" ", "_")
                    addmodulen = re.sub("[/:.,]", "-", addmodulen)
                    break

#            line = clean_line(src.readline(), src)

#            while line and not line.startswith("##"):

#                addintro += line

#                line = clean_line(src.readline(),src)

            while line:

                chapter = re.sub("{.+}", "", line)
                chapter = chapter.replace("#", "").lstrip().rstrip().replace(" ", "_")
                chapter = re.sub("[/:.,]", "-", chapter)

                origchapter = chapter
                number = 1
                if chapter in chapterdict:
                    chapter = origchapter + "-Tehtävät"
                while chapter in chapterdict:
                    number += 1
                    chapter = origchapter + f"_{number}"
                chapterpath = f"{addNamewoExt}/{chapter}"

                chapterdict[chapter] = addNamewoExt

                addchapters = f"{addchapters}  {chapter}\n"

                with open(f"{chapterpath}_mod.md", 'w') as trgt:

                    headinglevel = len(re.match("(#+) ",line).group(1))

                    trgt.write(line)

                    line = clean_line(src.readline(), src)

                    while line and not re.match("#{1,2} ",line):

                        if re.match("#+",line):
                            newheadinglevel = len(re.match("(#+) ",line).group(1))
                            while newheadinglevel > headinglevel+1:
                                trgt.write(f"\n\n{'#'*(headinglevel+1)}" " THIS SHOULD BE HIDDEN! \n:::+:hiddenhead:}\n:::-\n")
                                headinglevel += 1
                            if newheadinglevel > headinglevel:
                                headinglevel = newheadinglevel

                        trgt.write(line)

                        line = clean_line(src.readline(), src)

                md_to_rst(f"{chapterpath}_mod.md")

        with open(f"../{addNamewoExt}/index.rst", 'w') as trgtindex:

            trgtindex.write(
                f"{addmodulen}\n"
                f"{'='*len(addmodulen)}\n"
                "\n"
                f"{addintro}\n"
                "\n"
                ".. toctree::\n"
                "\n"
                f"{addchapters}"
            )

        chapters = f"{chapters}  ../{addNamewoExt}/index\n"

    with open(f"../{NamewoExt}/index.rst", 'w') as trgtindex:

        trgtindex.write(
            f"{modulen}\n"
            f"{'='*len(modulen)}\n"
            "\n"
            f"{intro}\n"
            "\n"
            ".. toctree::\n"
            "\n"
            f"{chapters}"
        )


os.chdir("..")

UPDATE_APLUS()

print("\nCourse ready.")

# HERE JUST SO I CAN REMEMBER THE COMMANDS, CHANGE OR REMOVE AT WILL
if publish:
    usern = "laakson7"
    courseid = "geometria"
    print(f"\nrun commands: cd {os.getcwd()}/_build;scp -r * {usern}@tie-lukioplus.rd.tuni.fi:/plussa/grader/courses/{courseid}/_build")