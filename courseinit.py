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

import time


"""
Check these before funning
"""
update = False  # Download all files even if they already exists

publish = True # Wether to translate for local testing, or inputting to the intterwebs. Doesn't really do much,
                # maybe just check the end of file for manually changing few lines instead of full rerun.


# evaste (cookie) is needed to download files and images from TIM.
# In Firefox, this is acquired by enabling Tools->Web Developer->Network, then go to a TIM page you have rights to,
# right click on an element in the list and go to Copy->Copy as cURL. Then paste it to return function and make it a
# single string. Remove the first two "words", until the first '-H'
evaste = (
#        r"ex:copytexthere"
r"-H 'Host: tim.jyu.fi' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Referer: https://tim.jyu.fi/view/tau/toisen-asteen-materiaalit/matematiikka/geometria' -H 'Cookie: session=.eJyNjsEOgjAQRP-lZwyCoMDFT2m27RQbaEvKogfjv1tiYuLNw2Z3srsz7ynkguQpILAYOG0oBAV9i0kMQhRCk4e0Kfosy7vDo2TaSo5uRTjQysjNEyM5otlxucDQGEfnpom-IvwcXXfbNVnJcULIvm1lTm1vDCzBola6otpc0CpluqZvqrNSTWftMf_NOVKaqP-k2edcH5oR0YPzagfYViTpjBi6qqlfb3P4W9A.XTlsHQ.LItSXpRXrfuJBCn-WqQSG26Znko; _ga=GA1.2.1762882191.1563259360; XSRF-TOKEN=IjUxZDM1OWRkZWZhZWZlMmJjMWEyZDdlNWJiZDg0OTQxNmJiNDhmZjAi.XTlsHQ.SFoZMoxv-YEJVYNn4lQtUiSg2u8' -H 'DNT: 1' -H 'Connection: keep-alive' -H 'Upgrade-Insecure-Requests: 1'"
)

"""
Translatable parts
"""

def showhide():
    ret = "Show/Hide"
    if lang()=="fi":
        ret = "Näytä/Piilota"
    return  ret

"""
Helper functions
"""

plugin_lib = {}

"""Function for translating markdown parts inside plugins, that otherwise wouldn't go through pandoc asis"""
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
        return re.match("'(.*)'", line).group(1)

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

"""Create a mathcheck question with all neccessary files."""
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
        trgt.write(
"""#!/bin/bash

export PYTHONPATH=/submission/user

cat /exercise/teacher-input.txt ratkaisu > mc_input

sed -i 's/&gt;/>/g' mc_input
sed -i 's/&lt;/</g' mc_input

cat mc_input | mathcheck.out > mc_output

capture mathcheck.out < mc_input # in /usr/local/bin

# annetaan pisteitä sen mukaan, oliko mc tyytyväinen
# huomaa, että plussa skaalaa pisteet. jos plussassa tehtävän maksimipisteiksi on
# merkitty 50 ja tässä annetaan 1/2, opiskelija saa 25 pst. jos tässä annetaan 2/3,
# opiskelija saa 33 pst jne.

if grep -q "\!points\! 1" mc_output;
then

  echo "2/2" > /feedback/points
  echo '<br><br><div class="alert alert-success">Jipii, oikein meni! :)</div>' >> /feedback/out

elif grep -q "class=warn" mc_output;
then

  echo "1/2" > /feedback/points
  echo '<br><br><div class="alert alert-warning">Annoit turhan hankalan vastauksen! Voi vipstaakki! Voisikohan vastauksen esittää sievemmin?</div>' >> /feedback/out

else

  echo "0/2" > /feedback/points
  echo '<br><br><div class="alert alert-danger">Sait nolla pistettä. Yritä uudelleen.</div>' >> /feedback/out

fi


err-to-out
grade

"""
        )

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
"""view_type: access.types.stdasync.acceptPost 
fields: # näiden täytyy olla valideja HTML-formien attribuutteja
  - name: ratkaisu # Lomakkeen nimi verkkosivulla
    title: Ratkaisu # Näkyy syötekentän yläpuolella
    required: True

# configuration for the new Docker container grading sandbox
container:
  image: sesodesa/grade-mathcheck:2019-04-22
  mount: exercises/mathcheck-example
  cmd: /exercise/run.sh
"""
        )

    plugin_lib[ex_name]=f".. submit:: mathcheck_{ex_name} 1\n  :config: exercises/{ex_name}/config.yaml\n  \n"

    return f"PLUGIN_INSERT({ex_name})\n"





