# -*- coding: utf-8 -*-
"""
Created on Tues Dec 03 2024
Updated on Tues Dec 23 2025

@author: Tess Grynoch and Lisa Palmer

License: MIT License 
"""
#Load Libraries
import json
import requests #APIs
import re #regular expressions

#%%


#Input your Open Respository url. 
#If you do not want to submit your repository url each time, paste you url in quotes after the equal symbol. 
repository = input("Repository url (ex. https://repository.escholarship.umassmed.edu)")

#Input the item ID located on edit page of item
item = input("Item ID:") 

# 1.	Pull in data for individual record from Open Repository REST API
itemurl = repository + "/server/api/core/items/"+ item
response = requests.get(itemurl)
data = response.json()
#print(response.json()) #For testing purposes to check what data is pulled from the repository

# 2. Edit JSON to display in standard key: value pairs
#Extract metadata element which houses all pertinent information
metadata = data["metadata"]

#Convert list to JSON format and print JSON for easier viewing.
def jprint(obj):
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

jprint(metadata)

#Turn JSON into variable data
data = json.dumps(response.json(), sort_keys=True, indent=4)

#Remove language, authority, confidence, and places child keys from JSON
#For elements that only have a single value
keysneeded = ["dc.date.issued","dc.description.abstract", "dc.identifier.uri","dc.publisher", "dc.title","dc.type"]
singles = {key: metadata[key] for key in keysneeded}

singles2 = {} #create empty dictionary for them to go in
#pair key with text from value 
for key, value in singles.items():
    x=value[0]
    for inner_key, inner_value in x.items():
        if inner_key == "value":
            singles2[key]= inner_value
            
#For elements that have multiple values (authors and orcids)
#For records with multiple authors - create a dictionary for authors called creators early and iterate on the values
#Determine the number of authors by calculating the length of (number of elements in) "dc.contributor.author"
authorcount = len(metadata["dc.contributor.author"])

#create a vector with author numbers to pull from for numbering
authornumbers = list(map(str, (list(range(1,authorcount+1)))))

#if there is a single author we can treat it as an element with a single value
authors = {}
if authorcount == 1:
    for key, value in metadata["dc.contributor.author"][0].items():
        if key == "value":
            authors["dc.contributor.author"]= value
            
#replace each dc.contributor.author with dc.contributor.author# with the number
# being the author order 
if authorcount > 1 :
    for i in authornumbers:
        x= int(i) - 1
        for key, value in metadata["dc.contributor.author"][x].items():
            if key == "value":
                authors["dc.contributor.author"+i]= value
                
# Create list of dc.contributor.author keys based on author count
dcauthorkeys = []
if authorcount > 1 :
    for i in authornumbers:
        dcauthorkeys.append("dc.contributor.author" + i)
else:
    dcauthorkeys.append("dc.contributor.author")

#Solution for multiple orcids
#if there is a single orcid id we can treat it as an element with a single value

if "dc.identifier.orcid" in metadata.keys():
    orcid = {}
    if authorcount == 1:
        for key, value in metadata["dc.identifier.orcid"][0].items():
            if key == "value":
                orcid["dc.identifier.orcid"]= value        
    if authorcount > 1 :
        PrintORCIDs = re.findall(r'\d\d\d\d-\d\d\d\d-\d\d\d\d-\d\d\d\d', json.dumps(metadata))

#merge singles, authors, and orcid dictionaries together
# define Merge function to combine two dictionaries
def Merge(dict1, dict2):
  for i in dict2.keys():
      dict1[i]=dict2[i]
  return dict1

doimetadata = Merge(singles2, authors)
if authorcount==1 and "dc.identifier.orcid" in metadata.keys():
    doimetadata = Merge(doimetadata, orcid)

# 3. Transform relevant JSON fields to DataCite JSON standards 
    
#transform is the function to add a parent level to the dictionary using an 
# existing key in the dictionary
def transform(dct, affected_keys):
    new_dct = dct.copy()
    for new_key, keys in affected_keys.items():
        new_dct[new_key] = {key: new_dct.pop(key) for key in keys}
    return new_dct
  
