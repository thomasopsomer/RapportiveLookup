# -*- coding: utf-8 -*-
# @Author: ThomasO

"""
curl 'https://api.linkedin.com/v1/people/email=thomasopsomer.enpc%40gmail.com:(first-name,last-name,headline,location,distance,positions,twitter-accounts,im-accounts,phone-numbers,member-url-resources,picture-urls::(original),site-standard-profile-request,public-profile-url)' \
    -H 'x-li-format: json' \
    -H 'oauth_token:  nDE-JQ0wuLuODWBQMj4ZYw5HC-uI09GDhBCVkk' \
    --compressed

    {u'distance': 0,
     u'firstName': u'Thomas',
     u'headline': u'Data Scientist chez The Assets',
     u'lastName': u'Opsomer',
     u'location': {u'country': {u'code': u'fr'}, u'name': u'Paris Area, France'},
     u'pictureUrls': {u'_total': 1,
                      u'values': [u'https://media.licdn.com/mpr/mpr/p/1/005/09e/335/267a549.jpg']},
     u'positions': {u'_total': 1,
                    u'values': [{u'company': {u'id': 5004979,
                                              u'industry': u'Technologies et services de l\u2019information',
                                              u'name': u'The Assets',
                                              u'size': u'11-50',
                                              u'type': u'Public Company'},
                                 u'id': 643366341,
                                 u'isCurrent': True,
                                 u'location': {u'country': {u'code': u'fr',
                                                            u'name': u'France'},
                                               u'name': u'Paris Area, France'},
                                 u'startDate': {u'month': 1, u'year': 2015},
                                 u'title': u'Data Scientist'}]},
     u'publicProfileUrl': u'https://www.linkedin.com/in/thomas-opsomer-94366388',
     u'siteStandardProfileRequest': {u'url': u'https://www.linkedin.com/profile/view?id=AAoAABKbR4MBLaCIfu6MWNbYpBbZJppDaHLvk2M&authType=name&authToken=rmPD&trk=api*a109924*s118458*'}}

"""

import json
import unicodedata
import re
import requests
import logging
from pprint import pprint


# logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 2. Add handler
steam_handler = logging.StreamHandler()
steam_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
steam_handler.setFormatter(formatter)
logger.addHandler(steam_handler)

# Disable requests logging
logging.getLogger("requests").setLevel(logging.WARNING)

# global params
COLUMNS = ["email", "firstName", "lastName", "phoneNumber", "country_code",
           "country_name", "headline",
           "title_0", "title_1", "title_2",
           "co_name_0", "co_id_0", "co_type_0", "co_industry_0", "co_size_0",
           "co_name_1", "co_id_1", "co_type_1", "co_industry_1", "co_size_1",
           "co_name_2", "co_id_2", "co_type_2", "co_industry_2", "co_size_2"]


