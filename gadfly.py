
# Author: Pierce Brooks

import os
import sys
import json
import logging
import traceback
import subprocess
import urllib.requests as requester
import esprima_ast_visitor_py.visitor as visit
from GoogleAds.main import GoogleAds
from bs4 import BeautifulSoup
from urllib.parse import urlparse

ads = GoogleAds()
advertisor_id = sys.argv[1]
creative_ids = None
creatives = {}
if (os.path.exists(os.path.join(os.getcwd(), advertisor_id+".json"))):
    descriptor = open(os.path.join(os.getcwd(), advertisor_id+".json"), "r")
    creative_ids = json.loads(descriptor.read())
    creatives = creative_ids["creatives"]
    creative_ids = creative_ids["creative_ids"]
    descriptor.close()
else:
    creative_ids = ads.creative_search_by_advertiser_id(advertisor_id, 40)
urls = []
for creative_id in creative_ids:
    ad = None
    if (creative_id in creatives):
        ad = creatives[creative_id]
    else:
        try:
            ad = ads.get_detailed_ad(advertisor_id, creative_id)
        except:
            logging.error(traceback.format_exc())
            ad = None
    if (ad == None):
        break
    creatives[creative_id] = ad
    for key in ad:
        if (ad[key] in urls):
            continue
        try:
            parse = urlparse(ad[key])
            if (parse.path.endswith(".js")):
                urls.append(ad[key])
        except:
            logging.error(traceback.format_exc())
contents = {}
contents["creatives"] = creatives
contents["creative_ids"] = creative_ids
descriptor = open(os.path.join(os.getcwd(), advertisor_id+".json"), "w")
descriptor.write(json.dumps(contents))
descriptor.close()
contents = []
for url in urls:
    if (sys.flags.debug):
        print(url)
    try:
        content = requester.urlopen(url).read()
        contents.append(content)
    except:
        logging.error(traceback.format_exc())
esprima_ast_strings = []
for content in contents:
    target = os.path.join(os.getcwd(), sys.argv[0]+".js")
    descriptor = open(target, "w")
    descriptor.write(content)
    descriptor.close()
    command = []
    command.append("node")
    command.append(os.path.join(os.getcwd(), "gadfly.js"))
    command.append(target)
    lines = []
    exit = 0
    try:
        process = subprocess.Popen(command, env=dict(os.environ.copy()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            line = process.stdout.readline()
            if ((len(line) == 0) and not (process.poll() == None)):
                break
            try:
                line = line.decode("UTF-8").strip()
            except:
                continue
            lines.append(line)
        status = process.communicate()[0]
        exit += process.returncode
    except:
        logging.error(traceback.format_exc())
        continue
    if (exit == 0):
        esprima_ast_strings.append(json.loads("\n".join(lines)))
    else:
        values.append(value)
while (len(esprima_ast_strings) > 0):
    esprima_ast_string = esprima_ast_strings[0]
    if (len(esprima_ast_strings) > 1):
        esprima_ast_strings = esprima_ast_strings[1:]
    else:
        esprima_ast_strings = []
    try:
        program = visit.objectify(esprima_ast_string) # visit.Node object
        if ("str" in str(type(program))):
            values.append(str(program))
        else:
            for node in program.traverse():
                if (node.type == "Literal"):
                    if (len(str(node.value)) < 25):
                        values.append(str(node.value))
                    else:
                        nodes = []
                        value = str(node.value)
                        if ((value.startswith("<!DOCTYPE html>")) or (value.startswith("<html>"))):
                            try:
                                soup = BeautifulSoup(value)
                                scripts = soup.find_all("script")
                                for script in scripts:
                                    nodes.append(str(script.string))
                            except:
                                nodes = []
                                nodes.append(value)
                        else:
                            nodes.append(value)
                        for value in nodes:
                            #print(value)
                            target = os.path.join(os.getcwd(), sys.argv[0]+".js")
                            descriptor = open(target, "w")
                            descriptor.write(value)
                            descriptor.close()
                            command = []
                            command.append("node")
                            command.append(os.path.join(os.getcwd(), "es.js"))
                            command.append(target)
                            lines = []
                            exit = 0
                            try:
                                process = subprocess.Popen(command, env=dict(os.environ.copy()), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                while True:
                                    line = process.stdout.readline()
                                    if ((len(line) == 0) and not (process.poll() == None)):
                                        break
                                    try:
                                        line = line.decode("UTF-8").strip()
                                    except:
                                        continue
                                    lines.append(line)
                                status = process.communicate()[0]
                                exit += process.returncode
                            except:
                                continue
                            if (exit == 0):
                                esprima_ast_strings.append(json.loads("\n".join(lines)))
                            else:
                                values.append(value)
    except:
        logging.error(traceback.format_exc())
descriptor = open(os.path.join(os.getcwd(), sys.argv[0]+".json"), "w")
descriptor.write(json.dumps(values))
descriptor.close()

