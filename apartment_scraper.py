"""
Created By: Harrison Muncaster
Date: 03/20/2021
PY Version: 3.9
Purpose: Scrap the websites of apartment complexes im interested in
and look for specific units that fit my criteria. Email findings to myself!
"""


import requests
import json
import os
import socket
from functools import cached_property

import yagmail
from json2html import *


class Apartment:
    """Class representing an Apartment"""
    def __init__(self, apartment):
        self.unit = apartment['Unit']
        self.type = apartment['Type']
        self.baths = int(apartment['Baths'])
        self.sqft = int(apartment['SqFt'])
        self.building = int(apartment['Building'])
        self.floor = int(apartment['Floor'])
        self.rent = int(apartment['Rent'])
        self.availability = apartment['Available']


class Brand:
    """Class representing the Brand Apartments Complex"""
    def __init__(self):
        self.url = os.environ['APT_BRAND_URL']
        self.apartments = [Apartment(apt) for apt in self.apartment_data]

    @cached_property
    def apartment_data(self) -> list:
        """Cached Property:
        Get call to the Brands website and parse HTML response for relevant
        apartment data. Return list of apartments(dicts).
        """
        try:
            response = requests.get(self.url).text
            all_lines = response.split('\n')
            first_line_index = None
            last_line_index = None

            for i, line in enumerate(all_lines):

                # find index of first line & parse first line
                if 'dataSet' in line:
                    all_lines[i] = all_lines[i].split('var dataSet = ')[-1]
                    first_line_index = i

                # find index of last line & parse 2nd to last line
                if first_line_index:
                    if line.startswith('</script>'):
                        all_lines[i-1] = all_lines[i-1][:-2]
                        last_line_index = i
                        break

            apartment_data = json.loads(''.join(all_lines[first_line_index:last_line_index]))

        except Exception as e:
            apartment_data = None

        return apartment_data


def main():

    recipient = os.environ['APT_BOT_RECIPIENT']
    sender = os.environ['APT_BOT_SENDER']
    password = os.environ['APT_BOT_SENDER_PWD']

    # Initialize server connection
    client = yagmail.SMTP(user=sender, password=password)

    # Initialize instance of Brand Apartments Class
    the_brand = Brand()

    # Ensure apartment data is valid, otherwise send error alert email & exit
    if not the_brand.apartments:
        subject = 'Apartment Bot Alert ERROR!'
        body = (f'<h3 style="color:red;"><i>Attention Asshole!</i></h3>'
                f'<p>There was an issue with the Apartment Bot Automation on {socket.gethostname()}.</p>'
                f'<p>Please investigate and fix as soon as possible!!!</p>')
        try:
            # send the error alert email
            client.send(to=recipient, subject=subject, contents=body)
        except Exception as e:
            print(f'ERROR: {e}')

        raise SystemExit('Script exited without completing. Please investigate issues.')

    # Create list of apartments(dicts) if criteria is met
    list_of_apartments = [
        {
            'Unit': apt.unit,
            'Building': apt.building,
            'Floor': apt.floor,
            'Type': apt.type,
            'Baths': apt.baths,
            'Sq. Footage': apt.sqft,
            'Rent': f'${apt.rent}',
            'Availability': apt.availability
        }
        for apt in the_brand.apartments
        if (apt.sqft >= 900) and (apt.floor == 1 or apt.floor == 6)
    ]
    # Sort list by Square Footage
    list_of_apartments.sort(key=lambda i: i['Sq. Footage'], reverse=True)

    # Convert list of apartments to HTML
    html = json2html.convert(json=list_of_apartments, table_attributes='border=\"0\" cellpadding=\"10\"')
    body = (f'<h3 style="color:red;"><i>Attention Asshole!</i></h3>'
            f'<p>An apartment youve been waiting for has become available! See below!</p>'
            f'{html}')
    subject = 'Apartment Bot Alert!'

    try:
        # send the apartment email
        client.send(to=recipient, subject=subject, contents=body)
        print('Email sent successfully!')

    except Exception as e:
        print(f'ERROR: {e}')


if __name__ == '__main__':
    main()