"""Create a geogebra plugin with all neccessary files."""
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
    par_script = "'{"
    found_id = re.search('material_id: *"(.+)"', lines)
    if found_id:
        material_id = found_id.group(1)
        par_script += f'"material_id" : {material_id}, '

    for scrpt in found_script:
        if scrpt.isspace():
            pass
        funcs = re.findall(r"P\.(.+?)= *function *\(.*?\) *{(.*?)}\n", scrpt, re.DOTALL)
        for one in funcs:
            funcnam = one[0].rstrip()
            funcval = one[1].lstrip()
            if funcnam == "getData":
                test_script = funcval # Tämä muokkauksen kautta test.jssään?
            else:
                pass # Muita funktioita ei tarvittane, jos niitä on muita kuin setDataInit, joka kaiketi vain alustaa

        par_split = re.findall(r"P\.(.+)=(.+);", scrpt)
        for one in par_split:
            parnam = one[0].rstrip()
            parval = one[1].lstrip()
            par_script += f"\"{parnam}\" : {parval}, "

    par_script = par_script.rstrip(", ")
    par_script += "}'" # par_scirpt config-yamlin par kohtaan tai ggscriptille

    found_commands = re.search(r"commands: \|!!\n(.*?)\n!!", lines, re.DOTALL)
    commands = ""
    if found_commands:
        commands = found_commands.group(1)
        commands = re.sub("\n", ";", commands)
        commands = f"\"{commands}\""
        # commands config-yamlin cmd kohtaan


        # Jos plugini on rakennettu komennoilla, mutta ilman tarkistusta -> ei plussan tehtävä
        # TODO komennot skriptille

    if not test_script:
        plug = (
            f'<div id="{ex_name}">Geogebra App</div>\n'
            '<script>\n'
            f'    var ggbApp = new GGBApplet({par_script}, true);\n'
            '    window.addEventListener("load", function() {\n'
            f"        ggbApp.inject('{ex_name}');\n"
            '    });\n'
            '</script>\n'
        )
        return plug

    os.makedirs(f"../exercises/{ex_name}", exist_ok=True)

    with open(f"../exercises/{ex_name}/run.sh", 'w') as trgt:
        trgt.write(
"""#!/bin/bash

# The uploaded user files are always in /submission/user
# and named identically to config.yaml regardless of the uploaded file names.

# The mount directory from config.yaml is in /exercise.
# Append the required support files to test user solution.
cp /exercise/*.js .

# "capture" etc description in https://github.com/apluslms/grading-base


# cat v | capture nodejs tests.js $1
#capture nodejs ../tests.js $1 $2 

err-to-out
grade
"""
        )

    instructions = ""
    if re.search("stem: '.*'",lines, re.DOTALL):
        instructions = re.search("stem: '(.*)'",lines, re.DOTALL).group(1)

        instructions = do_pandoc(instructions, "html")
        instruct_list = instructions.split('\n')
        instructions = ""
        for inst in instruct_list:
            instructions += f"  {inst}\n"
    # Mikäli stem kohtaa ei ole, poimittaneen kaikki teksti tähän edellisen "Tehtävä"otsikon alusta...
    # Tähän hätään jätetään kokoanna käyttämättä, jotta kokeiluyaml rakentuu varmasti oikein


    with open(f"../exercises/{ex_name}/config.yaml", 'w') as trgt:
        trgt.write( "---\n"
                    f"title: {ex_name}\n"
                    "max_points: 1\n"
                    "instructions: |\n"
                    "  <p> OHJEET TBA\n"
                    '    <iframe src="/grader/static/santtufork/_static/child.html"\n'
                    f'    id="ggbFrame_{ex_name}"'
"""
        onload="postMsg();" width="1000" height="600" frameborder="0"></iframe>
    
    <script type="text/javascript">
      function postMsg() {
"""
f'        var ggbFrame = document.getElementById("ggbFrame_{ex_name}");\n'
f'        var cmd = {commands};\n'
f'        var par = {par_script};\n'
"""        ggbFrame.contentWindow.postMessage(cmd+"\\n"+par, '*');
      };
      var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
      var eventer = window[eventMethod];
      var messageEvent = eventMethod === "attachEvent" ? "onmessage" : "message";
      eventer(messageEvent, function (e) {
        var data = (typeof e.data) === "string" ? e.data : "";
"""
f'        document.getElementById("{ex_name}_id").style.display = "none";\n'
f'        document.getElementById("{ex_name}_id").value = data;\n'
"""      });
    </script>
  </p>
# acceptPost tuottaa tekstikentän sivulle
# tiedoston palautuslomakkeen sijaan
view_type: access.types.stdasync.acceptPost 
fields: # näiden täytyy olla valideja HTML-formien attribuutteja
"""
f'  - name: {ex_name} # Lomakkeen nimi verkkosivulla, täytyy olla yksikäsitteinen ja sopia yhteen v_id:n kanssa (ks.yllä, kahdessa kohtaa ja alla run.sh:n jälkeen)\n'
"""    required: True

container:
  image: apluslms/grade-nodejs:11-2.7
  mount: exercises/geogebra-example
"""
f'  cmd: /exercise/run.sh {ex_name}'
        )



