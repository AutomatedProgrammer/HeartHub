import os
import sys
import queue
import threading
import tkinter as tk
import customtkinter as ctk
import datetime
import calendar

from CPRLifelineAutomation import CPRLifelineAutomation
from config import DRY_RUN, UPLOAD
import StudentApproveScript

class StudentForm(ctk.CTkToplevel):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.geometry("525x500")
        self.resizable(False, False)
        self.title("Add Student")

        ctk.CTkLabel(self, text="First Name", anchor="w").place(x=39, y=40)
        ctk.CTkLabel(self, text="Last Name", anchor="w").place(x=279, y=40)
        self.fname = ctk.CTkEntry(self, width=200, height=30)
        self.fname.place(x=39, y=70)
        self.lname = ctk.CTkEntry(self, width=200, height=30)
        self.lname.place(x=279, y=70)

        ctk.CTkLabel(self, text="Email Address", anchor="w").place(x=39, y=160)
        ctk.CTkLabel(self, text="Phone Number", anchor="w").place(x=279, y=160)
        self.email = ctk.CTkEntry(self, width=200, height=30)
        self.email.place(x=39, y=190)
        self.phone = ctk.CTkEntry(self, width=200, height=30)
        self.phone.place(x=279, y=190)

        ctk.CTkLabel(self, text="Course", anchor="w").place(x=39, y=280)
        ctk.CTkLabel(self, text="Course Date", anchor="w").place(x=279, y=280)
        self.course = ctk.CTkEntry(self, width=200, height=30)
        self.course.place(x=39, y=310)
        self.date = ctk.CTkEntry(self, width=200, height=30)
        self.date.place(x=279, y=310)

        ctk.CTkLabel(self, text="Course Location", anchor="w").place(x=39, y=390)
        self.location = ctk.CTkEntry(self, width=200, height=30)
        self.location.place(x=39, y=420)
        ctk.CTkButton(self, text="Submit", width=140, height=70, command=self.submit).place(x=300, y=400)

    def submit(self):
        student = [self.fname.get(), self.lname.get(), self.email.get(), self.phone.get(), self.course.get(), self.date.get(), self.location.get()]
        self.callback(student)
        self.destroy() 

class DateForm(ctk.CTkToplevel):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback
        self.geometry("525x500")
        self.resizable(False, False)
        self.title("Select Date")

        current_year = datetime.datetime.now().year
        years = [str(year) for year in range(current_year - 10, current_year + 11)] 
        months = list(calendar.month_name)[1:]
        days = [f"{day:01d}" for day in range(1, 32)]

        ctk.CTkLabel(self, text="Start Year", anchor="w").place(x=39, y=40)
        ctk.CTkLabel(self, text="End Year", anchor="w").place(x=279, y=40)

        self.syear = ctk.CTkOptionMenu(self, values=years, width=200, height=30)
        self.syear.place(x=39, y=70)
        self.eyear = ctk.CTkOptionMenu(self, values=years, width=200, height=30)
        self.eyear.place(x=279, y=70)

        ctk.CTkLabel(self, text="Start Month", anchor="w").place(x=39, y=160)
        ctk.CTkLabel(self, text="End Month", anchor="w").place(x=279, y=160)
        
        self.smonth = ctk.CTkOptionMenu(self, values=months, width=200, height=30)
        self.smonth.place(x=39, y=190)
        self.emonth = ctk.CTkOptionMenu(self, values=months, width=200, height=30)
        self.emonth.place(x=279, y=190)

        ctk.CTkLabel(self, text="Start Day", anchor="w").place(x=39, y=280)
        ctk.CTkLabel(self, text="End Day", anchor="w").place(x=279, y=280)
        
        self.sday = ctk.CTkOptionMenu(self, values=days, width=200, height=30)
        self.sday.place(x=39, y=310)
        self.eday = ctk.CTkOptionMenu(self, values=days, width=200, height=30)
        self.eday.place(x=279, y=310)

        ctk.CTkButton(self, text="Submit", width=140, height=70, command=self.submit).place(x=185, y=390)

        self.syear.set(str(current_year))
        self.eyear.set(str(current_year))
        self.smonth.set("January")
        self.emonth.set("January")
        self.sday.set("1")
        self.eday.set("31")

    def submit(self):
        date = [self.syear.get(), self.smonth.get(), self.sday.get(), 
                self.eyear.get(), self.emonth.get(), self.eday.get()]
        self.destroy()
        self.callback(date)