#Select only the fields needed for DataCite metadata
#Create dictionary for authors
authors = {key:{key: doimetadata[key]} for key in dcauthorkeys}
for i in dcauthorkeys:
    field = authors[i].pop(i)
    authors[i]["name"] = field
authors = transform(authors, {"creators": dcauthorkeys})
#Create dictionary for all other fields taking into account items 
# without an orcid and/or items with multiple authors 
if ('dc.identifier.orcid' in doimetadata.keys() and authorcount == 1):
    doimetadata = {key: doimetadata[key] for key in doimetadata.keys() 
             & {'dc.date.issued','dc.description.abstract',
                'dc.identifier.uri','dc.publisher','dc.title',
                'dc.type','dc.identifier.orcid'}}
else: 
  doimetadata = {key: doimetadata[key] for key in doimetadata.keys() 
       & {'dc.date.issued','dc.description.abstract',
          'dc.identifier.uri','dc.publisher','dc.title',
          'dc.type'}} 
#Combine the two dictionaries using Merge function defined below 
doimetadata = Merge(authors, doimetadata) 

#Rename keys to DataCite keys and add consistent fields 
field = doimetadata.pop("dc.publisher")
doimetadata["publisher"] = field
field = doimetadata.pop("dc.title")
doimetadata["title"] = field
field = doimetadata.pop("dc.date.issued")
doimetadata["publicationYear"] = field
field = doimetadata.pop("dc.description.abstract")
doimetadata["description"] = field
field = doimetadata.pop("dc.identifier.uri")
doimetadata["url"] = field
#create language field and set to English
doimetadata["language"] = "en"
field = doimetadata.pop("dc.type")
doimetadata["resourceTypeGeneral"] = field
if 'dc.identifier.orcid' in doimetadata.keys():
    field = doimetadata.pop("dc.identifier.orcid")
    doimetadata["nameIdentifier"] = field
#set language field for abstract to English and descriptionType as abstract
doimetadata["lang"] = "en"
doimetadata["descriptionType"] = "Abstract"
#Update publication year from a full date in ISO to just year
year = doimetadata["publicationYear"]
doimetadata["publicationYear"] = year[0:4]
#Create url from handle
handle = doimetadata["url"].split('/')
handle = "https://repository.escholarship.umassmed.edu/handle/20.500.14038/" + handle[4]
doimetadata["url"] = handle
#print(doimetadata)

#%%
#Update author info. Differentiate personal and organizational names and
# split personal names into given name and family name 
#Personal authors are identified as having a comma and corporate authors as non-comma
for i in dcauthorkeys:
    if "," in doimetadata["creators"][i]["name"]:
        doimetadata["creators"][i]["nameType"] = "Personal"
        fullname = doimetadata["creators"][i]["name"].split(', ')
        doimetadata["creators"][i]["givenName"] = fullname[1]
        doimetadata["creators"][i]["familyName"] = fullname[0]  
    else:
        doimetadata["creators"][i]["nameType"] = "Organizational"
        doimetadata["creators"][i]["givenName"] = ""
        doimetadata["creators"][i]["familyName"] = ""
#print(doimetadata)

#%%
#Map document types to resourceTypeGeneral and resourceType
#Removing resource type for Dataset, Preprint, and report because they
#are redundant
#Everything else in given the general type of Text
doimetadata["resourceType"] = doimetadata["resourceTypeGeneral"]

#man, really?
#to do : refacotor this decission tree. find a new algo if possible 
if doimetadata["resourceTypeGeneral"] == "Doctoral Dissertation":
    doimetadata["resourceTypeGeneral"] = "Dissertation"
elif doimetadata["resourceTypeGeneral"] == "Master's Thesis":
    doimetadata["resourceTypeGeneral"] = "Dissertation"
elif doimetadata["resourceTypeGeneral"] == "Newsletter":
    doimetadata["resourceTypeGeneral"] = "Text"