# tests.js kirjoitus näin alkuun, että edes jotain tapahtuu TODO tarkistuskoodi test_sciptistä
    if not os.path.exists("../exercises/tests.js"):
        with open(f"../exercises/tests.js", 'w') as trgt:
            trgt.write(
""""use strict";

Object.size = function (obj) {
    var size = 0;
    for (var key in obj) if (obj.hasOwnProperty(key)) size++;
    return size;
};

function replaceAll(str, find, replace) {
    if (str === undefined) return str;
    if (str === "") return str;
    return str.replace(new RegExp(find, 'g'), replace);
}

// the test function
// checks studentInput (got from Geogebra) against teacherInput (got from run.sh).
// teacherInput in JSON format, surrounded by single quotes - to keep it as one string
// studentInput as similar commands as inserted to GeoGebra, separator is ";"
// Each teacherInput grants one point if it matches - matching means str equivalence
function testTeacherVsStudent(teacherInput, studentInput) {
    var msg="";
    Object.keys(studentInput).forEach(function (key) {
        var value = studentInput[key];
        msg = msg + key + "=" + value + ";";
    });
    msg = msg + "<br>";

    var points = 0;
    Object.keys(teacherInput).forEach(function (key) {
        var value = teacherInput[key];

        if (Array.isArray(value) ) {
            // if two numbers given, the value must locate in the range
            var studentValue = studentInput[key];
            if (studentValue) {
                try {
                    studentValue = parseFloat(studentValue);
                    if (parseFloat(value[0]) < studentValue < parseFloat(value[1])) {
                        points++;
                        msg += (studentValue + " OK<br>");
                    }
                }
                catch (exp) { console.log(exp); }
            }
        }
        else {
            try {
                var studentValue = studentInput[key];
		if (studentValue) studentValue=studentValue.toString().trim().replace(" ","");
                value = value.toString().trim();
                if (value === studentValue) {
                    points++;
                    msg = msg + key + " &#128077;<br>";   //thumbs-up
                }
                else {
                    msg = msg + key + " &#128078;<br>";  //thumbs-down
                }
            }
            catch (exp) { console.log(exp); }
        }
    });
    return {
        points:points, 
        msg:msg
    };
}


function getMap(str) {
    var studentInput={}
    if (str.length === 0) return {};
    var commands = str.split(";");
    for (var i = 0; i < commands.length; i++) {
        var command = commands[i];
        var parts = command.split(":");
        if (parts.length < 2) parts = command.split("=");
        var key = parts[0].trim();
        var value = "";
        if (parts.length > 1) {
            value = parts[1].trim();
        }
        if (key === "") continue;
        studentInput[key] = value;
    }
    return studentInput;
}


const testFunctions = [
    testTeacherVsStudent
];

function testMain(teacherInput, studentInput) {
    var points = 0;
    var max_points = 0;
    var msg = "";

    for (var test of testFunctions) {
        msg = msg + "Testing " + test.toString().split("\n")[0] + " ... <br>";
        max_points += Object.size(teacherInput);
        try {
            var res = test(teacherInput, studentInput);
            points = points + res.points;
            msg = msg + res.msg;
        } catch (exp) { console.log(exp); }
    }

    return {
        points: points,
        max_points: max_points,
        msg: msg
    };
}

if (require.main === module) {

    var teacherInput = {};
    try {
        // single quotes removed 
        var input = replaceAll(process.argv[3], "'", "");
        teacherInput = JSON.parse(input);
    } catch (exp) {console.log(exp);}

    // first parameter must be a file name, defaults to "v".
    // Yet multiple variables in the same page with the same name "v" 
    // mandates to name variables differently.
    // "v" is like "vastaus": a student input
    var fileName = "v"; //student input, defaults to "v"    
    try {
        fileName = process.argv[2];
    } catch (exp) { console.log(exp); }

    // read "v" or fileName
    var fs = require('fs');
    fs.readFile(fileName, 'utf8', function (err, contents) {
        var studentInput = getMap(contents);
        var result = testMain(teacherInput, studentInput);
        console.log(result.points+"/"+result.max_points+"<br>");
        console.log(result.msg+"<br>");
        console.error("TotalPoints: ", result.points);	    
        console.error("MaxPoints: ", result.max_points);
        console.error("filename: "+fileName);
        //console.error(teacherInput);
    if (result.points/result.max_points>0.5) console.error("Hienoa!");
    else if (result.points/result.max_points==0.5) console.error("Lähellä!");
    else console.error("Yritä vielä!");
        
    });
    return true;

}"""
            )

    plugin_lib[ex_name]=f".. submit:: geogebra_{ex_name} 1\n  :config: exercises/{ex_name}/config.yaml\n  \n"

    return f"PLUGIN_INSERT({ex_name})\n"