class TextboxHandler:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue

    def write(self, text):
        self.msg_queue.put(text)

    def flush(self):
        pass

class CPRLifelineGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.app = CPRLifelineAutomation()
        self.msg_queue = queue.Queue()

        self.title("CSC 131 AHA Automation")
        self.geometry("839x547")
        self.resizable(False, False)
        
        self.update_idletasks()
        self.geometry("+0+0")
        
        ctk.set_appearance_mode("Dark") 
        ctk.set_default_color_theme("dark-blue")

        self.setup_ui()
        self.setup_output()

    def setup_ui(self):
        self.console_text = ctk.CTkTextbox(self, width=763, height=354, fg_color="#1d1e1e")
        self.console_text.place(x=39, y=103)
        self.console_text.configure(state="disabled")

        ctk.CTkButton(self, text="Run AHA Script", width=121, height=40, command=self.run_aha_script).place(x=40, y=40)
        ctk.CTkButton(self, text="Add Student", width=121, height=40, command=self.add_student).place(x=200, y=40)
        ctk.CTkButton(self, text="Display Dashboard", width=121, height=40, command=self.display_dashboard).place(x=360, y=40)
        ctk.CTkButton(self, text="Set Auto Run", width=121, height=40, command=self.auto_run).place(x=520, y=40)
        ctk.CTkButton(self, text="Export CSVs", width=121, height=40, command=self.export_all_csvs).place(x=680, y=40)
        ctk.CTkButton(self, text="Export AHA", width=121, height=40, command=self.export_aha).place(x=40, y=479)
        ctk.CTkButton(self, text="Export RQI", width=121, height=40, command=self.export_rqi).place(x=200, y=479)
        ctk.CTkButton(self, text="Export Prepod", width=121, height=40, command=self.export_prepod).place(x=360, y=479)
        ctk.CTkButton(self, text="Dry Run", width=121, height=40, command=self.dry_run).place(x=520, y=479)
        ctk.CTkButton(self, text="Full Cycle", width=121, height=40, command=self.full_cycle).place(x=680, y=479)

    def setup_output(self):
        sys.stdout = TextboxHandler(self.msg_queue)
        self.after(100, self.process_queue)

    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self.console_text.configure(state="normal")
                self.console_text.insert("end", msg)
                self.console_text.see("end")
                self.console_text.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def add_student(self):
        def add_thread(student):
            threading.Thread(target=lambda: self.app.tracker.add_student(*student), daemon=True).start()
        form = StudentForm(callback=add_thread)

    def run_aha_script(self):
        def run_script(dates):
            StudentApproveScript.main(dates[0], dates[1], dates[2], dates[3], dates[4], dates[5])
        form = DateForm(callback=run_script)

    def display_dashboard(self): 
        threading.Thread(target=self.app.tracker.print_dashboard, daemon=True).start()
    def export_aha(self): 
        threading.Thread(target=self.app.tracker.export_aha_csv, daemon=True).start()
    def export_rqi(self): 
        threading.Thread(target=self.app.tracker.export_rqi_csv, daemon=True).start()
    def export_prepod(self): 
        threading.Thread(target=self.app.tracker.export_prepod_csv, daemon=True).start()
    
    def export_all_csvs(self):
        def csvs():
            self.app.tracker.export_aha_csv()
            self.app.tracker.export_rqi_csv()
            self.app.tracker.export_prepod_csv()
        threading.Thread(target=csvs, daemon=True).start()

    def dry_run(self): 
        threading.Thread(target=self.app.run_full_cycle, kwargs={'dry_run': True, 'upload': False}, daemon=True).start()

    def full_cycle(self):
        threading.Thread(target=self.app.run_full_cycle, kwargs={'dry_run': False, 'upload': True}, daemon=True).start()

    def auto_run(self):
        val = ctk.CTkInputDialog(text=f"Enter minutes:", title="Auto Run").get_input()
        if val is None or not val.isdigit(): 
            return
        threading.Thread(target=self.app.run_monitor, kwargs={'interval_minutes' : int(val), 'upload': UPLOAD, 'dry_run' : DRY_RUN}, daemon=True).start()

app = CPRLifelineGUI()
app.mainloop()