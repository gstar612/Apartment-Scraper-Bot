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

from typing import Optional
from functools import cached_property

import yagmail
from json2html import *


class Apartment:
    """Class representing an Apartment"""
    def __init__(self, apartment):
        self.unit = apartment.get('Unit')
        self.type = apartment.get('Type')
        self.baths = int(apartment.get('Baths', 0))
        self.sqft = int(apartment.get('SqFt', 0))
        self.building = int(apartment.get('Building', 0))
        self.floor = int(apartment.get('Floor', 0))
        self.rent = apartment.get('Rent')
        self.availability = apartment.get('Available')
        self.complex = apartment.get('Complex')


class HollySt:
    """Class representing the Holly St Complex"""
    def __init__(self) -> None:
        self.url = os.environ['APT_HOLLYST_URL']
        self.ids = ['1024819', '1024820', '1024821', '1024822', '1024823', '1024824']
        self.apartments = [Apartment(apt) for apt in self.apartment_data]

    @cached_property
    def apartment_data(self) -> Optional[list]:
        """Cached Property:
        Get call to the Holly St website and parse HTML response for relevant
        apartment data. Return list of apartments(dicts).
        """
        try:
            floorplans_resp = requests.get(f'{self.url}/floorplans.aspx').text
            floorplans_lines = floorplans_resp.split('\n')
            apartment_data = []
            available_units = [
                apt_id
                for line in floorplans_lines
                for apt_id in self.ids
                if f'floorPlans={apt_id}' in line
                and 'Availability' in line
            ]

            for unit in available_units:
                apt_response = requests.get(f'{self.url}/availableunits.aspx?&floorPlans={unit}').text
                apt_lines = apt_response.split('\n')
                apt_details = dict()
                for apt_line in apt_lines:
                    if 'Floor Plan : ' in apt_line:
                        header = apt_line.split('<h3>')[-1].split('</h3>')[0]
                        apt_details['Baths'] = header.split(', ')[-1].split()[0]
                        apt_details['Type'] = header.split(': ')[-1].split(' -')[0]
                        apt_details['Complex'] = 'Holly St.'
                        apt_line_list = apt_line.split()
                        for item in apt_line_list:
                            if "data-label='Rent'>" in item:
                                apt_details['Rent'] = item.split("'>")[-1].split('<')[0]
                            if "Ft.'>" in item:
                                apt_details['SqFt'] = item.split("'>")[-1].split('<')[0]

                            if "data-label='Apartment'>" in item:
                                apt_details['Unit'] = item.split("'>")[-1].split('<')[0]
                            if "MoveInDate=" in item:
                                apt_details['Available'] = item.split('MoveInDate=')[-1].split("')")[0]
                        break

                apartment_data.append(apt_details)

        except Exception as e:
            apartment_data = None

        return apartment_data


class Brand:
    """Class representing the Brand Apartments Complex"""
    def __init__(self) -> None:
        self.url = os.environ['APT_BRAND_URL']
        self.apartments = [Apartment(apt) for apt in self.apartment_data]

    @cached_property
    def apartment_data(self) -> Optional[list[dict]]:
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
            apartment_data = [dict(apt, **{'Complex': 'The Brand'}) for apt in apartment_data]

        except Exception as e:
            apartment_data = None

        return apartment_data


def main():

    recipient = os.environ['APT_BOT_RECIPIENT']
    sender = os.environ['APT_BOT_SENDER']
    password = os.environ['APT_BOT_SENDER_PWD']

    # Initialize server connection
    client = yagmail.SMTP(user=sender, password=password)

    # Initialize instance of Brand Apartments & Holly St Apartments Class
    the_brand = Brand()
    holly_st = HollySt()

    # Ensure apartment data is valid, otherwise send error alert email & exit
    if not the_brand.apartments or not isinstance(holly_st.apartments, list):
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

    # Create list of The Brand apartments(dicts) if criteria is met
    the_brand_list = [
        {
            'Unit': apt.unit,
            'Building': apt.building,
            'Floor': apt.floor,
            'Type': apt.type,
            'Baths': apt.baths,
            'Sq. Footage': apt.sqft,
            'Rent': f'${apt.rent}',
            'Availability': apt.availability,
            'Complex': apt.complex
        }
        for apt in the_brand.apartments
        if (apt.sqft >= 900) and (apt.floor == 1 or apt.floor == 6)
    ]

    # Create list of Holly St apartments(dicts) if criteria is met
    holly_st_list = [
        {
            'Unit': apt.unit,
            'Building': apt.building,
            'Floor': apt.floor,
            'Type': apt.type,
            'Baths': apt.baths,
            'Sq. Footage': apt.sqft,
            'Rent': f'${apt.rent}',
            'Availability': apt.availability,
            'Complex': apt.complex
        }
        for apt in holly_st.apartments
        if apt.availability
    ]

    list_of_all_apartments = the_brand_list + holly_st_list

    # Ensure list_of_apartments is not null otherwise exit script
    if not list_of_all_apartments:
        raise SystemExit('There were no apartments that matched specified criteria.')

    # Sort list by Square Footage
    list_of_all_apartments.sort(key=lambda i: i['Sq. Footage'], reverse=True)

    # Convert list of apartments to HTML
    html = json2html.convert(json=list_of_all_apartments, table_attributes='border=\"0\" cellpadding=\"10\"')
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
