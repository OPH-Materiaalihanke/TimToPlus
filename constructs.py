"""
Translatable parts
"""
import shutil
import os
import re

from courseinfo import *

def showhide():
    ret = "Show/Hide"
    if lang()=="fi":
        ret = "Näytä/Piilota"
    return ret

def MC_RUN():
    return ("""#!/bin/bash

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

def MC_CONF():
    return ("""view_type: access.types.stdasync.acceptPost 
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

def GG_RUN():
    return ("""#!/bin/bash

# The uploaded user files are always in /submission/user
# and named identically to config.yaml regardless of the uploaded file names.

# The mount directory from config.yaml is in /exercise.
# Append the required support files to test user solution.
cp /exercise/*.js .

# "capture" etc description in https://github.com/apluslms/grading-base


# cat v | capture nodejs tests.js $1
capture nodejs ../tests.js $1

err-to-out
grade
"""
            )

def GG_CONF(ex_name, instructions, commands, params):
    return ("""---
"""f"title: {ex_name}""""
max_points: 2
instructions: |
"""f"  <p> {instructions} </p>""""
  <p>
  <iframe """f'id="{ex_name}_frame"'""" src="_static/ggframe.html" onload="postMsg();" width="1000" height="600" frameborder="0"></iframe>
  <script type="text/javascript">
    function postMsg() {
"""f'      document.getElementById("{ex_name}_id").style.display = "none";'"""
    };
    """f'{ex_name}_frame.contentWindow.postMessage({commands}+"´´´"+{params},'""" '*');
  </script>
  </p>
view_type: access.types.stdasync.acceptPost 
fields: # näiden täytyy olla valideja HTML-formien attribuutteja
"""f'  - name: {ex_name}'"""
    required: True

container:
  image: apluslms/grade-nodejs:11-2.7
  mount: exercises/geogebra-example
"""f'  cmd: /exercise/run.sh {ex_name}_frame.ggb-element'
            )

def GG_TEST(test_script):
    return (
""""use strict";

Object.size = function (obj) {
    var size = 0;
    for (var key in obj) if (obj.hasOwnProperty(key)) size++;
    return size;
};

function testMain(filename) {
    
"""f"{test_script}""""
    return {
        points: return_values.points,
        max_points: 2,  //ONKO NÄIN?
        msg: return_values.message
    };
}

if (require.main === module) {

    var filename;
    try {
        filename = process.argv[2];
    } catch (exp) { console.log(exp); return false; }

    var result = testMain(filename);
    console.log(result.points+"/"+result.max_points+"<br>");
    console.log(result.msg+"<br>");
    console.error("TotalPoints: ", result.points);	    
    console.error("MaxPoints: ", result.max_points);
    console.error("filename: "+fileName);
    //console.error(teacherInput);
    console.error(result.message);
        
    return true;

}""")

def DEP_ggstatic():

    with open("_static/ggframe.html", 'w') as trgt:
        trgt.write("""<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <meta name=viewport content="width=device-width,initial-scale=1">
        <title> GeoGebra </title>
    <script src = "https://cdn.geogebra.org/apps/deployggb.js"></script>
    <script>

    function parseData(data) {
      var parts = data.split("´´´");
      var cmd = parts[0];
      var par="";
      if (parts.length>1)
        par = parts[1];
      console.log(cmd, par);
      return [cmd, par];
    }

    window.onmessage = function(e)
    {
      // cmd and par as global variables
      console.log("onmessage: ", e.data);
      
      var ggbData = parseData(e.data);

      console.log(ggbData);
      cmd = ggbData[0];
      par = ggbData[1];
      
      var params = {};


      par["language"] = "fi";
      par["width"] = window.innerWidth;
      par["height"] = window.innerHeight;
      par["appletOnLoad"] = initCommands;

      initApplet(par);
    };

    function initCommands()
    {
      ggbApplet.evalCommand(cmd);
    }

    function initApplet(params)
    {
      var ggbApplet = new GGBApplet(params, true);
      ggbApplet.inject('ggb-element');
    }

    </script>
  </head>
  <body>
    <div id="ggb-element"></div>
  </body>
</html>""")


def DEP_contentui():
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
                    lineblock = (
""".toggle-header {
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
                    )


                elif lineblock.startswith(".toggle-header:after {"):
                    lineblock = (
""".toggle-header:after {
    display: inline;
    content: " ▼";
}
"""
                    )

                elif lineblock.startswith(".toggle-header.open:after {"):
                   lineblock = (
""".toggle-header.open:after {
    display: inline;
    content: " ▲";
}
"""
                   )

                if not lineblock.endswith("}\n"):
                    lineblock += "}\n"
                trgt.write(lineblock)
                line = src.readline()

def UPDATE_APLUS():

    print("Updating conf.py")
    if not os.path.exists("conf_orig.py"):
        shutil.copyfile("conf.py", "conf_orig.py")
        shutil.copymode("conf.py", "conf_orig.py")

    with open("conf_orig.py", 'r') as src:

        with open("conf.py", 'w') as trgt:

            line = src.readline()

            while line:

                line = re.sub(r"(extensions = \[)", f"\\1\n\t'sphinxcontrib.contentui',", line)

                line = re.sub(r"(exclude_patterns =.*?)(?:, 'Source')?\]", f"\\1, 'Source']", line)

                line = re.sub(r"(course_open_date =).*", f"\\1 '{course_open()}'", line)
                line = re.sub(r"(course_close_date =).*", f"\\1 '{course_close()}'", line)
                line = re.sub(r"(project =).*", f"\\1 '{project()}'", line)
                line = re.sub(r"(copyright =).*", f"\\1 '{copyright()}'", line)
                line = re.sub(r"(author =).*", f"\\1 '{author()}'", line)
                line = re.sub(r"(course_close_date =).*", f"\\1 '{course_close()}'", line)
                line = re.sub(r"(language =).*", f"\\1 '{lang()}'", line)

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

                    trgt.write("<link data-aplus rel=\"stylesheet\"\n"
                               "href=\"{{ pathto('_static/contentui.css', 1) }}\"\n"
                               "type=\"text/css\"\n"
                               "/>\"\n\n")

                elif line.startswith("<!-- Custom course styles -->"):

                    trgt.write('<script data-aplus src="https://cdn.geogebra.org/apps/deployggb.js"></script>\n\n'
                               '<script data-aplus type="text/javascript"\n'
                               "src=\"{{ pathto('_static/contentui.js', 1) }}\">\n"
                               "</script>\n\n")

                trgt.write(line)
                line = src.readline()

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
                line = re.sub(r"(STATIC_CONTENT_HOST=).*\"", "\\1..\"", line)

                trgt.write(line)
                line = src.readline()