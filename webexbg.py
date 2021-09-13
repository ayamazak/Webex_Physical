import requests
import shutil
import os
import xml.etree.ElementTree as ET
import urllib3
import http.client
import ssl
import sys
import operator
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import configparser
import csv
from collections import Counter
import ast
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
configFile = "webex_settings.ini"

def read_csv():
    csv_file = open("./test.csv", "r", errors="", newline="")
    f = csv.reader(csv_file, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
    header = next(f)
    dict_from_csv = {i[0]:i[1] for i in f}

    return dict_from_csv

def get_from_ini(key):
    if config.has_option('Settings', key):
        key_value = config['Settings'][key]
        if key == "scale_logo":
            key_value = config.getboolean('Settings',key)
        elif len(key_value) > 0 and key_value[0] == "_" and key_value[-1:] == "_":
            print(f"\n**ERROR** please configure item '{key}' in the .ini file\n")
            exit()
        return key_value
    else:
        print(f"\n**ERROR** missing entry in .ini file: {key}\nAdd this key or rename the .ini file to create a new one.")
        exit()

config = configparser.ConfigParser(allow_no_value=True)
if os.path.isfile("./" + configFile):
    try:
        config.read('./' + configFile)
        endpoint_ip = get_from_ini("endpoint_ip")
        d_inputfile = ast.literal_eval(get_from_ini("my_inputfile"))
        my_logofolder = r'{}'.format(get_from_ini("my_logofolder"))
        if my_logofolder[-1:] == "\\":
            my_logofolder = r'{}'.format(my_logofolder[:-1])
        my_token_xapi = get_from_ini("my_token_xapi")
        my_user_image_location = get_from_ini("my_user_image_location")
    except Exception as e:
        print(f"\n**ERROR** reading settings file.\n    ERROR: {e} ")
        exit()
else:
    try:
        config = configparser.ConfigParser(allow_no_value=True)
        config.add_section('Settings')
        config.set('Settings', 'endpoint_ip  ', 'IP')
        config.set('Settings', 'my_inputfile ', '{BACKGROUND_IMAGE_FILENAMES}')
        config.set('Settings', 'my_logofolder', '')
        config.set('Settings', 'my_token_xapi', 'TOKEN')
        config.set('Settings', 'my_user_image_location  ', 'User3')
        with open('./' + configFile, 'w') as configfile:
            config.write(configfile)
        print(f"\n*NOTE* configuration .ini file does not exist\n  ---> open the generated .ini file to configure this script\n")
        exit()
    except Exception as e:
        print(f"\n**ERROR** creating config file.\n    ERROR: {e} ")
        exit()

def read_allparticipants():
    getparticipant_payload = "<Command><Conference><ParticipantList><Search></Search></ParticipantList></Conference></Command>"
    participant_xml = xapiCall(headers,getparticipant_payload, endpoint_ip)
    #print(participant_xml)
    if "not found" in participant_xml:
        print(f"\n*NOTE* No active call\n")
        exit()
    if "error" in participant_xml.lower():
        print(f"\n**ERROR** Getting participant details. \n           Message: {participant_xml}\n")
        exit()
    userdomain_array = dict()
    tree = ET.fromstring(participant_xml)
    username = []
    for elem in tree.iter():
        if elem.tag == "DisplayName":
            username.append(elem.text)
    return username

def xapiCall(headers,payload,endpointip):
    conn = http.client.HTTPSConnection(endpointip, context = ssl._create_unverified_context(), timeout=20)
    try:
        conn.request("POST", "/putxml", payload, headers)
        res = conn.getresponse()
    except Exception as e:
        print(f"\n**ERROR** connecting to video device ({endpointip}).\n          Message: {e}\n")
        exit()
    if res.status == 200:
        data = res.read().decode("utf-8")
        if "error" in data.lower():
            data = "**ERROR** xapiCall: " + data.split("status=")[1].split("/>")[0]
    else:
        data = "**ERROR** xapiCall: status: " + str(res.status) + "  -- reason: " + str(res.reason)
    return data


def image_to_b64(base64object,new_logo):
    my_image_extension = new_logo.rsplit('.',1)[1].lower()
    if my_image_extension != "png":
        my_image_extension = "jpeg"  # (not 'jpg') needed by base64 encoder
    buffer = BytesIO()
    base64object.convert('RGB')
    base64object.save(buffer,format=my_image_extension)
    myimage = buffer.getvalue()
    myimage_b64 = str(base64.b64encode(myimage))[2:][:-1]
    return myimage_b64

if __name__ == '__main__':
    p_job_m = ''

    while True:
        time.sleep(10)
        # _1_ READ ALL PARTICIPANTS
        webex_users = read_allparticipants()
        print('1_ READ all the participants:', webex_users)

        dict_jobs = read_csv()
        jobs = [dict_jobs[webex_users[i]] for i in range(len(webex_users))]

        print('The jobs of the participants:', jobs)
        job_c = Counter(jobs)
        job_m = job_c.most_common()[0][0]

        if p_job_m == job_m:
            print('Already using the background for', job_m)
            continue

        p_job_m = job_m

        # _2_ PREPARE BACKGROUND FOR UPLOAD
        print('2_ PREPARE the background for', job_m)
        logos = d_inputfile
        print(logos)
        new_logo = logos[job_m]
        imBackground = Image.open(new_logo)
        back_im64 = image_to_b64(imBackground,new_logo)
        imBackground.convert('RGB').save(my_logofolder + "/_result.jpg")

        payload = "<Command><Cameras><Background><Upload><Image>" + my_user_image_location + "</Image><body>xxx</body></Upload></Background></Cameras></Command>"
        payload = payload.replace("xxx", back_im64)

        # _3_ UPLOAD BACKGROUND
        print("3_ UPLOADING background to video device @" + endpoint_ip)
        xapiresult = xapiCall(headers,payload, endpoint_ip)
        if "**ERROR**" in xapiresult:
            print(f"\n**ERROR** Can't add new background:\n {xapiresult}\n")

        # _4_ SWITCH TO BLUR
        print(f"4_ Switch to Blur and then back to {my_user_image_location} to make changes visible.")
        payl_switchbg = "<Command><Cameras><Background><Set><Mode>BlurMonochrome</Mode></Set></Background></Cameras></Command>"
        xapiresult = xapiCall(headers,payl_switchbg, endpoint_ip)
        if "**ERROR**" in xapiresult:
            print(f"\n**ERROR** Can't switch to blur:\n {xapiresult}\n")

        # _5_ SWITCH TO NEW BACKGROUND
        payl_switchbg = "<Command><Cameras><Background><Set><Image>" + my_user_image_location + "</Image><Mode>Image</Mode></Set></Background></Cameras></Command>"
        xapiresult = xapiCall(headers,payl_switchbg, endpoint_ip)
        if "**ERROR**" in xapiresult:
            print(f"\n**ERROR** Can't switch to new background\n{xapiresult}\n")

        print("____ finished ___________________________________\n")
