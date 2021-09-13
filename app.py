"""This is a sample script for Avoid-the-3Cs_via_Meraki-Camera.

Copyright (c) 2021 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

from flask import Flask, render_template, Response
from flask import request
import cv2
import requests
from detect import personcount
from webexbg import get_from_ini, read_allparticipants

app = Flask(__name__)

meraki_api_key = ""
cam_serial = ""

headers = {
  'Authorization': 'Basic ' + get_from_ini("my_token_xapi"),
  'Content-Type': 'text/xml'
}
endpoint_ip = get_from_ini('endpoint_ip')

def get_rtspurl(cam_serial):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Cisco-Meraki-API-Key": meraki_api_key
    }

    try:
        r_rtspurl = requests.request('GET', f"https://api.meraki.com/api/v1/devices/{cam_serial}/camera/video/settings", headers=headers)
        r_rtspurl_json = r_rtspurl.json()
        return r_rtspurl_json["rtspUrl"]
    except Exception as e:
        return print(f"Error when getting image URL: {e}") 

camera = cv2.VideoCapture(get_rtspurl(cam_serial))

def gen_frames():
   while True:
       success, frame = camera.read()
       if not success:
           break
       else:
           ret, buffer = cv2.imencode('.jpg',frame)
           frame = buffer.tobytes()
           yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route("/")
def index():
    num_of_person = personcount()
    people = num_of_person[0]
    webex_users = read_allparticipants()
    return render_template("index.html", people=people, webex=webex)

@app.route('/company_booth')
def company_booth():
    num_of_person = personcount()
    people = num_of_person[0]
    webex = read_allparticipants()
    return render_template("company_booth.html", people=people, webex=webex)

@app.route('/video_feed')
def video_feed():
   return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(threaded=True)