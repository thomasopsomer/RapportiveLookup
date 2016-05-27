# -*- coding: utf-8 -*-
# @Author: thomasopsomer

from rapportive_client import RapportiveClient, COLUMNS, get_token
import unicodecsv as csv
import begin


@begin.start
@begin.convert(email_position=int, header=bool)
def main(input_path, output_path, header=True, email_position=2):
    """ """
    # get list of email to process
    with open(input_path, "r") as csvfile:
        emails = []
        email_csv = csv.reader(csvfile, delimiter=',', quotechar='"')
        if header:
            email_csv.next()
        for row in email_csv:
            emails.append(row[email_position])

    # number of lines in output file
    with open(output_path, "r") as csvfile:
        N = len(csvfile.readlines())

    # Init rapportive client
    curl_string = None
    token = None
    #curl_string = raw_input('Enter curl statement {} : ')
    token = raw_input('Enter token: ')
    client = RapportiveClient(token=token, curl_string=curl_string)

    # process emails and write result to csv output file
    with open(output_path, "a+") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=COLUMNS)
        if N == 0:
            writer.writeheader()

        for email in emails:
            try:
                r = client.get_info(email)
            except:
                curl_string = raw_input('Enter new curl statement {} : ')
                token = get_token(curl_string)
                client.change_token(token)
                r = client.get_info(email)

            writer.writerow(r)
            # writer.writerow(dict((k, str(v)) for k, v in r.items()))