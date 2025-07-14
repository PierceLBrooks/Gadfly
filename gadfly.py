
# Author: Pierce Brooks

import os
import sys
import json
import time
import shutil
import hashlib
import logging
import requests
import mimetypes
import traceback
import subprocess
import xml.etree.ElementTree as xml_tree
import esprima_ast_visitor_py.visitor as visit
from GoogleAds.main import GoogleAds
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def is_valid_url(subject):
    try:
        result = urlparse(subject)
        return all([result.scheme, result.netloc])
    except:
        return False

def handle(node, parent):
    handles = []
    if (node == None):
        return handles
    for child in node:
        children = handle(child, node)
        for i in range(len(children)):
            if not (children[i] in handles):
                handles.append(children[i])
    if ((is_valid_url(node.text)) and not (node.text in handles)):
        handles.append(node.text)
    if ((is_valid_url(node.tail)) and not (node.tail in handles)):
        handles.append(node.tail)
    if ((sys.flags.debug) and (parent == None)):
        for handled in handles:
            print(str(handled))
    return handles

def hashify(string):
    sha = hashlib.sha256()
    sha.update(string.encode("UTF-8"))
    return str(sha.hexdigest())

logging.basicConfig(filename=os.path.join(os.getcwd(), sys.argv[0]+".log"), filemode="w", level=logging.DEBUG, format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")
mimetypes.init()
try:
    mimetypes.add_type("application/dash+xml", ".mpd", strict=True)
    mimetypes.add_type("application/dash-patch+xml", ".mpp", strict=True)
except:
    pass
records = []
record = []
limit = 100
proxy = None
ads = GoogleAds()
if (sys.flags.debug):
    print(str(sys.argv))
advertisor_id = " ".join(sys.argv[1:])
advertisor_ids = []
if ((len(advertisor_id) == 22) and (advertisor_id[:2] == "AR")):
    advertisor_ids.append(advertisor_id)
else:
    suggestions = ads.get_all_search_suggestions(advertisor_id)
    for suggestion in suggestions:
        try:
            suggestion = suggestion["1"]["2"]
            if ((len(suggestion) == 22) and (suggestion[:2] == "AR")):
                advertisor_ids.append(suggestion)
        except:
            pass
suggestion = " ".join(sys.argv[1:])
if (sys.flags.debug):
    print(advertisor_ids)
if (len(advertisor_ids) == 0):
    sys.exit(-1)
advertisor_ids = list(sorted(advertisor_ids))
for advertisor_id in advertisor_ids:
    time.sleep(1)
    if not (proxy == None):
        ads.refresh_session(proxy=proxy)
    if (sys.flags.debug):
        print(advertisor_id)
    creative_ids = None
    creatives = {}
    if (os.path.exists(os.path.join(os.getcwd(), advertisor_id+".json"))):
        descriptor = open(os.path.join(os.getcwd(), advertisor_id+".json"), "r")
        creative_ids = json.loads(descriptor.read())
        creatives = creative_ids["creatives"]
        creative_ids = creative_ids["creative_ids"]
        descriptor.close()
    else:
        try:
            creative_ids = ads.creative_search_by_advertiser_id(advertisor_id, 200)
        except:
            logging.error(traceback.format_exc())
            creative_ids = None
    if (creative_ids == None):
        continue
    creative_ids = list(sorted(creative_ids))
    urls = []
    mimes = []
    errors = 0
    for creative_id in creative_ids:
        time.sleep(1)
        if (sys.flags.debug):
            print(creative_id)
        ad = None
        if (creative_id in creatives):
            ad = creatives[creative_id]
        else:
            try:
                ad = ads.get_detailed_ad(advertisor_id, creative_id)
            except:
                if (sys.flags.debug):
                    print("Error!")
                logging.error(traceback.format_exc())
                ad = None
                errors += 1
        if (ad == None):
            break
        key = "Advertisor Keyword"
        if not (key in ad):
            if not (suggestion == advertisor_id):
                ad[key] = suggestion
        creatives[creative_id] = ad
        for key in ad:
            if (ad[key] in urls):
                continue
            try:
                parse = urlparse(ad[key])
                if (parse.path.endswith(".js")):
                    urls.append([ad[key], creative_id])
                elif (parse.netloc.endswith("googlevideo.com")):
                    mimes.append([ad[key], creative_id])
            except:
                logging.error(traceback.format_exc())
    if (sys.flags.debug):
        print("Errors: "+str(errors)+" / "+str(len(creative_ids)))
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
        creative_id = url[1]
        if (sys.flags.debug):
            print(str(url))
        url = url[0]
        try:
            record.append([url])
            response = requests.get(url)
            record[len(record)-1].append(str(response.status_code))
            content = response.text
            mapping[hashify(content)] = url
            if (sys.flags.debug):
                print(hashify(content)+" -> "+url)
            contents.append([content, creative_id])
        except:
            logging.error(traceback.format_exc())
    if (len(contents) < len(urls)):
        print("[GADFLY] Could not get all content URLs: %s / %s"%(str(len(contents)), str(len(urls))))
    esprima_ast_strings = []
    values = []
    for content in contents:
        creative_id = content[1]
        content = content[0]
        if (len(content) < limit):
            if (sys.flags.debug):
                if (hashify(content) in mapping):
                    print(mapping[hashify(content)])
        if (content.startswith("<?xml ")):
            if (sys.flags.debug):
                print(creative_id)
                print(content)
            if ("xmlns=\"urn:mpeg:dash:schema:mpd:" in content.lower()):
                index = 0
                while (True):
                    target = os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+str(index)+".mpd")
                    if (os.path.exists(target)):
                        index += 1
                        continue
                    if (hashify(content) in mapping):
                        content += "\n<!--"+mapping[hashify(content)]+"-->"
                    descriptor = open(target, "w")
                    descriptor.write(content)
                    descriptor.close()
                    break
                continue
            try:
                target = ""
                while (True):
                    target = os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+str(index)+".xml")
                    if (os.path.exists(target)):
                        index += 1
                        continue
                    if (hashify(content) in mapping):
                        content += "\n<!--"+mapping[hashify(content)]+"-->"
                    descriptor = open(target, "w")
                    descriptor.write(content)
                    descriptor.close()
                    break
                if not (len(target) == 0):
                    tree = xml_tree.parse(target)
                    base = tree.getroot()
                    handles = handle(base, None)
                    for handled in handles:
                        mimes.append([handled, creative_id])
            except:
                logging.error(traceback.format_exc())
            continue
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
            esprima_ast_strings.append([json.loads("\n".join(lines)), creative_id])
        else:
            print("[GADFLY] Parse failure @: \""+str(mapping[hashify(content)])+"\"")
            values.append(content)
    if (len(esprima_ast_strings) < len(contents)):
        print("[GADFLY] Could not parse all content URLs: %s / %s" % (str(len(esprima_ast_strings)), str(len(urls))))
    while ((len(esprima_ast_strings) > 0) or (len(mimes) > 0)):
        if (len(esprima_ast_strings) > 0):
            esprima_ast_string = esprima_ast_strings[0]
            creative_id = esprima_ast_string[1]
            esprima_ast_string = esprima_ast_string[0]
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
                            if (len(str(node.value)) < limit):
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
                                        logging.error(traceback.format_exc())
                                else:
                                    nodes.append(value)
                                for value in nodes:
                                    #print(value)
                                    if (len(value) < limit):
                                        if (sys.flags.debug):
                                            print(value)
                                        continue
                                    if (value.startswith("<?xml ")):
                                        if (sys.flags.debug):
                                            print(creative_id)
                                            print(value)
                                        if ("xmlns=\"urn:mpeg:dash:schema:mpd:" in value.lower()):
                                            index = 0
                                            while (True):
                                                target = os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+str(index)+".mpd")
                                                if (os.path.exists(target)):
                                                    index += 1
                                                    continue
                                                if (hashify(value) in mapping):
                                                    value += "\n<!--"+mapping[hashify(value)]+"-->"
                                                descriptor = open(target, "w")
                                                descriptor.write(value)
                                                descriptor.close()
                                                break
                                            continue
                                        try:
                                            index = 0
                                            target = ""
                                            while (True):
                                                target = os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+str(index)+".mpd")
                                                if (os.path.exists(target)):
                                                    index += 1
                                                    continue
                                                if (hashify(value) in mapping):
                                                    value += "\n<!--"+mapping[hashify(value)]+"-->"
                                                descriptor = open(target, "w")
                                                descriptor.write(value)
                                                descriptor.close()
                                                break
                                            if not (len(target) == 0):
                                                tree = xml_tree.parse(target)
                                                base = tree.getroot()
                                                handles = handle(base, None)
                                                for handled in handles:
                                                    mimes.append([handled, creative_id])
                                        except:
                                            logging.error(traceback.format_exc())
                                        continue
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
                                        esprima_ast_strings.append([json.loads("\n".join(lines)), creative_id])
                                    else:
                                        values.append(value)
            except:
                logging.error(traceback.format_exc())
        for mime in mimes:
            creative_id = mime[1]
            origin = mime[0]
            if (sys.flags.debug):
                print(str(mime))
            if ("googlevideo.com" in origin):
                if (os.path.exists(os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+hashify(origin)+".mp4"))):
                    if (sys.flags.debug):
                        print(os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+hashify(origin)+".mp4"))
                    continue
            try:
                record.append([origin])
                mime = requests.get(origin)
                record[len(record)-1].append(str(mime.status_code))
                if ("200" in str(mime.status_code)):
                    headers = mime.headers
                    mime = mime.content
                    extension = None
                    for header in headers:
                        if not (header.strip().lower() == "content-type"):
                            continue
                        extension = str(headers[header])
                        if (";" in extension):
                            extensions = extension.split(";")
                            extension = None
                            for i in range(len(extensions)):
                                if ("/" in extensions[i]):
                                    extension = extensions[i].strip()
                                    break
                    if not (extension == None):
                        extension = mimetypes.guess_extension(extension)
                    if (extension == None):
                        extension = "."+str(extension)
                        if (sys.flags.debug):
                            print(extension)
                            print(str(headers))
                    if ((mime.startswith("<!DOCTYPE html>".encode("UTF-8"))) or (mime.startswith("<html>".encode("UTF-8")))):
                        nodes = []
                        try:
                            soup = BeautifulSoup(mime.decode("UTF-8"))
                            scripts = soup.find_all("script")
                            for script in scripts:
                                nodes.append(str(script.string))
                        except:
                            logging.error(traceback.format_exc())
                        for value in nodes:
                            #print(value)
                            if (len(value) < limit):
                                if (sys.flags.debug):
                                    print(value)
                                continue
                            if (value.startswith("<?xml ")):
                                if (sys.flags.debug):
                                    print(creative_id)
                                    print(value)
                                if ("xmlns=\"urn:mpeg:dash:schema:mpd:" in value.lower()):
                                    index = 0
                                    while (True):
                                        target = os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+str(index)+".mpd")
                                        if (os.path.exists(target)):
                                            index += 1
                                            continue
                                        if (hashify(value) in mapping):
                                            value += "\n<!--"+mapping[hashify(value)]+"-->"
                                        descriptor = open(target, "w")
                                        descriptor.write(value)
                                        descriptor.close()
                                        break
                                    continue
                                try:
                                    index = 0
                                    target = ""
                                    while (True):
                                        target = os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+str(index)+".mpd")
                                        if (os.path.exists(target)):
                                            index += 1
                                            continue
                                        if (hashify(value) in mapping):
                                            value += "\n<!--"+mapping[hashify(value)]+"-->"
                                        descriptor = open(target, "w")
                                        descriptor.write(value)
                                        descriptor.close()
                                        break
                                    if not (len(target) == 0):
                                        tree = xml_tree.parse(target)
                                        base = tree.getroot()
                                        handles = handle(base, None)
                                        for handled in handles:
                                            mimes.append([handled, creative_id])
                                except:
                                    logging.error(traceback.format_exc())
                                continue
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
                                esprima_ast_strings.append([json.loads("\n".join(lines)), creative_id])
                            else:
                                values.append(value)
                    if not (os.path.exists(os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+hashify(origin)+str(extension)))):
                        descriptor = open(os.path.join(os.getcwd(), advertisor_id+"_"+creative_id+"_"+hashify(origin)+str(extension)), "wb")
                        descriptor.write(mime)
                        descriptor.close()
            except:
                logging.error(traceback.format_exc())
        mimes = []
    records += values
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
            print(str(output.decode("UTF-8")))
        except:
            logging.error(traceback.format_exc())
if (os.path.exists(str(shutil.which("ffmpeg")))):
    for root, folders, files in os.walk(os.getcwd()):
        for name in files:
            if ((name.endswith(".m3u")) or (name.endswith(".m3u8"))):
                if not (os.path.exists(os.path.join(root, name+".mp4"))):
                    command = []
                    command.append("ffmpeg")
                    command.append("-allowed_extensions")
                    command.append("ALL")
                    command.append("-protocol_whitelist")
                    command.append("file,http,https,crypto,tcp,tls")
                    command.append("-loglevel")
                    command.append("debug")
                    command.append("-i")
                    command.append(os.path.join(root, name))
                    command.append(os.path.join(root, name+".mp4"))
                    try:
                        output = subprocess.check_output(command)
                        print(str(output.decode("UTF-8")))
                    except:
                        logging.error(traceback.format_exc())
                    time.sleep(1)
        break
descriptor = open(os.path.join(os.getcwd(), sys.argv[0]+".json"), "w")
descriptor.write(json.dumps(records+record))
descriptor.close()