elif doimetadata["resourceTypeGeneral"] == "Poster":
    doimetadata["resourceType"] = "Conference Poster"
    doimetadata["resourceTypeGeneral"] = "Text"
elif doimetadata["resourceTypeGeneral"] == "Presentation":
    doimetadata["resourceType"] = "Conference Presentation"
    doimetadata["resourceTypeGeneral"] = "Text"
elif doimetadata["resourceTypeGeneral"] == "Other":
    doimetadata["resourceTypeGeneral"] = "Text"
elif doimetadata["resourceTypeGeneral"] == "Podcast":
    doimetadata["resourceType"] = "Podcast"
    doimetadata["resourceTypeGeneral"] = "Sound"
elif doimetadata["resourceTypeGeneral"] == "Video":
    doimetadata["resourceType"] = "Video"
    doimetadata["resourceTypeGeneral"] = "Audiovisual"
elif doimetadata["resourceType"] == "Dataset": 
    doimetadata.pop("resourceType")
elif doimetadata["resourceType"] == "Preprint":
    doimetadata.pop("resourceType")
elif doimetadata["resourceType"] == "Report":
    doimetadata.pop("resourceType")
else: doimetadata["resourceTypeGeneral"] = "Text"

#%%
#Add parent values and order to create structure of final json file for upload to DataCite
data3 = doimetadata
data3 = transform(data3, {"titles":["title"]})
data3 = transform(data3, {"descriptions":["lang","description","descriptionType"]})
if 'resourceType' in data3.keys():
    data3 = transform(data3, {"types":["resourceType", "resourceTypeGeneral"]})
else:
    data3 = transform(data3, {"types":["resourceTypeGeneral"]})
  
#Create affiliation dictionary and append
#Assumes all authors are affiliated with the same institution
#Authors who are not affiliated with the institution need to have their affiliation manually updated in the DataCite record
affiliationName = input("Institutional affiliation for authors. Assumes all authors are affiliated with the same institution. Authors who are not affiliated with the institution need to have their affiliation manually updated in the DataCite record")
affiliationRORID = input("Affiliation ROR ID. Get from https://ror.org/. (ex. https://ror.org/0464eyp60)")
affiliation = {"affiliation": {
                        "affiliationIdentifier": affiliationRORID,
                        "affiliationIdentifierScheme": "ROR",
                        "name": affiliationName,
                        "schemeUri": "https://ror.org/"
                    }}
for i in dcauthorkeys:
    data3["creators"][i] = Merge(data3["creators"][i], affiliation)

#Add ORCID to creator if applicable
if 'nameIdentifier' in data3.keys():
    orcidurl = "https://orcid.org/" + doimetadata["nameIdentifier"]
    orcid = {"nameIdentifiers": {
                                "schemeUri": "https://orcid.org",
                                "nameIdentifier": orcidurl,
                                "nameIdentifierScheme": "ORCID"}}  
    data3["creators"]["dc.contributor.author"] = Merge(data3["creators"]["dc.contributor.author"], orcid)
    del data3["nameIdentifier"]

#Remove creator group keys  
data3["creators"] = [data3["creators"].pop(key) for key in dcauthorkeys]

#Add type and prefix
data3["type"] = "dois"
#Test prefix #Use production prefix when ready to mint draft DOIs on the production server
data3["prefix"] = input("DOI prefix for repository")
data3 = transform(data3, {"attributes":["prefix","creators","titles","publisher",
                                        "publicationYear","language","types",
                                        "descriptions","url"]})
#Make data the first key
data3 = transform(data3, {"data":["type","attributes"]})
#print(data5)

#%%
#Write JSON file called DataCiteUpload
data3json = json.dumps(data3, indent = 4)
with open('DataCiteUpload.json', 'w') as file:

    # write
    file.write(data3json)
#%%
# 4. Use DataCite REST API to mint Draft DOI
data4 = open('DataCiteUpload.json')

# url for testing server
url = "https://api.test.datacite.org/dois"
# url for production server
# url = "https://api.datacite.org/dois"

authorization = input("Authorization key from https://support.datacite.org/reference/post_dois")