"""Create multiplequestions questionnaire, and save it to be inserted later"""
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

    if re.search(r"\[.*\]\(https://tim.jyu.fi/view", line): #internal link #TODO

        line = re.sub(f"{view_folder}", "..", line)
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


"""
Install contentui packages
"""
if not os.path.exists("./extensions/sphinxcontrib"):
    os.system(f"pip3 install -t {os.getcwd()}/extensions sphinxcontrib-contentui")

if not os.path.exists("extensions/sphinxcontrib/contentui_orig.css"):
    shutil.copyfile("extensions/sphinxcontrib/contentui.css", "extensions/sphinxcontrib/contentui_orig.css")

print("Updating contentui.css")

shutil.copyfile("extensions/sphinxcontrib/contentui_orig.css", "extensions/sphinxcontrib/contentui.css")

with open("extensions/sphinxcontrib/contentui_orig.css", 'r') as src:

    with open("extensions/sphinxcontrib/contentui.css", 'w') as trgt:

        line = src.readline()

        while line:
            lineblock = ""

            while not line.startswith("."):
                trgt.write(line)
                line = src.readline()

            while not line.startswith("}"):
                lineblock += line

                if line.endswith("}\n"):
                    break

                line = src.readline()

            if lineblock.startswith(".toggle-header {"):
                lineblock =""".toggle-header {
    display: inline-block;
    clear: both;
    cursor: pointer;
    font-size: 1.17em;
    margin-top: 1em;
    margin-bottom: 1em;
    margin-left: 0;
    margin-right: 0;
    font-weight: bold;
}
"""


            elif lineblock.startswith(".toggle-header:after {"):
                lineblock =""".toggle-header:after {
    display: inline;
    content: " ▼";
}
"""

            elif lineblock.startswith(".toggle-header.open:after {"):
               lineblock = """.toggle-header.open:after {
    display: inline;
    content: " ▲";
}
"""
            if not lineblock.endswith("}\n"):
                lineblock += "}\n"
            trgt.write(lineblock)
            line = src.readline()

"""
Create main index, and while at it download course .mds if neccessary
"""

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

latex_preambles = []

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
                if line.startswith("math_preamble:"):
                    preamble = line.replace("math_preamble: ", "").rstrip()
                    if preamble and not latex_preambles.count(preamble):
                        latex_preambles.append(preamble)
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

        line = clean_line(src.readline(), src)

        while line and not line.startswith("##"):

            intro += line

            line = clean_line(src.readline(), src)

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
                    if line.startswith("math_preamble:"):
                        preamble = line.replace("math_preamble: ", "").rstrip()
                        if preamble and not latex_preambles.count(preamble):
                            latex_preambles.append(preamble)
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

            line = clean_line(src.readline(), src)

            while line and not line.startswith("##"):

                addintro += line

                line = clean_line(src.readline(),src)

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

