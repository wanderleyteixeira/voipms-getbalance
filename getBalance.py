#!/usr/bin/python

# Usage: python3.7 getBalance.py

from voipms import VoipMs
import boto3, os, http.client, urllib

def usage():
  print('Usage: '+sys.argv[0]+'')

def initAccount(user, password):
    voip = VoipMs(user, password)
    return voip

def getBalance(voip):
    total = voip.general.get.balance(advanced=False)
    voipms_total = round(float(total['balance']['current_balance']),2)
    s = f"""<response>
   <error>0</error>
   <balanceString>${voipms_total}</balanceString>
</response>
"""
    #print(s)
    f = open('/home/balance.voipms', 'w')
    f.write(s)
    f.close()
    pushover(voipms_total)

def uploadS3():
    session = boto3.Session(
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],)
    s3 = session.resource('s3')
    s3.meta.client.upload_file(Filename=os.environ["ACROBITS_FILENAME"], Bucket=os.environ["AWS_S3_BUCKET"], Key=os.environ["ACROBITS_FILENAME"])

def pushover(voipms_total):
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request("POST", "/1/messages.json",
            urllib.parse.urlencode({
                "token": os.environ["PUSHOVER_TOKEN"],
                "user": os.environ["PUSHOVER_USER"],
                "message": "VoIP.ms balance: $%s" % voipms_total,
                }), { "Content-type": "application/x-www-form-urlencoded" })
    conn.getresponse()

if __name__ == "__main__":
    import sys
    client = initAccount(os.environ["VOIPMS_USER"], os.environ["VOIPMS_KEY"])
    getBalance(client)
    uploadS3()

