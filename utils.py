import pandas as pd
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime

def get_table_df(page_source, table_id):
    soup = BeautifulSoup(page_source, 'html.parser')
    tables = soup.find('table', attrs={"id":table_id})
    df = pd.read_html(str(tables))[0].dropna(how='all')
    return df.fillna('')

def flattened_data(scrapper):
    result = []
    for page in range(1, scrapper.page_no):
        try:
            if 9 - len(scrapper.contact_details[page]):
                scrapper.contact_details[page] += [''] * (9 - len(scrapper.contact_details[page]))

            codes = [300, 600, 605, 700, 705, 720, 725, 708, 728, 1000]
            study_hours_details = []
            for code in codes:
                study_hours_details += scrapper.study_hours_details.get((page, code), ['']*4)

            row = [datetime.now().strftime("%Y-%m-%d, %H:%M:%S")] +\
                    scrapper.institution_details[page] +\
                    scrapper.address_details[page] +\
                    scrapper.contact_details[page] +\
                    scrapper.study_type_details[page] +\
                    study_hours_details
            print(row)

            result.append(row)
        except KeyError:
            continue
    return result