# ### Rapportive Client Class
class RapportiveClient(object):
    """
    Client to use the linkedin API through token given by the rapportive
    plugin for gmail.
    """
    def __init__(self, token=None, curl_string=None):
        """
        Instantiate the client with your token or the curl_string that
        you can get in gmail -> inspect -> network -> Copy As Curl
        """
        if curl_string is not None:
            token = get_token(curl_string)
        if token is None:
            raise ValueError("you need to provide a token or the curl as string")
        self.token = token

    def get_raw_info(self, email, verbose=False):
        """
        Make the 'call' to linkedin API, using the `token` found in your gmail :)
        Handle error:
            - 401: Unauthorized (token expired)
            - 403: Too much call for this token
            - 404: No result found for this email
        if 401 or 403 : need to change token 
        """
        URL = """https://api.linkedin.com/v1/people/email={}:(first-name,last-name,headline,location,distance,positions,twitter-accounts,im-accounts,phone-numbers,member-url-resources,picture-urls::(original),site-standard-profile-request,public-profile-url)""" \
            .format(email.replace("@", "%40"))
        headers = {"x-li-format": "json",
                   "format": "json",
                   "oauth_token": self.token}

        r = requests.get(URL, headers)
        r_json = json.loads(r.content)
        if r.status_code == 200:
            logger.info("Status code: %s - Email: %s found" % (r.status_code, email))
            raw_info = r_json
            # add email
            raw_info["email"] = email
            if verbose:
                pprint(raw_info)
        elif r.status_code == 401:
            logger.info("Status code: %s - Token has expired - %s" %
                        (r.status_code, r_json["message"]))
            raw_info = 401
        elif r.status_code == 403:
            logger.info("Status code: %s - Too much call - %s" %
                        (r.status_code, r_json["message"]))
            raw_info = 403
        elif r.status_code == 404:
            logger.info("Status code: %s - Email: %s not found" % (r.status_code, email))
            raw_info = {}
        else:
            logger.info("Status code: %s - for email %s - %s" %
                        (r.status_code, email, r_json["message"]))
            raw_info = {}
        return raw_info

    def parse_raw_info(self, res_json):
        """
        Parse the response from getInfo() into our `res` object
        res = dictionary with keys:
            firstName,      country_code,        co_name_0 .. 3,      co_industry_0 .. 3,
            lastName,       country_name,        co_id_0 .. 3,        co_size_0 .. 3
            headline,       phoneNumber,         co_type_0 .. 3,      email
        """

        res = dict((key, "") for key in COLUMNS)
        if res_json == {}:
            return res
        else:
            res["firstName"] = checkAndGet("firstName", res_json)
            res["lastName"] = checkAndGet("lastName", res_json)
            res["headline"] = checkAndGet("headline", res_json)
            res["country_code"] = checkAndGet("code", res_json["location"]["country"])
            res["country_name"] = checkAndGet("name", res_json["location"])
            #
            # phoneNumber
            if "phoneNumbers" in res_json:
                if "values" in res_json["phoneNumbers"]:
                    res["phoneNumber"] = res_json["phoneNumbers"]["values"][0]["phoneNumber"]
            #
            # Company
            if "values" in res_json["positions"]:
                for i, co in enumerate(res_json["positions"]["values"]):
                    # Limit to 3 different company
                    if i > 2:
                        break
                    # Check if more that one field in the company description
                    # if so, we get all field from a linkedin co
                    # otherwise just the name
                    if len(co["company"].keys()) > 1:
                        res["co_id_" + str(i)] = checkAndGet("id", co["company"])
                        res["co_industry_" + str(i)] = checkAndGet("industry", co["company"])
                        res["co_name_" + str(i)] = checkAndGet("name", co["company"])
                        res["co_size_" + str(i)] = checkAndGet("size", co["company"])
                        res["co_type_" + str(i)] = checkAndGet("type", co["company"])
                    elif len(co["company"].keys()) == 1:
                        res["co_name_" + str(i)] = co["company"]["name"]
                    if "title" in co:
                        res["title_" + str(i)] = co["title"]
            return res

    def get_info(self, email):
        """
        Get and parse information back from the linkedin API
        """
        res_tmp = self.get_raw_info(email)
        if res_tmp in [401, 403]:
            raise ValueError("Need a new token")
        else:
            res = {}
            res = self.parse_raw_info(res_tmp)
            res["email"] = email
            clean_res = {}
            for key, value in res.iteritems():
                if isinstance(value, str):
                    clean_res[key] = deaccent(any2unicode(value))
                else:
                    clean_res[key] = value
            return clean_res

    def change_token(self, new_token):
        self.token = new_token


# ### Functions

def get_token(curl_string):
    """ """
    pattern = r".*oauth_token:\s([A-z0-9-_]*)\'.*$"
    r = re.search(pattern, curl_string)
    if r:
        return r.group(1)


def checkAndGet(key, obj):
    if key in obj:
        return obj[key]


def any2utf8(text, errors='strict', encoding='utf8'):
    """Convert a string (unicode or bytestring in `encoding`), to bytestring in utf8."""
    if isinstance(text, unicode):
        return text.encode('utf8')
    # do bytestring -> unicode -> utf8 full circle, to ensure valid utf8
    return unicode(text, encoding, errors=errors).encode('utf8')


def any2unicode(text, encoding='utf8', errors='strict'):
    """Convert a string (bytestring in `encoding` or unicode), to unicode."""
    if isinstance(text, unicode):
        return text
    return unicode(text, encoding, errors=errors)


def deaccent(text):
    """ """
    if not isinstance(text, unicode):
        # assume utf8 for byte strings, use default (strict) error handling
        text = text.decode('utf8')
    norm = unicodedata.normalize("NFD", text)
    result = (u'').join(ch for ch in norm if unicodedata.category(ch) != 'Mn')
    return unicodedata.normalize("NFC", result)

