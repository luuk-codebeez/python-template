import requests
import argparse
import json
import time
import threading
import sys


def getConfig(config):
    f = open(config, "r")
    return json.loads(f.read(), strict=False)


def appendPR(buildRequest, pullRepo, pullId):
    if (pullRepo != False):
        buildRequest.update( { "pullRepo": pullRepo } )
        buildRequest.update( { "pullId": pullId } )
    return buildRequest


def appendOutputRepo(buildRequest, pullRepo, pullId):
    if (pullRepo != False):
        buildRequest.update( { "pullRepo": pullRepo } )
        buildRequest.update( { "pullId": pullId } )
    return buildRequest


def triggerBuild(buildRequests, code):
    url = "https://blimpfunc.azurewebsites.net/api/HttpBuildPipeline_HttpStart"
    querystring = {"code": code}
    payload = json.dumps(buildRequests)
    headers = {
        'Content-Type': "application/json",
        'cache-control': "no-cache"
        }
    response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
    print(response.content.decode('utf-8'))
    return json.loads(response.content.decode('utf-8'), strict=False)


def getStatusQueryGetUri(jsonResponse):
    return jsonResponse["statusQueryGetUri"]


def pollPipeline(statusQueryGetUri):
    url = statusQueryGetUri
    headers = {
        'cache-control': "no-cache"
        }
    response = requests.request("GET", url, headers=headers)
    print(response.content.decode('utf-8'))
    return json.loads(response.content.decode('utf-8'), strict=False)


def buildImage(br, code, results, outputMessage):
    tries = 0
    success = False
    while tries < 1:
        try:
            tries = tries + 1
            print("building")
            print(br)
            statusQueryGetUri = getStatusQueryGetUri(triggerBuild(br, code))
            print(statusQueryGetUri)
            while True:
                time.sleep(60)
                content = pollPipeline(statusQueryGetUri)
                runtimeStatus = content["runtimeStatus"]
                if runtimeStatus == "Completed":
                    print("build completed")
                    print(content["output"].replace("\\", "/"))
                    output = json.loads(content["output"].replace("\\", "/"), strict=False)
                    status = output["status"]
                    if (status == "success"):
                        print("pass")
                        success = True
                        break
                    else:
                        print("failed")
                        break
                elif runtimeStatus == "Running":
                    print("running")
                    continue
                else:
                    print("failed")
                    break
            if success:
                break
            else:
                print("trying again")
                print(br)
                continue
        except:
            print(sys.exc_info())
    if success:
        results.append(True)
        outputMessage.append(
            "Build request Succeed on following input: \n" + json.dumps(br))
        sys.exit(0)
    else:
        results.append(False)
        outputMessage.append(
            "Build request Failed on following input: \n" + json.dumps(br) + "\n" +
            "failure message: \n" + content["output"].replace("\\", "/"))
        sys.exit(1)


parser = argparse.ArgumentParser()
parser.add_argument('--config', help='config file')
parser.add_argument('--code', help='code')
parser.add_argument('--pullId', help='pullId')
parser.add_argument('--pullRepo', help='pullRepo')
args = parser.parse_args()

config = args.config
code = args.code
pullRepo = args.pullRepo
pullId = args.pullId

print("config")
print(config)
print("pullRepo")
print(pullRepo)
print("pullId")
print(pullId)

threads = []
results = []
outputMessage = []
buildRequests = getConfig(config)
for br in buildRequests:
    br = appendPR(br, pullRepo, pullId)
    print(br)
    t = threading.Thread(target=buildImage, args=((br, code, results, outputMessage)))
    threads.append(t)
    t.start()
    time.sleep(60)

# Wait for all of them to finish
for t in threads:
    t.join()

print("------------------------------------------------------------------------")

withfailures = False

for r in results:
    if r == False:
        withfailures = True

if (withfailures):
    print("Runs completed with Failures")
else:
    print("Runs completed with no Failures")

for msg in outputMessage:
    print(msg)

if (withfailures):
    sys.exit(1)
else:
    sys.exit(0)
