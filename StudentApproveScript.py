from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.relative_locator import locate_with
from selenium import webdriver
from datetime import datetime
import time
import json
import os
from config import AHA_EMAIL, AHA_PASSWORD, DELAY

no_courses = False

def select_date(driver, year, month, day):
    current_year_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".calendar_year__single-value")))
    
    if current_year_element.text != year:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(By.CSS_SELECTOR, ".calendar_year__control")).click()
        time.sleep(1)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'calendar_year__option') and text()='{year}']"))).click()

    current_month_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".calendar_month__single-value")))
    
    if current_month_element.text != month:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".calendar_month__control"))).click()
        
        time.sleep(1)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'calendar_month__option') and text()='{month}']"))).click()
    
    time.sleep(1)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(@class, 'react-datepicker__day') " f"and not(contains(@class, 'react-datepicker__day--outside-month'))] " f"//span[text()='{day}']"))).click()

def main(year1, month1, day1, year2, month2, day2):
    courses = []
    emails = []
    names = []
    dates = []
    driver = webdriver.Chrome()
    try:
        driver.get("https://atlas.heart.org/")
        driver.maximize_window()

        #Click sign in
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='button']"))).click()

        #Input email
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "Email"))).send_keys(AHA_EMAIL)

        #Input password
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "Password"))).send_keys(AHA_PASSWORD) 

        #Put in credentials
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()

        time.sleep(DELAY)
        driver.get("https://atlas.heart.org/organisation/class-listing?applyTsFilter=true")
        time.sleep(DELAY)

        #Select Sac state as both instructor and course org
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "css-19bb58m"))).click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Sac State')]"))).click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "icon_down_dir"))).click()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//li[contains(., '26027755195 / Sac State')]"))).click()

        #Set the date
        time.sleep(DELAY)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//i[@class='customReactCalendarPicker_calendarIcon__w9gD9 aha-icon-calendar']"))).click()
        time.sleep(DELAY)
        select_date(driver, year1, month1, day1)
        time.sleep(DELAY)
        select_date(driver, year2, month2, day2)

        try:
            #Student selections
            student_count = len(WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located(((By.XPATH, "//i[@class='aha-icon-meat-balls']")))))
        except:
            print("No courses found, exiting...")
            no_courses = True
            driver.quit()
        #Copy the course and dates listed
        course_list = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located(((By.CSS_SELECTOR, "td[data-title='Course']"))))
        courses = []

        for i in course_list:
            courses.append([i.find_element(By.CSS_SELECTOR, "span[class*='TCtablename']").text, True])

        course_dates = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located(((By.CSS_SELECTOR, "td[data-title='Class Time']"))))
        dates = []
        for i in course_dates:
            dates.append([i.text.split('\n')[0], True])

        emails = []
        names = []
        #Iterates through classes and then accepts each student. Fetches the names and emails from each student
        for i in range(student_count):
            student = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, "//i[@class='aha-icon-meat-balls']")))
            driver.execute_script("window.scrollBy(0, 500);")
            student[i].click()
            time.sleep(DELAY)
            WebDriverWait(driver, 10).until(lambda x : x.find_element(locate_with(By.ID, "kebab-item-0").near(student[i]))).click()

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-testid='acceptbutton']")))
                pending_count = len(WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[data-testid='acceptbutton']"))))
                time.sleep(DELAY)

                for j in range(pending_count):
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Accept']"))).click()
                    time.sleep(DELAY)
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='acceptBtn']"))).click()
                    time.sleep(DELAY)

                driver.execute_script("window.scrollBy(0, 500);")
                fetched_emails = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div[class*='dynamicTable_rtlBorderRight']")))
                fetched_names = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div[class*='dynamicTable_name__viewClass']")))
                
                temp_names = []
                temp_emails = []
                for x in range(len(fetched_emails)):
                    temp_names.append(fetched_names[x].text)
                    temp_emails.append(fetched_emails[x].text)

                names.append(temp_names)
                emails.append(temp_emails)
                
                driver.execute_script("window.scrollBy(0, -500);")
                time.sleep(DELAY)
                driver.back()
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(DELAY)
            
            except:
                print("No accept, moving on...")
                driver.execute_script("window.scrollBy(0, 500);")
                try:
                    fetched_emails = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div[class*='dynamicTable_rtlBorderRight']")))
                    fetched_names = WebDriverWait(driver, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "div[class*='dynamicTable_name__viewClass']")))
                except:
                    fetched_emails = []
                    fetched_names = []
                
                temp_names = []
                temp_emails = []
                if not fetched_emails:
                    courses[i][1] = False
                    dates[i][1] = False
                    driver.back()
                    driver.execute_script("window.scrollTo(0, 0);")
                    continue
                for x in range(len(fetched_emails)):
                    temp_names.append(fetched_names[x].text)
                    temp_emails.append(fetched_emails[x].text)

                names.append(temp_names)
                emails.append(temp_emails)
                time.sleep(DELAY)
                driver.back()
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(DELAY)
                continue

    except Exception as e:
        if not no_courses:
            print(f"Something went wrong: {e}")

    finally:
        #students = []
        PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
        STUDENT_DB_FILE = os.path.join(PROJECT_DIR, "student_records.json")
        if not os.path.exists(STUDENT_DB_FILE):
            students = []
        else:
            r = open(STUDENT_DB_FILE, "r")
            students = json.load(r)
            r.close()
        ex_courses = []
        ex_dates = []

        for i in range(len(courses)):
            if courses[i][1] == True:
                ex_courses.append(courses[i][0])

        for i in range(len(dates)):
            if dates[i][1] == True:
                ex_dates.append(dates[i][0])

        for i in range(len(ex_dates)):
            
            for j in range(len(emails[i])):
                student = {
                "first_name": names[i][j].split()[0],
                "last_name": names[i][j].split()[1],
                "email": emails[i][j],
                "phone": "",
                "course": ex_courses[i],
                "course_date": ex_dates[i],
                "location": "",
                "enrollment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "paid": False,
                "paid_amount": "",
                "welcome_email_sent": False,
                "reminder_email_sent": False,
                "reminder_date": "",
                "rqi_exported": False
                }
                students.append(student)
                print(names[i][j].split()[0])
                print(names[i][j].split()[1])

        f = open(STUDENT_DB_FILE, "w")
        json.dump(students, f, indent=2)
        f.close()
        driver.quit()

#main("2026", "May", "1", "2026", "May", "2")