from lib2to3.pgen2 import driver
import sys
import time
import warnings
import traceback
import pandas as pd
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

import utils
import config
from helpers.g_sheet_handler import GoogleSheetHandler

warnings.filterwarnings("ignore")

ELEMENT_ID_INITIAL = 'ContentPlaceHolder1_tabInstituteDetails_InsDetails1_ucInstitutesDetails'
STATUS_MODE = "מאושר לתמיכה"

class DataScrapping():
    def __init__(self, browser, username, password):
        self.page_no = 0
        self.browser = browser
        self.username = username
        self.password = password
        self.user_login = False
        
        self.institution_details = {}
        self.address_details = {}
        self.contact_details = {}
        self.study_type_details = {}
        self.study_hours_details = {}

        self.study_hours_page_rows = []
        self.study_hours_code_map = {}

        self.ins_support_mode_status_for_page = {}

    def login_to_site(self):
        print("Start user login..")
        try:
            self.browser.get(config.WEB_LINK)
            self.browser.find_element(By.ID,'txtUserName').send_keys(self.username)
            print('username:', self.username)
            time.sleep(3)
            self.browser.find_element(By.ID, 'txtPassword').send_keys(self.password)
            print('password:',self.password)
            time.sleep(3)
            self.browser.find_element(By.ID, 'LoginButton').click()
            time.sleep(3)
            incorrect = self.Check_User_Pass()
            if "שם משתמש או סיסמא אינם נכונים" in incorrect:
                print("incorrect username and password")
            else:    
                print("  Login Successful !!")
                self.user_login = True
        except:
            print("  Login Failed !!\n")
            time.sleep(3)

    def logout(self):
        self.user_login = False
        self.browser.find_element(By.ID, 'ucTalmudHeader_ucLogOut_lnkLogOut').click(); time.sleep(3)
        self.browser.find_element(By.ID, 'ucTalmudHeader_ucLogOut_btnOk').click(); time.sleep(3)
        print('Logged out user(%s) successfully!\n' %self.username)
        time.sleep(3)

    def get_page(self):
        if self.user_login:
            self.page_no += 1

            # print(" \npage before:", self.page_no)
            # if self.page_no > 27:
            #     print("marked as last page!..................")
            #     return False
            # if self.page_no > 17:
            #     self.page_no = 27
            # elif self.page_no > 1:
            #     self.page_no = 17

            # print(" page after:", self.page_no)

            try:
                print("\n\t = = = = = = = = = = [PAGE-NO: ", self.page_no, "] = = = = = = = = = =")
                self.page = self.browser.find_element(By.ID, f'ucTalmudSideBar_tvTalmudt{self.page_no}')
                self.page.click()
                return True
            except:
                print('No more pages!')
            return False

    
    def Check_User_Pass(self):
        try:
            msg = WebDriverWait(self.browser,10).until(EC.presence_of_element_located((By.ID,'ucMessagePopUp_lblMessage'))).text
                                
            if msg:
                if msg in 'שם משתמש או סיסמא אינם נכונים':
                    WebDriverWait(self.browser,20).until(EC.element_to_be_clickable((By.ID,'ucMessagePopUp_spanBtnOk'))).click()
        except:
            msg = ""
        return msg          

    def parse_institution_details(self):
        print("\t\t[Institution details]")
        institution_name = self.browser.find_element(By.ID, ELEMENT_ID_INITIAL+'_lblInsName').text
        no_of_students_studying = self.browser.find_element(By.ID, ELEMENT_ID_INITIAL+'_lblInsTotalStudents').text
        no_of_students_supported = self.browser.find_element(By.ID, ELEMENT_ID_INITIAL+'_lblTotalStudent').text
        quota_students_per_institution = self.browser.find_element(By.ID, ELEMENT_ID_INITIAL+'_lblStudentsQuota').text
        total_heads_per_sitting_name = self.browser.find_element(By.ID, ELEMENT_ID_INITIAL+'_txtInsManagerName').get_attribute('value')
        ins_support_mode_status = self.browser.find_element(By.ID, 'ContentPlaceHolder1_tabInstituteDetails_InsDetails1_ucInstitutesDetails_lblInsStatus').text

        # if ins_support_mode_status != STATUS_MODE:
        #     print("\t\tins_support_mode_status = ", ins_support_mode_status)
        #     print("\t\tEnding the page with this status!")
        #     self.ins_support_mode_status_for_page[self.page_no] = ins_support_mode_status
        #     self.institution_details[self.page_no] = [ins_support_mode_status, institution_name]
        #     return

        self.institution_details[self.page_no] = [
            ins_support_mode_status, institution_name, no_of_students_studying, no_of_students_supported, quota_students_per_institution, total_heads_per_sitting_name
        ]

    def parse_address_details(self):
        if self.ins_support_mode_status_for_page.get(self.page_no):
            self.address_details[self.page_no] = [""]
            return

        try:
            if self.institution_details[self.page_no][0] == 'לא מאושר לדיווח':
                return
        except KeyError:
            return

        print("\t\t[StudyUrl/Address]")
        df = utils.get_table_df(self.browser.page_source, ELEMENT_ID_INITIAL+'_gvInsAddress')
        # df['מספר בית'] = df['מספר בית'].astype(int)
        del df['מיקוד']; del df['תיבת דואר']
        print('address_details :',df.values.tolist())
        self.address_details[self.page_no] = df.values.tolist()[0] if df.values.tolist() else []


    def parse_contact_details(self):
        if self.ins_support_mode_status_for_page.get(self.page_no):
            self.contact_details[self.page_no] = [""]
            return

        try:
            if self.institution_details[self.page_no][0] == 'לא מאושר לדיווח':
                return
        except KeyError:
            return

        print("\t\t[ContactInfo/Phone] ")
        df = utils.get_table_df(self.browser.page_source, ELEMENT_ID_INITIAL+'_gvInsPhone')
        df['מספר טלפון'] = df['קידומת'].astype(int).astype(str) + df['מספר טלפון'].astype(int).astype(str)
        del df['קידומת']
        self.contact_details[self.page_no] = []
        if df.values.tolist():
            self.contact_details[self.page_no] = df.values.tolist()[0]
            if len(df.values.tolist()) > 1:
                self.contact_details[self.page_no] = df.values.tolist()[0] + df.values.tolist()[1]

    def parse_study_type_details(self):
        if self.ins_support_mode_status_for_page.get(self.page_no):
            self.study_type_details[self.page_no] = [""]
            return
        try:
            if self.institution_details[self.page_no][0] == 'לא מאושר לדיווח':
                return
        except KeyError:
            return

        print("\t\t[StudyType details]")
        df = utils.get_table_df(self.browser.page_source, 'ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes_ucStudyTypeSearch_gvStudyType')
        table_page_no = 1
        time.sleep(2)
        WebDriverWait(self.browser,20).until(EC.element_to_be_clickable((By.ID,'__tab_ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes'))).click()
        next_table_page = self.browser.find_element(By.ID, 'ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes_ucStudyTypeSearch_gvStudyTypeGridPager_pager')
        all_a_classes = next_table_page.find_elements(By.CLASS_NAME, 'ButtonCssClass')
        self.browser.implicitly_wait(10)
        for idx, a_class in enumerate(all_a_classes):
            if idx == 2 and a_class.get_attribute('href'):
                try:
                    self.browser.implicitly_wait(10)
                    a_class.click()
                    time.sleep(5)
                    df2 = utils.get_table_df(self.browser.page_source, 'ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes_ucStudyTypeSearch_gvStudyType')
                    df = df.append(df2, ignore_index=True)
                    self.browser.implicitly_wait(10)
                except:
                    self.browser.implicitly_wait(10)
                    continue
        code_value_map = dict(zip(df['קוד סוג לימודים'].astype(int), df['מספר תלמידים נתמכים'].astype(int).astype(str) + ',' + df['מספר תלמידים מדווחים'].astype(int).astype(str)))
        codes = [300, 600, 605, 700, 705, 708, 720, 725, 728, 1000]
        self.study_type_details[self.page_no] = [code_value_map.get(c, "") for c in codes]
        pd.set_option('display.max_columns', None)
        df2 = df[['מספר תלמידים נתמכים', 'קוד סוג לימודים', 'מספר תלמידים מדווחים', 'שעות לימוד שבועיות']].loc[((df['מספר תלמידים נתמכים'] > 0) | (df['מספר תלמידים מדווחים'] > 0))]
        df2 = df2.drop(['מספר תלמידים מדווחים'], axis=1)
        # if df2.empty and self.institution_details[self.page_no][0] != "מאושר לתמיכה - ללא זכאים":
        #     print('Checking data for No of students Reported:')
        #     df2 = df[['קוד סוג לימודים', 'מספר תלמידים מדווחים']].loc[(df['מספר תלמידים מדווחים'] > 0)]
        print('study_hours_page_rows:')
        print("df2.values.tolist():", df2.values.tolist())
        print("df2.index.values.tolist():", df2.index.values.tolist())
        for (value, code, hrs), row in zip(df2.values.tolist(), df2.index.values.tolist()):
            table_row = row%8
            table_page_no = 2 if row >= 8 else 1
            study_hrs_page_row_item = (self.page_no, table_page_no, code, table_row+1, hrs)
            if study_hrs_page_row_item not in self.study_hours_page_rows:
                self.study_hours_page_rows.append(study_hrs_page_row_item)
            print((self.page_no, table_page_no, code, table_row+1), end=",")
        # print("\nself.study_hours_page_rows:", self.study_hours_page_rows)

    def parse_study_hours_details(self):
        if self.ins_support_mode_status_for_page.get(self.page_no):
            self.study_hours_details[self.page_no] = [""]
            return

        print("\t\t[StudyHour details]")
        for page_no, table_page_no, code, tr_no, hrs in self.study_hours_page_rows:
            print("\n=======page_no, table_page_no, tr_no======", page_no, table_page_no, tr_no)
            max_retry = 3
            while max_retry >= 0:
                print("max_retry left:", max_retry)
                try:
                    self.browser.find_element(By.ID, f'ucTalmudSideBar_tvTalmudt{page_no}').click()
                    if hrs == '0:00':
                        print('Study hours Data Not found!, setting up [missing] ')
                        self.study_hours_details[(page_no, int(code))] = ['Missing', 'Missing', 'Missing', 'Missing']
                        print(self.study_hours_details[(page_no, int(code))])
                        break

                    time.sleep(2)
                    
                    self.study_hours_details[(page_no, int(code))] = ['Failed', 'Failed', 'Failed', 'Failed']
                    WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.ID, '__tab_ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes')))
                    WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.ID, '__tab_ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes'))).click()
                    time.sleep(10)

                    if table_page_no > 1:
                        time.sleep(3)
                        WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.ID, 'ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes_ucStudyTypeSearch_gvStudyTypeGridPager_pager')))
                        all_a_classes = self.browser.find_elements(By.CLASS_NAME, 'ButtonCssClass')
                        self.browser.implicitly_wait(10)
                        for idx, a_class in enumerate(all_a_classes):
                            if idx == 10 and a_class.get_attribute('href'):
                                self.browser.implicitly_wait(10)
                                a_class.click()
                                time.sleep(5)
                                break

                    table = WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.ID, 'ContentPlaceHolder1_tabInstituteDetails_InsStudyTypes_ucStudyTypeSearch_gvStudyType')))
                    if table.text:
                        print('Study Type Table Found!')
                        tr = table.find_elements(By.TAG_NAME, "tr")[tr_no]
                        tr.click(); time.sleep(5)
                        self.browser.implicitly_wait(10)
                        WebDriverWait(self.browser, 20).until(EC.element_to_be_clickable((By.ID, 'ContentPlaceHolder1_btnUpdateStudyType'))).click()        
                        table_id = "ContentPlaceHolder1_tabStudyTypeDetails_STDetails_ucStudyTypeDetails_gvSchedule"
                        time.sleep(3)
                        df = utils.get_table_df(self.browser.page_source, table_id)
                        df2 = pd.DataFrame()
                        df2['משעה'], df2['עד שעה'] = df['משעה'], df['עד שעה']
                        data = df2.values.tolist()[0]+df2.values.tolist()[1] if df2.values.tolist()[0]!=df2.values.tolist()[1] else df2.values.tolist()[0]+['', '']
                        print(data)
                        self.study_hours_details[(page_no, int(code))] = data
                        break
                    else:
                        print('Study Type Table NOT Found!, retry again...!')
                        raise Exception
                        
                except Exception as err:
                    print(err)
                    print(traceback.print_exc())

                    print('Failed to load Data for this page!, \n\tRefreshing Page, Trying Again!')
                    time.sleep(10)
                    self.browser.refresh()
                    print('start implecit wait.....')
                    self.browser.implicitly_wait(15)
                    max_retry -= 1


    def push_data_to_drive(self):
        print(f"\t\t[Pushing data to drive for user - {self.username}]")
        data = utils.flattened_data(self)
        GoogleSheetHandler(data=data, sheet_name='All_data').appendsheet_records()


if __name__=='__main__':
    args = len(sys.argv)
    options = Options()

    if args > 1 and sys.argv[1].lower() == '--headless_mode=on':
        print('sys.argv:', sys.argv)
        """ Custom options for browser """ 
        options.headless = True
        browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    else:
        browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    print(" * *  * *  * *  * *  * *  * * START  * *  * *  * *  * *  * * ")
    action = ActionChains(browser)
    users = GoogleSheetHandler(sheet_name='Users').getsheet_records()
    for user in users[1:]:
        username, password = user[0], user[1]
        print("Start scrapping for user: %s" %username)
        scrapper = DataScrapping(browser, username, password)
        scrapper.login_to_site()

        if scrapper.user_login:
            while scrapper.get_page():
                scrapper.parse_institution_details()
                scrapper.parse_address_details()
                scrapper.parse_contact_details()
                scrapper.parse_study_type_details()
            scrapper.parse_study_hours_details()
            scrapper.push_data_to_drive()
            scrapper.logout()

        print("End activity for user!\n\n")
    browser.close()
