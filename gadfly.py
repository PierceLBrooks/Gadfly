
# Author: Pierce Brooks

import os
import sys
import json
import hashlib
import logging
import requests
import mimetypes
import traceback
import subprocess
import esprima_ast_visitor_py.visitor as visit
from GoogleAds.main import GoogleAds
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def hashify(string):
    sha = hashlib.md5()
    sha.update(string.encode("UTF-8"))
    return sha.hexdigest()

mimetypes.init()
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
    creative_ids = ads.creative_search_by_advertiser_id(advertisor_id, 200)
urls = []
mimes = []
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
            elif (parse.netloc.endswith("googlevideo.com")):
                mimes.append([ad[key], creative_id])
        except:
            logging.error(traceback.format_exc())
for mime in mimes:
    creative_id = mime[1]
    try:
        mime = requests.get(mime[0])
        if ("200" in str(mime.status_code)):
            headers = mime.headers
            mime = mime.content
            descriptor = open(os.path.join(os.getcwd(), creative_id+mimetypes.guess_extension(headers["Content-Type"])), "wb")
            descriptor.write(mime)
            descriptor.close()
    except:
        logging.error(traceback.format_exc())
contents = {}
contents["creatives"] = creatives
contents["creative_ids"] = creative_ids
descriptor = open(os.path.join(os.getcwd(), advertisor_id+".json"), "w")
descriptor.write(json.dumps(contents))
descriptor.close()
contents = []
if (sys.flags.debug):
    print(str(len(creative_ids)))
    print(str(len(creatives)))
mapping = {}
for url in urls:
    if (sys.flags.debug):
        print(url)
    try:
        content = requests.get(url).text
        mapping[hashify(content)] = url
        if (sys.flags.debug):
            print(hashify(content)+" -> "+url)
        contents.append(content)
    except:
        logging.error(traceback.format_exc())
if (len(contents) < len(urls)):
    print("[GADFLY] Could not get all content URLs: %s / %s"%(str(len(contents)), str(len(urls))))
esprima_ast_strings = []
values = []
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
        print("[GADFLY] Parse failure @: \""+str(mapping[hashify(content)])+"\"")
        values.append(value)
if (len(esprima_ast_strings) < len(contents)):
    print("[GADFLY] Could not parse all content URLs: %s / %s" % (str(len(esprima_ast_strings)), str(len(urls))))
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
videos = []
for i in range(len(values)):
    video = values[i]
    if not (video == "video_videoId"):
        continue
    if (i+1 >= len(values)):
        break
    video = "https://youtube.com/watch?v=%s"%tuple([values[i+1]])
    if (video in videos):
        continue
    videos.append(video)
for video in videos:
    if (sys.flags.debug):
        print(video)
    command = []
    command.append(sys.executable)
    command.append("-m")
    command.append("yt_dlp")
    command.append("-i")
    command.append("-v")
    command.append(video)
    try:
        output = subprocess.check_output(command)
    except:
        logging.error(traceback.format_exc())