payload = data4.read()
headers = {"content-type": "application/json",
    "authorization": authorization
}

response = requests.post(url, data=payload, headers=headers)

print(response.text)

#%%
#Save the json to check the response
with open('DataCiteDoiMetadata.json', 'w') as file:

    # write
    file.write(response.text)
    
#%%
# 5. Pull DataCite DOI for item using DataCite REST API response
#Start with DataCiteDoiMetadata.json which was the response.text
with open('DataCiteDoiMetadata.json','r') as file:
  # read JSON data
  data5 = json.load(file)
  newdoi = data5["data"]["id"] #new doi variable to upload to Open Repository 
  handle = data5["data"]["attributes"]["url"] #url for item in Open Repository

#Print reminder text in Python and save as text file with item id
if (authorcount > 1 and 'dc.identifier.orcid' in metadata):
    print("Add " + newdoi + " to " + handle + "and add the following ORCID iD(s) to their corresponding author(s): " + ', '.join(map(str, PrintORCIDs))) 
else:
    print("Add " + newdoi + " to " + handle)
if (authorcount > 1 and 'dc.identifier.orcid' in metadata):
    Reminder = "Add " + newdoi + " to " + handle + "and add the following ORCID iD(s) to their corresponding author(s): " + ', '.join(map(str, PrintORCIDs))
else:
    Reminder = "Add " + newdoi + " to " + handle
ReminderFileName = "newdoiReminder_" + item + ".txt" 
with open(ReminderFileName, 'w') as file:
    file.write(Reminder)

#%%
# 6. Update Repository record with DOI - add DOI to dc.identifier.doi – use Open Repository REST API

#Create the patch JSON file
patchdoi = {}
patchdoi["op"] = "add" 
patchdoi["path"] = "/metadata/dc.identifier.doi"
patchdoi["value"] = {"value": newdoi}
patchdoi2 =[patchdoi]

patchdoi_json = json.dumps(patchdoi2, indent=4)

with open('patchdoi.json', 'w') as file:

    # write
    file.write(patchdoi_json)
    
#Gain authorization to make edits to Open Repository site. 
#Need JSON Web token in the Authorization header from this call response

# Get cookie and token for authorization from Open Repository website. 
#Instructions: Open the console in your browser's developer tools and run a search.
#Navigate to the Network view, select one of the GET responses to copy 
#the xsrfcookie and xsrftoken from the request headers.
xsrfcookie = input("xsrfcookie from Open Repository site. See instructions in code.")
xsrftoken = input("xsrftoken from OpenRepository site. See instructions in code.")

# Username and password of admin with permission to make edits to records
username = input("Open Repository admin username")
password = input("Open Repository admin password")

cookies = {
    'DSPACE-XSRF-COOKIE': xsrfcookie,
}

headers = {
    'X-XSRF-TOKEN': xsrftoken,
    # 'Cookie': 'DSPACE-XSRF-COOKIE={xsrf-cookie}',
    'Content-Type': 'application/x-www-form-urlencoded',
}

login = {
    'user': username,
    'password': password,
}

repologin = repository + "/server/api/authn/login"
authresponse = requests.post(repologin, cookies=cookies, headers=headers, data=login)

print(authresponse.headers)

#Adding DOI to record
bearer = authresponse.headers["Authorization"]
bearer0 = bearer[7:]
accessToken = '{{"accessToken":"'+bearer0+'"}}'

cookies = {
    'DSPACE-XSRF-COOKIE': xsrfcookie,
    'dsAuthInfo': accessToken,
}

headers = {
    'Authorization': bearer,
    'X-XSRF-TOKEN': xsrftoken,
    'Content-Type': 'application/json',
    # 'Cookie': 'DSPACE-XSRF-COOKIE={csrf}; dsAuthInfo={{"accessToken":"{bearer}"}}',
}


data6 = open('patchdoi.json')
data7 = data6.read()

doiuploadresponse = requests.patch(itemurl, cookies=cookies, headers=headers, data=data7)

print(doiuploadresponse.text)


