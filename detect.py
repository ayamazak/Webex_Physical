import requests
import json

meraki_api_key = ""

def personcount():
 camlist = []
 num_of_person=[]

 for sn in camlist:
  meraki_headers = {'X-Cisco-Meraki-API-Key': meraki_api_key}
  meraki_live_url = 'https://api.meraki.com/api/v0/devices/'+sn+'/camera/analytics/live'
  meraki_live_response = requests.get(meraki_live_url, headers=meraki_headers)
  meraki_live_response_json=json.loads(meraki_live_response.text)
  num_of_person_detected=meraki_live_response_json['zones']['0']['person']
  num_of_person.append(num_of_person_detected)
 return num_of_person

if __name__ == '__main__':
    detect_num = personcount()
    print(detect_num)