print("Updating conf.py")
if not os.path.exists("conf_orig.py"):
    shutil.copyfile("conf.py", "conf_orig.py")
    shutil.copymode("conf.py", "conf_orig.py")

with open("conf_orig.py", 'r') as src:

    with open("conf.py", 'w') as trgt:

        line = src.readline()

        latex_preamble = ""

        if latex_preambles:
            latex_preamble = "\t'preamble':"
            for s in latex_preambles:
                latex_preamble += f"\n\t\t{s}"

        while line:

            line = re.sub(r"(extensions = \[)", f"\\1\n\t'sphinxcontrib.contentui',", line)

            line = re.sub(r"(exclude_patterns =.*?)(?:, 'Source')?\]", f"\\1, 'Source']",line)

            line = re.sub(r"(course_open_date =).*", f"\\1 '{course_open()}'",line)
            line = re.sub(r"(course_close_date =).*", f"\\1 '{course_close()}'",line)
            line = re.sub(r"(project =).*", f"\\1 '{project()}'",line)
            line = re.sub(r"(copyright =).*", f"\\1 '{copyright()}'",line)
            line = re.sub(r"(author =).*", f"\\1 '{author()}'",line)
            line = re.sub(r"(course_close_date =).*", f"\\1 '{course_close()}'", line)
            line = re.sub(r"(language =).*", f"\\1 '{lang()}'",line)
            if line.startswith("latex_elements") and latex_preamble:
                while line and not re.match(r"\}", line):
                    line = src.readline()
                line = ("latex_elements = {\n"
                        f"{latex_preamble},"
                        "}\n")

            trgt.write(line)
            line = src.readline()

if not os.path.exists("_static/course_orig.css"):
    shutil.copyfile("_static/course.css", "_static/course_orig.css")

print("Updating _static/course.css")

shutil.copyfile("_static/course_orig.css", "_static/course.css")

with open("_static/course.css", 'a') as coursecss:

    coursecss.write("\n.hiddenhead\n{\n\tdisplay:none\n}\n")


if not os.path.exists("_templates/layout_orig.html"):
    shutil.copyfile("_templates/layout.html", "_templates/layout_orig.html")

print("Updating _templates/layout.html")

shutil.copyfile("_templates/layout_orig.html", "_templates/layout.html")

with open("_templates/layout_orig.html", 'r') as src:

    with open("_templates/layout.html", 'w') as trgt:

        line = src.readline()

        while line:

            if line.startswith("{% endblock %}"):

                trgt.write( "<link data-aplus rel=\"stylesheet\"\n"
                            "href=\"{{ pathto('_static/contentui.css', 1) }}\"\n"
                            "type=\"text/css\"\n"
                            "/>\"\n\n")

            elif line.startswith("<!-- Custom course styles -->"):

                trgt.write( '<script data-aplus src="https://cdn.geogebra.org/apps/deployggb.js"></script>\n\n'
                            "<script data-aplus type=\"text/javascript\"\n"
                            "src=\"{{ pathto('_static/contentui.js', 1) }}\">\n"
                            "</script>\n\n")

            trgt.write(line)
            line = src.readline()


if publish:
    if not os.path.exists("docker-compile_orig.sh"):
        shutil.copyfile("docker-compile.sh", "docker-compile_orig.sh")
        shutil.copymode("docker-compile.sh", "docker-compile_orig.sh")

    print("Updating docker-compile.sh")

    shutil.copyfile("docker-compile_orig.sh", "docker-compile.sh")
    shutil.copymode("docker-compile_orig.sh", "docker-compile.sh")


    with open("docker-compile_orig.sh", 'r') as src:

        with open("docker-compile.sh", 'w') as trgt:

            line = src.readline()

            while line:

                line = re.sub(r"(STATIC_CONTENT_HOST=).*\"","\\1..\"",line)

                trgt.write(line)
                line = src.readline()

print("\nCourse ready.")

# HERE JUST SO I CAN REMEMBER THE COMMANDS, CHANGE OR REMOVE AT WILL
if publish:
    usern = "laakson7"
    courseid = "geometria"
    print(f"\nrun commands: cd {os.getcwd()}/_build;scp -r * {usern}@tie-lukioplus.rd.tuni.fi:/plussa/grader/courses/{courseid}/_build")