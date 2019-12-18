# -*- coding:utf-8 -*-
###################################################
# STDF Reader GUI                                 #
# Version: Beta 0.1                               #
#                                                 #
# Sep. 18, 2019                                   #
# A project forked from Thomas Kaunzinger         #
#                                                 #
# References:                                     #
# PySTDF Library                                  #
# PyQt5                                           #
# numpy                                           #
# matplotlib                                      #
# countrymarmot (cp + cpk)                        #
# PyPDF2                                          #
# ZetCode + sentdex (PyQt tutorials)              #
# My crying soul because there's no documentation #
###################################################

###################################################

#######################
# IMPORTING LIBRARIES #
#######################

import sys
import os
#import fix_qt_import_error
# from PyQt5.QtWidgets import QWidget, QDesktopWidget, QApplication, QToolTip, QPushButton
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pystdf.IO import *
from pystdf.Writers import *

import pystdf.V4 as V4
from pystdf.Importer import STDF2DataFrame

from abc import ABC

import numpy as np
import matplotlib.pyplot as plt
from decimal import Decimal
import decimal
import pandas as pd

from matplotlib.backends.backend_pdf import PdfPages
from PyPDF2 import PdfFileMerger, PdfFileReader

import time

###################################################

########################
# QT GUI FUNCTIONALITY #
########################

# Object oriented programming should be illegal cus i forgot how to be good at it
# These are the functions for the QMainWindow/widget application objects that run the whole interface


class Application(QMainWindow):  # QWidget):

    # Construct me
    def __init__(self):
        super().__init__()

        # Have to read the imported .txt file but I'm not totally sure how
        self.data = None
        self.far_data, self.mir_data, self.sdr_data, self.pmr_data, self.pgr_data, self.pir_data, self.ptr_data, self.prr_data, self.tsr_data, self.hbr_data, self.sbr_data, self.pcr_data, self.mrr_data, self.mpr_data = [
        ], [], [], [], [], [], [], [], [], [], [], [], [], []

        self.number_of_sites = None
        self.list_of_test_numbers = [['', 'ALL DATA']]
        self.list_of_test_numbers_string = []

        exitAct = QAction(QIcon('exit.png'), '&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(qApp.quit)
        aboutAct = QAction(QIcon('about.png'), '&About', self)
        aboutAct.triggered.connect(self.aboutecho)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        helpMenu = menubar.addMenu('&Help')
        fileMenu.addAction(exitAct)
        helpMenu.addAction(aboutAct)

        self.status_text = QLabel()
        self.status_text.setText('Welcome!')

        # Button to parse to .txt
        self.stdf_upload_button = QPushButton('Parse STD/STDF to .txt')
        self.stdf_upload_button.setToolTip(
            'Browse for a file ending in .std or .stdf to create a parsed .txt file')
        self.stdf_upload_button.clicked.connect(self.open_parsing_dialog)

        # Button to parse to .xlsx
        self.stdf_upload_button_xlsx = QPushButton(
            'Parse to .xlsx (not recommended)')
        self.stdf_upload_button_xlsx.setToolTip(
            'Browse for stdf to create .xlsx file. This is slow and unnecessary, but good for seeing parsed structure.')
        self.stdf_upload_button_xlsx.clicked.connect(
            self.open_parsing_dialog_xlsx)

        # Button to upload the .txt file to work with
        self.txt_upload_button = QPushButton('Upload parsed .txt file')
        self.txt_upload_button.setToolTip(
            'Browse for the .txt file containing the parsed STDF data')
        self.txt_upload_button.clicked.connect(self.open_text)

        # Generates a summary of the loaded text
        self.generate_summary_button = QPushButton(
            'Generate summary of all results (Sites Merge)')
        self.generate_summary_button.setToolTip(
            'Generate a results .csv summary for the uploaded parsed .txt')
        self.generate_summary_button.clicked.connect(
            lambda: self.make_csv(True))

        # Generates a summary of the loaded text
        self.generate_summary_button_split = QPushButton(
            'Generate summary of all results (Sites Split)')
        self.generate_summary_button_split.setToolTip(
            'Generate a results .csv summary for the uploaded parsed .txt')
        self.generate_summary_button_split.clicked.connect(
            lambda: self.make_csv(False))

        # Selects a test result for the desired
        self.select_test_menu = QComboBox()
        self.select_test_menu.setToolTip(
            'Select the tests to produce the PDF results for')
        self.select_test_menu.activated[str].connect(self.selection_change)

        # Button to generate the test results for the desired tests from the selected menu
        self.generate_pdf_button = QPushButton(
            'Generate .pdf from selected tests')
        self.generate_pdf_button.setToolTip(
            'Generate a .pdf file with the selected tests from the parsed .txt')
        self.generate_pdf_button.clicked.connect(self.plot_list_of_tests)

        self.limit_toggle = QCheckBox('Plot against failure limits', self)
        self.limit_toggle.setChecked(True)
        self.limit_toggle.stateChanged.connect(self.toggler)
        self.limits_toggled = True

        self.progress_bar = QProgressBar()

        self.WINDOW_SIZE = (700, 230)
        self.file_path = None
        self.text_file_location = self.file_path

        self.setFixedSize(self.WINDOW_SIZE[0], self.WINDOW_SIZE[1])
        self.center()
        self.setWindowTitle('STDF Reader For AP Beta V0.2')

        self.test_text = QLabel()
        self.test_text.setText("test")

        self.selected_tests = []

        self.file_selected = False

        self.all_test = []
        self.all_data = self.all_test

        self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.all_data, all_test=self.all_test,
                                             ptr_data=self.ptr_data, number_of_sites=self.number_of_sites,
                                             selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                             list_of_test_numbers=self.list_of_test_numbers)

        self.threaded_task.notify_progress_bar.connect(self.on_progress)
        self.threaded_task.notify_status_text.connect(self.on_update_text)

        self.threaded_text_parser = TextParseThread()
        self.threaded_text_parser.notify_status_text.connect(
            self.on_update_text)

        self.generate_pdf_button.setEnabled(False)
        self.select_test_menu.setEnabled(False)
        self.generate_summary_button.setEnabled(False)
        self.generate_summary_button_split.setEnabled(False)
        self.limit_toggle.setEnabled(False)

        self.main_window()

    # Main interface method
    def main_window(self):
        #self.setGeometry(300, 300, 300, 200)
        #self.resize(900, 700)
        self.setWindowTitle('STDF Reader For AP Beta V0.2')

        # Layout
        layout = QGridLayout()
        self.setLayout(layout)

        # Adds the widgets together in the grid
        layout.addWidget(self.status_text, 0, 0, 1, 2)
        layout.addWidget(self.stdf_upload_button, 1, 0)
        layout.addWidget(self.stdf_upload_button_xlsx, 1, 1)
        layout.addWidget(self.txt_upload_button, 2, 0, 1, 2)
        layout.addWidget(self.generate_summary_button, 3, 0)  # , 1, 2)
        layout.addWidget(self.generate_summary_button_split, 3, 1)
        layout.addWidget(self.select_test_menu, 4, 0, 1, 2)
        layout.addWidget(self.generate_pdf_button, 5, 0)
        layout.addWidget(self.limit_toggle, 5, 1)
        layout.addWidget(self.progress_bar, 6, 0, 1, 2)

        # 创建一个 QWidget ，并将其布局设置为 layout_grid ：
        widget = QWidget()
        widget.setLayout(layout)
        # 将 widget 设为主窗口的 central widget ：
        self.setCentralWidget(widget)

        # Window settings
        self.show()

    def aboutecho(self):
        QMessageBox.information(
            self, 'About', 'Author：Chao Zhou \n verion Beta 0.1 \n 感谢您的使用！ \n chao.zhou@teradyne-china.com ', QMessageBox.Ok)

    # Centers the window
    def center(self):
        window = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        window.moveCenter(center_point)
        self.move(window.topLeft())

    # Opens and reads a file to parse the data
    def open_parsing_dialog(self):

        # self.threaded_text_parser.start()
        #
        # self.main_window()

        self.status_text.setText('Parsing to .txt, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        if filepath[0] == '':

            self.status_text.setText('Please select a file')
            pass

        else:

            self.status_text.update()
            FileReaders.process_file(filepath[0])
            self.status_text.setText(
                str(filepath[0].split('/')[-1] + '_parsed.txt created!'))

    # Opens and reads a file to parse the data to an xlsx
    def open_parsing_dialog_xlsx(self):

        self.status_text.setText('Parsing to .xlsx, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        if filepath[0] == '':

            self.status_text.setText('Please select a file')
            pass

        else:

            self.status_text.update()
            FileReaders.to_excel(filepath[0])
            self.status_text.setText(
                str(filepath[0].split('/')[-1] + '_excel.xlsx created!'))

    # Checks if the toggle by limits mark is checked or not
    def toggler(self, state):

        if state == Qt.Checked:
            self.limits_toggled = True
        else:
            self.limits_toggled = False

    # Opens and reads a file to parse the data. Much of this is what was done in main() from the text version
    def open_text(self):

        # Change to allow to upload file without restart program
        if True:  # self.file_selected:

            #     self.status_text.setText(
            #         'Parsed .txt file already uploaded. Please restart program to upload another.')

            # else:

            # Only accepts text files
            filterboi = 'Text (*.txt)'
            filepath = QFileDialog.getOpenFileName(
                caption='Open .txt File', filter=filterboi)

            self.file_path = filepath[0]

            # Because you can open it and select nothing smh
            if self.file_path is not '':

                # self.txt_upload_button.setEnabled(False)

                self.progress_bar.setValue(0)

                self.data = open(self.file_path).read().splitlines()

                self.progress_bar.setValue(10)

                for i in range(0, len(self.data)):
                    if self.data[i].startswith("FAR"):
                        self.far_data.append(self.data[i])
                    elif self.data[i].startswith("MIR"):
                        self.mir_data.append(self.data[i])
                    elif self.data[i].startswith("SDR"):
                        self.sdr_data.append(self.data[i])
                    elif self.data[i].startswith("PMR"):
                        self.pmr_data.append(self.data[i])
                    elif self.data[i].startswith("PGR"):
                        self.pgr_data.append(self.data[i])
                    elif self.data[i].startswith("PIR"):
                        self.pir_data.append(self.data[i])
                    # or self.data[i].startswith("MPR"):
                    elif self.data[i].startswith("PTR"):
                        self.ptr_data.append(self.data[i])
                    elif self.data[i].startswith("MPR"):
                        self.mpr_data.append(self.data[i])
                    elif self.data[i].startswith("PRR"):
                        self.prr_data.append(self.data[i])
                    elif self.data[i].startswith("TSR"):
                        self.tsr_data.append(self.data[i])
                    elif self.data[i].startswith("HBR"):
                        self.hbr_data.append(self.data[i])
                    elif self.data[i].startswith("SBR"):
                        self.sbr_data.append(self.data[i])
                    elif self.data[i].startswith("PCR"):
                        self.pcr_data.append(self.data[i])
                    elif self.data[i].startswith("MRR"):
                        self.mrr_data.append(self.data[i])

                    self.progress_bar.setValue(10 + i/len(self.data) * 20)

                sdr_parse = self.sdr_data[0].split("|")
                self.number_of_sites = int(sdr_parse[3])

                self.progress_bar.setValue(35)

                self.list_of_test_numbers = [['', 'ALL DATA']]
                list_of_duplicate_test_numbers = []
                # Gathers a list of the test numbers and the tests ran for each site, avoiding repeats from rerun tests
                for i in range(0, len(self.ptr_data), self.number_of_sites):
                    if [self.ptr_data[i].split("|")[1], self.ptr_data[i].split("|")[7]] in self.list_of_test_numbers:
                        pass
                    else:
                        # Find the duplicate test number item from list
                        for item_to_exam in self.list_of_test_numbers:
                            if self.ptr_data[i].split("|")[1] == item_to_exam[0]:
                                if self.ptr_data[i].split("|")[7] != item_to_exam[1]:
                                    list_of_duplicate_test_numbers.append(
                                        [self.ptr_data[i].split("|")[1], self.ptr_data[i].split("|")[7], item_to_exam[1]])
                                    break

                        self.list_of_test_numbers.append(
                            [self.ptr_data[i].split("|")[1], self.ptr_data[i].split("|")[7]])

                    self.progress_bar.setValue(35 + i/len(self.ptr_data) * 15)
                # Log duplicate test number item from list, if exist
                if len(list_of_duplicate_test_numbers) > 0:
                    log_csv = pd.DataFrame(list_of_duplicate_test_numbers,
                                           columns=['Test Number', 'Test Name', 'Test Name'])
                    try:
                        log_csv.to_csv(path_or_buf=str(
                            self.file_path[:-11].split('/')[-1] + "_duplicate_test_number.csv"))
                    except PermissionError:
                        self.status_text.setText(
                            str("Duplicate test number found! Please close " + "duplicate_test_number.csv file to generate a new one"))

                        # Set buttons to false if upload file fail
                        self.progress_bar.setValue(0)
                        self.generate_pdf_button.setEnabled(False)
                        self.select_test_menu.setEnabled(False)
                        self.generate_summary_button.setEnabled(False)
                        self.generate_summary_button_split.setEnabled(False)
                        self.limit_toggle.setEnabled(False)
                        self.main_window()
                        return

                # Extracts the PTR data for the selected test number
                self.list_of_test_numbers_string = ['ALL DATA']
                for i in range(1, len(self.list_of_test_numbers)):

                    self.list_of_test_numbers_string.append(
                        str(self.list_of_test_numbers[i][0] + ' - ' + self.list_of_test_numbers[i][1]))

                    self.progress_bar.setValue(
                        50 + i / len(self.list_of_test_numbers) * 15)

                all_ptr_test = []

                for i in range(1, len(self.list_of_test_numbers)):

                    all_ptr_test.append(Backend.ptr_extractor(
                        self.number_of_sites, self.ptr_data, self.list_of_test_numbers[i]))

                    self.progress_bar.setValue(
                        65 + i / len(self.list_of_test_numbers) * 25)

                # Gathers each set of data from all runs for each site in all selected tests

                self.all_test = []
                for i in range(len(all_ptr_test)):
                    self.all_test.append(Backend.single_test_data(
                        self.number_of_sites, all_ptr_test[i]))
                    self.progress_bar.setValue(90 + i / len(all_ptr_test) * 9)

                self.all_data = self.all_test

                self.file_selected = True

                self.select_test_menu.addItems(
                    self.list_of_test_numbers_string)

                self.selected_tests = [['', 'ALL DATA']]

                # log parsed document, if duplicate test number exist, show warning !
                if len(list_of_duplicate_test_numbers) > 0:
                    self.status_text.setText(
                        'Parsed .txt uploaded! But Duplicate Test Number Found! Please Check \'duplicate_test_number.csv\'')
                else:
                    self.status_text.setText('Parsed .txt uploaded!')

                self.progress_bar.setValue(100)

                self.generate_pdf_button.setEnabled(True)
                self.select_test_menu.setEnabled(True)
                self.generate_summary_button.setEnabled(True)
                self.generate_summary_button_split.setEnabled(True)
                self.limit_toggle.setEnabled(True)

                self.main_window()

            else:

                self.status_text.setText('Please select a file')

    # Handler for the summary button to generate a csv table results file for a summary of the data
    def make_csv(self, merge_sites):

        # Won't perform action unless there's actually a file
        if self.file_selected:

            self.progress_bar.setValue(0)

            table = self.get_summary_table(self.all_test, self.ptr_data, self.number_of_sites,
                                           self.list_of_test_numbers[1: len(self.list_of_test_numbers)], merge_sites)

            self.progress_bar.setValue(10)

            if merge_sites == True:
                csv_summary_name = str(
                    self.file_path[:-11].split('/')[-1] + "_merge_summary.csv")
            else:
                csv_summary_name = str(
                    self.file_path[:-11].split('/')[-1] + "_split_summary.csv")

            # In case someone has the file open
            try:

                # Names the file appropriately
                if self.file_path.endswith('_parsed.txt'):

                    table.to_csv(path_or_buf=csv_summary_name)
                    self.status_text.setText(
                        str(csv_summary_name + " written successfully!"))

                    self.progress_bar.setValue(100)

                else:

                    table.to_csv(path_or_buf=csv_summary_name)
                    self.status_text.setText(
                        str(csv_summary_name + " written successfully!"))

                    self.progress_bar.setValue(100)

            except PermissionError:

                if self.file_path.endswith('_parsed.txt'):

                    self.status_text.setText(
                        str("Please close " + csv_summary_name + "_summary.csv"))

                    self.progress_bar.setValue(0)

                else:

                    self.status_text.setText(str(
                        "Please close " + csv_summary_name.split('/')[-1] + "_summary.csv"))

                    self.progress_bar.setValue(0)

        else:

            self.status_text.setText('Please select a file')

    # Chooses the tests to be run for the graphical processing
    def selection_change(self, i):

        if i == 'ALL DATA':
            self.selected_tests = [['', 'ALL DATA']]

            self.all_test = self.all_data

        else:
            self.selected_tests = Backend.find_tests_of_number(
                i.split(' - ')[0], self.list_of_test_numbers[1:])

            all_ptr_test = []
            for i in range(0, len(self.selected_tests)):
                all_ptr_test.append(Backend.ptr_extractor(
                    self.number_of_sites, self.ptr_data, self.selected_tests[i]))

            # Gathers each set of data from all runs for each site in all selected tests
            self.all_test = []
            for i in range(len(all_ptr_test)):
                self.all_test.append(Backend.single_test_data(
                    self.number_of_sites, all_ptr_test[i]))

    # Supposedly gets the summary results for all sites in each test (COMPLETELY STOLEN FROM BACKEND LOL)
    def get_summary_table(self, test_list_data, data, num_of_sites, test_list, merge_sites):

        parameters = ['Units', 'Runs', 'Fails', 'Min', 'Mean',
                      'Max', 'Range', 'STD', 'Cp', 'Cpl', 'Cpu', 'Cpk']

        summary_results = []

        for i in range(0, len(test_list_data)):
            # merge all sites data
            all_data_array = np.concatenate(test_list_data[i], axis=0)

            units = Backend.get_units(data, test_list[i], num_of_sites)

            minimum = Backend.get_plot_min(data, test_list[i], num_of_sites)

            maximum = Backend.get_plot_max(data, test_list[i], num_of_sites)

            if merge_sites == True:
                summary_results.append(Backend.site_array(
                    all_data_array, minimum, maximum, units, units))
            else:
                for j in range(0, len(test_list_data[i])):
                    summary_results.append(Backend.site_array(
                        test_list_data[i][j], minimum, maximum, j, units))

            self.progress_bar.setValue(60 + i / len(test_list_data) * 20)

        test_names = []

        for i in range(0, len(test_list)):
            # add for split multi-site
            for j in range(0, len(test_list_data[i])):
                test_names.append(test_list[i][1])
                # if merge sites data, only plot test name
                if merge_sites == True:
                    break

            self.progress_bar.setValue(80 + i / len(test_list) * 10)

        table = pd.DataFrame(
            summary_results, columns=parameters, index=test_names)

        self.progress_bar.setValue(95)

        return table

    # Given a set of data for each test, the full set of ptr data, the number of sites, and the list of names/tests for the
    #   set of data needed, expect each item in this set of data to be plotted in a new figure
    # test_list_data should be an array of arrays of arrays with the same length as test_list, which is an array of tuples
    #   with each tuple representing the test number and name of the test data in that specific trial
    def plot_list_of_tests(self):

        if self.file_selected:

            self.generate_pdf_button.setEnabled(False)
            self.select_test_menu.setEnabled(False)
            self.limit_toggle.setEnabled(False)

            self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.all_data,
                                                 all_test=self.all_test, ptr_data=self.ptr_data,
                                                 number_of_sites=self.number_of_sites,
                                                 selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                                 list_of_test_numbers=self.list_of_test_numbers)

            self.threaded_task.notify_progress_bar.connect(self.on_progress)
            self.threaded_task.notify_status_text.connect(self.on_update_text)

            self.threaded_task.start()
            self.main_window()

            # # Runs through each of the tests in the list and plots it in a new figure
            # self.progress_bar.setValue(0)
            #
            # pp = PdfFileMerger()
            #
            # if self.selected_tests == [['', 'ALL DATA']]:
            #
            #     for i in range(1, len(self.list_of_test_numbers)):
            #
            #         pdfTemp = PdfPages(str(self.file_path + "_results_temp"))
            #
            #         plt.figure(figsize=(11, 8.5))
            #         pdfTemp.savefig(Backend.plot_everything_from_one_test(self.all_data[i - 1], self.ptr_data, self.number_of_sites, self.list_of_test_numbers[i], self.limits_toggled))
            #
            #         pdfTemp.close()
            #
            #         pp.append(PdfFileReader(str(self.file_path + "_results_temp"), "rb"))
            #
            #         self.status_text.setText(str(i) + "/" + str(len(self.list_of_test_numbers[1:])) + " test results completed")
            #
            #         self.progress_bar.setValue((i + 1) / len(self.list_of_test_numbers[1:]) * 90)
            #
            #         plt.close()
            #
            # else:
            #
            #     for i in range(0, len(self.selected_tests)):
            #
            #         pdfTemp = PdfPages(str(self.file_path + "_results_temp"))
            #
            #         plt.figure(figsize=(11, 8.5))
            #         pdfTemp.savefig(Backend.plot_everything_from_one_test(self.all_test[i], self.ptr_data, self.number_of_sites, self.selected_tests[i], self.limits_toggled))
            #
            #         pdfTemp.close()
            #
            #         pp.append(PdfFileReader(str(self.file_path + "_results_temp"), "rb"))
            #
            #         self.status_text.setText(str(i) + "/" + str(len(self.selected_tests)) + " test results completed")
            #
            #         self.progress_bar.setValue((i + 1) / len(self.selected_tests) * 90)
            #
            #         plt.close()
            #
            # os.remove(str(self.file_path + "_results_temp"))
            #
            # # Makes sure that the pdf isn't open and prompts you to close it if it is
            # written = False
            # while not written:
            #     try:
            #         pp.write(str(self.file_path + "_results.pdf"))
            #         self.status_text.setText('PDF written successfully!')
            #         self.progress_bar.setValue(100)
            #         written = True
            #
            #     except PermissionError:
            #         self.status_text.setText(str('Please close ' + str(self.file_path + "_results.pdf") + ' and try again.'))
            #         time.sleep(1)
            #         self.progress_bar.setValue(99)

        else:

            self.status_text.setText('Please select a file')

    def on_progress(self, i):
        self.progress_bar.setValue(i)

    def on_update_text(self, txt):
        self.status_text.setText(txt)


# Attempt to utilize multithreading so the program doesn't feel like it's crashing every time I do literally anything
class PdfWriterThread(QThread):

    notify_progress_bar = pyqtSignal(int)
    notify_status_text = pyqtSignal(str)

    def __init__(self, file_path, all_data, all_test, ptr_data, number_of_sites, selected_tests, limits_toggled, list_of_test_numbers, parent=None):
        QThread.__init__(self, parent)

        self.file_path = file_path
        self.all_data = all_data
        self.all_test = all_test
        self.ptr_data = ptr_data
        self.number_of_sites = number_of_sites
        self.selected_tests = selected_tests
        self.limits_toggled = limits_toggled
        self.list_of_test_numbers = list_of_test_numbers

    def run(self):

        self.notify_progress_bar.emit(0)

        pp = PdfFileMerger()

        if self.selected_tests == [['', 'ALL DATA']]:

            for i in range(1, len(self.list_of_test_numbers)):

                pdfTemp = PdfPages(str(self.file_path + "_results_temp"))

                plt.figure(figsize=(11, 8.5))
                pdfTemp.savefig(Backend.plot_everything_from_one_test(
                    self.all_data[i - 1], self.ptr_data, self.number_of_sites, self.list_of_test_numbers[i], self.limits_toggled))

                pdfTemp.close()

                pp.append(PdfFileReader(
                    str(self.file_path + "_results_temp"), "rb"))

                self.notify_status_text.emit(str(str(
                    i) + "/" + str(len(self.list_of_test_numbers[1:])) + " test results completed"))

                self.notify_progress_bar.emit(
                    int((i + 1) / len(self.list_of_test_numbers[1:]) * 90))

                plt.close()

        else:

            for i in range(0, len(self.selected_tests)):

                pdfTemp = PdfPages(str(self.file_path + "_results_temp"))

                plt.figure(figsize=(11, 8.5))
                pdfTemp.savefig(Backend.plot_everything_from_one_test(
                    self.all_test[i], self.ptr_data, self.number_of_sites, self.selected_tests[i], self.limits_toggled))

                pdfTemp.close()

                pp.append(PdfFileReader(
                    str(self.file_path + "_results_temp"), "rb"))

                self.notify_status_text.emit(
                    str(str(i) + "/" + str(len(self.selected_tests)) + " test results completed"))

                self.notify_progress_bar.emit(
                    int((i + 1) / len(self.selected_tests) * 90))

                plt.close()

        os.remove(str(self.file_path + "_results_temp"))

        # Makes sure that the pdf isn't open and prompts you to close it if it is
        written = False
        while not written:
            try:
                pp.write(str(self.file_path + "_results.pdf"))
                self.notify_status_text.emit('PDF written successfully!')
                del pp
                self.notify_progress_bar.emit(100)
                written = True

            except PermissionError:
                self.notify_status_text.emit(
                    str('Please close ' + str(self.file_path + "_results.pdf") + ' and try again.'))
                time.sleep(1)
                self.notify_progress_bar.emit(99)


class TextParseThread(QThread):

    notify_status_text = pyqtSignal(str)

    def __init__(self, parent=None):

        QThread.__init__(self, parent)

    # Opens and reads a file to parse the data
    def run(self):

        self.notify_status_text.emit('Parsing to .txt, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        if filepath[0] == '':

            self.notify_status_text.emit('Please select a file')
            pass

        else:

            FileReaders.process_file(filepath[0])
            self.notify_status_text.emit(
                str(filepath[0].split('/')[-1] + '_parsed.txt created!'))


###################################################

#####################
# BACKEND FUNCTIONS #
#####################
# FORKED FROM CMD ATE DATA READER


# IMPORTANT DOCUMENTATION I NEED TO FILL OUT TO MAKE SURE PEOPLE KNOW WHAT THE HELL IS GOING ON

# ~~~~~~~~~~ Data definition explanations (in functions) ~~~~~~~~~~ #
# data --> ptr_data                                                 #
#   gathered in main()                                              #
#                                                                   #
# test_tuple --> ['test_number', 'test_name']                       #
#   Structure for associating a test's name with its test number    #
#                                                                   #
# test_list --> List of test_tuple                                  #
#   find_test_of_number() returns this                              #
#   list_of_test_numbers in main() is the complete list of this     #
#                                                                   #
# num_of_sites --> number of testing sites for each test run        #
#   number_of_sites = int(sdr_parse[3]) in main()                   #
#                                                                   #
# test_list_data --> list of sets of site_data                      #
#   (sorted in the same order as corresponding tests in test_list)  #
#                                                                   #
# site_data --> array of float data points number_of_sites long     #
#   raw data for a single corresponding test_tuple                  #
#                                                                   #
# test_list and test_list_data are the same length                  #
#                                                                   #
# minimum, maximum --> floats                                       #
#   lower and upper extremes for a site_data from a corresponding   #
#       test_tuple. These are found in the ptr_data (data), which   #
#       has the values located in one of the columns for the first  #
#       test site in the first data point in a test.                #
#   returned by get_plot_extremes() abstraction                     #
# units --> string                                                  #
#   Gathered virtually identically to minimum and maximum.          #
#       Represents units for plotting and post calculations on      #
#       data sets.                                                  #
#                                                                   #
# ~~~~~~~~~~~~ Parsed text file structure explanation ~~~~~~~~~~~~~ #
# The PySTDF library parses the data really non-intuitively,        #
#   although it can be viewed somewhat more clearly if you use the  #
#   toExcel() function (I recommend doing this for figuring out the #
#   way the file is formatted). Basically, each '|' separates the   #
#   information in columns, and the first column determines the     #
#   "page" you are dealing with. The only ones I found particularly #
#   useful were SDR (for the number of sites) and PTR (where all    #
#   the data is actually contained).                                #
# The way the PTR data is parsed is very non-intuitive still, with  #
#   the data broken into chunks num_of_sites lines long, meaning    #
#   each chunk of num_of_sites lines contain a corresponding        #
#   test_tuple that can be extracted, as well as a data point       #
#   result for each test site. This is then done for every single   #
#   test_tuple combination. After all that is done, the process is  #
#   repeated for every single run of the test, creating a new data  #
#   point for each site in each test tuple for however many numbers #
#   of tests there are.                                             #
# It's very not obvious at first, so I strongly recommend creating  #
#   an excel file first to look at it yourself and reverse-engineer #
#   it like I did if you really want to try and figure out the file #
#   format yourself. I'm sorry the library sucks but I didn't       #
#   design it :/ . Good luck!                                       #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #


# This is horrible design and I'm so sorry, but here's a huge library full of static methods for processing the data
# These were all taken virtually verbatim from the previous program so have mercy on me
class Backend(ABC):

    # Plots the results of everything from one test
    @staticmethod
    def plot_everything_from_one_test(test_data, data, num_of_sites, test_tuple, fail_limit):

        # Find the limits
        low_lim = Backend.get_plot_min(data, test_tuple, num_of_sites)
        hi_lim = Backend.get_plot_max(data, test_tuple, num_of_sites)
        units = Backend.get_units(data, test_tuple, num_of_sites)

        print(test_tuple)

        if low_lim == 'n/a':

            if min(np.concatenate(test_data)) < 0:
                low_lim = min(np.concatenate(test_data, axis=0))

            else:
                low_lim = 0

        if hi_lim == 'n/a' or low_lim > hi_lim:

            hi_lim = max(np.concatenate(test_data, axis=0))

        # Title for everything
        plt.suptitle(
            str("Test: " + test_tuple[0] + " - " + test_tuple[1] + " - Units: " + units))

        # Plots the table of results, showing a max of 16 sites at once, plus all the collective data
        table = Backend.table_of_results(test_data, low_lim, hi_lim, units)
        table = table[0:17]
        plt.subplot(211)
        cell_text = []
        for row in range(len(table)):
            cell_text.append(table.iloc[row])

        plt.table(cellText=cell_text, colLabels=table.columns, loc='center')
        plt.axis('off')

        # Plots the trendline
        plt.subplot(223)
        Backend.plot_full_test_trend(test_data, low_lim, hi_lim, fail_limit)
        plt.xlabel("Trials")
        plt.ylabel(units)
        plt.title("Trendline")
        plt.grid(color='0.9', linestyle='--', linewidth=1)

        # Plots the histogram
        plt.subplot(224)
        Backend.plot_full_test_hist(test_data, low_lim, hi_lim, fail_limit)
        plt.xlabel(units)
        plt.ylabel("Trials")
        plt.title("Histogram")
        plt.grid(color='0.9', linestyle='--', linewidth=1, axis='y')

    # TestNumber (string) + ListOfTests (list of tuples) -> ListOfTests with TestNumber as the 0th index (list of tuples)
    # Takes a string representing a test number and returns any test names associated with that test number
    #   e.g. one test number may be 1234 and might have 40 tests run on it, but it may be 20 tests under
    #   the name "device_test_20kHz" and then another 20 tests under the name "device_test_100kHz", meaning
    #   there were two unique tests run under the same test number.
    @staticmethod
    def find_tests_of_number(test_number, test_list):
        tests_of_number = []
        for i in range(0, len(test_list)):
            if test_list[i][0] == test_number:
                tests_of_number.append(test_list[i])

        return tests_of_number

    # Returns the lower allowed limit of a set of data
    @staticmethod
    def get_plot_min(data, test_tuple, num_of_sites):
        minimum = Backend.get_plot_extremes(data, test_tuple, num_of_sites)[0]
        try:

            smallboi = float(minimum)

        except ValueError:

            smallboi = 'n/a'

        return smallboi

    # Returns the upper allowed limit of a set of data
    @staticmethod
    def get_plot_max(data, test_tuple, num_of_sites):

        maximum = Backend.get_plot_extremes(data, test_tuple, num_of_sites)[1]

        try:

            bigboi = float(maximum)

        except ValueError:

            bigboi = 'n/a'

        return bigboi

    # Returns the units for a set of data
    @staticmethod
    def get_units(data, test_tuple, num_of_sites):
        return Backend.get_plot_extremes(data, test_tuple, num_of_sites)[2]

    # Abstraction of above 3 functions, returns tuple with min and max
    @staticmethod
    def get_plot_extremes(data, test_tuple, num_of_sites):
        minimum_test = 0
        maximum_test = 1
        units = ''
        temp = 0
        not_found = True
        while not_found:
            if data[temp].split("|")[1] == test_tuple[0]:
                minimum_test = (data[temp].split("|")[13])
                maximum_test = (data[temp].split("|")[14])
                units = (data[temp].split("|")[15])
                not_found = False
            temp += num_of_sites
        return [minimum_test, maximum_test, units]

    # Plots the results of all sites from one test
    @staticmethod
    def plot_full_test_trend(test_data, minimum, maximum, fail_limit):

        data_min = min(np.concatenate(test_data, axis=0))
        data_max = max(np.concatenate(test_data, axis=0))

        # in case of (-inf,inf)
        if (minimum == float('-inf')) or (maximum == float('inf')):
            minimum = data_min
            maximum = data_max

        expand = max([abs(minimum), abs(maximum)])

        # Plots each site one at a time
        for i in range(0, len(test_data)):
            Backend.plot_single_site_trend(test_data[i])

        # Plots the minimum and maximum barriers
        if fail_limit:
            if minimum == 'n/a' or minimum == float('-inf'):
                plt.plot(range(0, len(test_data[0])), [
                    0] * len(test_data[0]), color="red", linewidth=3.0)
                plt.plot(range(0, len(test_data[0])), [
                    maximum] * len(test_data[0]), color="red", linewidth=3.0)

            elif maximum == 'n/a' or maximum == float('inf'):
                plt.plot(range(0, len(test_data[0])), [
                    minimum] * len(test_data[0]), color="red", linewidth=3.0)
                plt.plot(range(0, len(test_data[0])), [max(np.concatenate(
                    test_data, axis=0))] * len(test_data[0]), color="red", linewidth=3.0)

            else:
                plt.plot(range(0, len(test_data[0])), [
                    minimum] * len(test_data[0]), color="red", linewidth=3.0)
                plt.plot(range(0, len(test_data[0])), [
                    maximum] * len(test_data[0]), color="red", linewidth=3.0)

        if fail_limit:

            # My feeble attempt to get pretty dynamic limits
            if minimum == maximum:
                plt.ylim(ymin=-0.05)
                # try:
                plt.ylim(ymax=max(maximum + abs(0.05 * expand), 1.05))
                # except ValueError:
                #     # print(type(maximum))
                #     print(max(maximum + abs(0.05 * expand), 1.05))
                #     os.system('pause')
            else:
                # try:
                plt.ylim(ymin=minimum - abs(0.05 * expand))
                # except ValueError:
                #     print(type(minimum))
                #     print(minimum)
                plt.ylim(ymax=maximum + abs(0.05 * expand))
        else:
            if minimum == maximum:
                plt.ylim(ymin=-0.05)
                plt.ylim(ymax=max(maximum + abs(0.05 * expand), 1.05))
            else:
                plt.ylim(ymin=(min(data_min, minimum - abs(0.05 * expand))))
                # try:
                plt.ylim(ymax=(max(data_max, maximum + abs(0.05 * expand))))
                # except BaseException:
                #     print(min(data_min, minimum - abs(0.05 * expand)))
                #     print(max(data_max, maximum + abs(0.05 * expand)))
                #     os.system('pause')

    # Returns the table of the results of all the tests to visualize the data
    @staticmethod
    def table_of_results(test_data, minimum, maximum, units):
        parameters = ['Site', 'Runs', 'Fails', 'Min', 'Mean',
                      'Max', 'Range', 'STD', 'Cp', 'Cpl', 'Cpu', 'Cpk']

        # Clarification
        if 'db' in units.lower():
            parameters[7] = 'STD (%)'

        all_data = np.concatenate(test_data, axis=0)

        test_results = [Backend.site_array(
            all_data, minimum, maximum, 'ALL', units)]

        for i in range(0, len(test_data)):
            test_results.append(Backend.site_array(
                test_data[i], minimum, maximum, i, units))

        table = pd.DataFrame(test_results, columns=parameters)

        return table

    # Returns an array a site's final test results
    @staticmethod
    def site_array(site_data, minimum, maximum, site_number, units):
        if minimum == 'n/a' and maximum == 'n/a':
            minimum = 0
            maximum = 0

        if (minimum == float('-inf')) or (maximum == float('inf')):
            minimum = 0
            maximum = 0
        # Big boi initialization
        site_results = []

        # Not actually volts, it's actually % if it's db technically but who cares
        volt_data = []

        # Pass/fail data is stupid
        if minimum == maximum or min(site_data) == max(site_data):
            mean_result = np.mean(site_data)
            std_string = str(np.std(site_data))
            cp_result = 'n/a'
            cpl_result = 'n/a'
            cpu_result = 'n/a'
            cpk_result = 'n/a'

        # The struggles of logarithmic data
        elif 'db' in units.lower():

            for i in range(0, len(site_data)):
                volt_data.append(Backend.db2v(site_data[i]))

            mean_result = Backend.v2db(np.mean(volt_data))
            standard_deviation = np.std(
                volt_data) * 100  # *100 for converting to %
            std_string = str('%.3E' % (Decimal(standard_deviation)))

            cp_result = str(Decimal(Backend.cp(volt_data, Backend.db2v(
                minimum), Backend.db2v(maximum))).quantize(Decimal('0.001')))
            cpl_result = str(Decimal(Backend.cpl(
                volt_data, Backend.db2v(minimum))).quantize(Decimal('0.001')))
            cpu_result = str(Decimal(Backend.cpu(
                volt_data, Backend.db2v(maximum))).quantize(Decimal('0.001')))
            cpk_result = str(Decimal(Backend.cpk(volt_data, Backend.db2v(
                minimum), Backend.db2v(maximum))).quantize(Decimal('0.001')))

        # Yummy linear data instead
        else:
            mean_result = np.mean(site_data)
            # try:
            std_string = str(
                Decimal(np.std(site_data)).quantize(Decimal('0.001')))
            cp_result = str(
                Decimal(Backend.cp(site_data, minimum, maximum)).quantize(Decimal('0.001')))
            cpl_result = str(
                Decimal(Backend.cpu(site_data, minimum)).quantize(Decimal('0.001')))
            cpu_result = str(
                Decimal(Backend.cpl(site_data, maximum)).quantize(Decimal('0.001')))
            cpk_result = str(
                Decimal(Backend.cpk(site_data, minimum, maximum)).quantize(Decimal('0.001')))
            # except decimal.InvalidOperation:
            #     print(type(minimum))
            #     print(minimum)
            #     print(maximum)
            #     os.system("pause")
            # raise UnexpectedSymbol(minimum, maximum)

        # Appending all the important results weow!
        site_results.append(str(site_number))
        site_results.append(str(len(site_data)))
        site_results.append(
            str(Backend.calculate_fails(site_data, minimum, maximum)))
        site_results.append(
            str(Decimal(min(site_data)).quantize(Decimal('0.001'))))
        site_results.append(
            str(Decimal(mean_result).quantize(Decimal('0.001'))))
        site_results.append(
            str(Decimal(max(site_data)).quantize(Decimal('0.001'))))
        site_results.append(
            str(Decimal(max(site_data) - min(site_data)).quantize(Decimal('0.001'))))
        site_results.append(std_string)
        site_results.append(cp_result)
        site_results.append(cpl_result)
        site_results.append(cpu_result)
        site_results.append(cpk_result)

        return site_results

    # Converts to decibels
    @staticmethod
    def v2db(v):
        return 20 * np.log10(abs(v))

    # Converts from decibels
    @staticmethod
    def db2v(db):
        return 10 ** (db / 20)

    # Counts the number of fails in a data set
    @staticmethod
    def calculate_fails(site_data, minimum, maximum):
        fails_count = 0
        if minimum != 'n/a' or maximum != 'n/a':
            # Increase a fails counter for every data point that exceeds an extreme
            for i in range(0, len(site_data)):
                if site_data[i] > float(maximum) or site_data[i] < float(minimum):
                    fails_count += 1

        return fails_count

    # Plots the historgram results of all sites from one test
    @staticmethod
    def plot_full_test_hist(test_data, minimum, maximum, fail_limit):

        # in case of n/a or inf
        if minimum == 'n/a' or minimum == float('-inf'):

            new_minimum = min(min(np.concatenate(test_data, axis=0)), 0)

        else:

            new_minimum = min(min(np.concatenate(test_data, axis=0)), minimum)

        if maximum == 'n/a' or maximum == float('inf'):

            new_maximum = max(np.concatenate(test_data, axis=0))

        else:

            new_maximum = max(max(np.concatenate(test_data, axis=0)), maximum)

        if (minimum == float('-inf')) or (maximum == float('inf')):
            minimum = 0
            maximum = 0

        # Plots each site one at a time
        for i in range(0, len(test_data)):
            Backend.plot_single_site_hist(
                test_data[i], new_minimum, new_maximum, test_data)

        if fail_limit == False:

            # My feeble attempt to get pretty dynamic limits
            if minimum == maximum:
                plt.xlim(xmin=-0.05)
                plt.xlim(xmax=1.05)

            elif minimum == 'n/a':
                expand = abs(maximum)
                plt.xlim(xmin=-0.05)
                plt.xlim(xmax=maximum + abs(0.05 * expand))

            elif maximum == 'n/a':
                expand = max(
                    [abs(minimum), abs(max(np.concatenate(test_data, axis=0)))])
                plt.xlim(xmin=minimum - abs(0.05 * expand))
                plt.xlim(xmax=max(np.concatenate(
                    test_data, axis=0)) + abs(0.05 * expand))

            else:
                expand = max([abs(minimum), abs(maximum)])
                plt.xlim(xmin=minimum - abs(0.05 * expand))
                plt.xlim(xmax=maximum + abs(0.05 * expand))

        else:

            if minimum == maximum:
                plt.axvline(x=0, linestyle="--")
                plt.axvline(x=1, linestyle="--")
                plt.xlim(xmin=-0.05)
                plt.xlim(xmax=1.05)

            elif minimum == 'n/a':
                expand = max(abs(maximum))
                plt.axvline(x=maximum, linestyle="--")
                plt.xlim(xmin=new_minimum - abs(0.05 * expand))
                plt.xlim(xmax=new_maximum + abs(0.05 * expand))

            elif maximum == 'n/a':
                expand = abs(minimum)
                plt.axvline(x=minimum, linestyle="--")
                plt.xlim(xmin=new_minimum - abs(0.05 * expand))
                plt.xlim(xmax=new_maximum + abs(0.05 * expand))

            else:
                expand = max([abs(minimum), abs(maximum)])
                plt.axvline(x=minimum, linestyle="--")
                plt.axvline(x=maximum, linestyle="--")
                plt.xlim(xmin=new_minimum - abs(0.05 * expand))
                plt.xlim(xmax=new_maximum + abs(0.05 * expand))

        plt.ylim(ymin=0)
        plt.ylim(ymax=len(test_data[0]))

    # Plots a single site's results
    @staticmethod
    def plot_single_site_trend(site_data):
        plt.plot(range(0, len(site_data)), site_data)

    # Plots a single site's results as a histogram
    @staticmethod
    def plot_single_site_hist(site_data, minimum, maximum, test_data):

        # if (minimum == float('-inf')) or (maximum == float('inf')):
        #     minimum = 0
        #     maximum = 0

        # At the moment the bins are the same as they are in the previous program's results. Will add fail bin later.

        # Damn pass/fail data exceptions everywhere
        if minimum == maximum:
            binboi = np.linspace(minimum-1, maximum + 1, 21)

        elif minimum > maximum:
            binboi = np.linspace(minimum, max(
                np.concatenate(test_data, axis=0)), 21)

        elif minimum == 'n/a':
            binboi = np.linspace(0, maximum, 21)

        elif maximum == 'n/a':
            binboi = np.linspace(minimum, max(
                np.concatenate(test_data, axis=0)), 21)

        else:
            binboi = np.linspace(minimum, maximum, 21)
        # try:
        plt.hist(site_data, bins=binboi, edgecolor='white', linewidth=0.5)
        # except ValueError:
        #     print(binboi)
        #     print(type(minimum))
        #     print(minimum)
        # np.clip(site_data, binboi[0], binboi[-1])

    # Creates an array of arrays that has the raw data for each test site in one particular test
    # Given the integer number of sites under test and the Array result from ptr_extractor for a certain test num + name,
    #   expect a 2D array with each row being the reran test results for each of the sites in a particular test
    @staticmethod
    def single_test_data(num_of_sites, extracted_ptr):

        # Me being bad at initializing arrays again, hush
        single_test = []

        # Runs through once for each of the sites in the test, incrementing by 1
        for i in range(0, num_of_sites):

            single_site = []

            # Runs through once for each of the loops of the test, incrementing by the number of test sites until all test
            # loops are covered for the individual testing site. The incremented i offsets it so that it moves on to the
            # next testing site
            for j in range(i, len(extracted_ptr), num_of_sites):
                single_site.append(float(extracted_ptr[j][6]))

            single_test.append(single_site)

        return single_test

    # Integer (Number_of_sites), Parsed List of Strings (ptr_data specifically), tuple ([test_number, test_name])
    #   Returns -> array with just the relevant test data parsed along '|'
    # It grabs the data for a certain test in the PTR data and turns that specific test into an array of arrays
    @staticmethod
    def ptr_extractor(num_of_sites, data, test_number):

        # Initializes an array of the data from one of the tests for all test sites
        ptr_array_test = []

        # Finds where in the data to start looking for the test in question
        starting_index = 0
        for i in range(0, len(data), num_of_sites):
            if (data[i].split("|")[1] == test_number[0]) and (data[i].split("|")[7] == test_number[1]):
                starting_index = i
                for j in range(starting_index, (starting_index + num_of_sites)):
                    ptr_array_test.append(data[j].split("|"))

        # Returns the array weow!
        return ptr_array_test

    # For the four following functions, site_data is a list of raw floating point data, minimum is the lower limit and
    # maximum is the upper limit

    # CP AND CPK FUNCTIONS
    # Credit to: countrymarmot on github gist:  https://gist.github.com/countrymarmot/8413981
    @staticmethod
    def cp(site_data, minimum, maximum):
        if minimum == 'n/a' or maximum == 'n/a':
            return 'n/a'
        else:
            sigma = np.std(site_data)
            cp_value = float(maximum - minimum) / (6 * sigma)
            return cp_value

    @staticmethod
    def cpk(site_data, minimum, maximum):
        if minimum == 'n/a' or maximum == 'n/a':
            return 'n/a'
        else:
            sigma = np.std(site_data)
            m = np.mean(site_data)
            cpu_value = float(maximum - m) / (3 * sigma)
            cpl_value = float(m - minimum) / (3 * sigma)
            cpk_value = np.min([cpu_value, cpl_value])
            return cpk_value

    # One sided calculations (cpl/cpu)
    @staticmethod
    def cpl(site_data, minimum):
        if minimum == 'n/a':
            return 'n/a'
        else:
            sigma = np.std(site_data)
            m = np.mean(site_data)
            cpl_value = float(m - minimum) / (3 * sigma)
            return cpl_value

    @staticmethod
    def cpu(site_data, maximum):
        if maximum == 'n/a':
            return 'n/a'
        else:
            sigma = np.std(site_data)
            m = np.mean(site_data)
            cpu_value = float(maximum - m) / (3 * sigma)
            return cpu_value


###################################################

############################
# FILE READING AND PARSING #
############################

# We're living that object oriented life now
# Here's where I put my functions for reading files
class FileReaders(ABC):

    # processing that big boi
    @staticmethod
    def process_file(filename):

        # Open that bad boi up
        f = open(filename, 'rb')
        reopen_fn = None

        # The name of the new file, preserving the directory of the previous
        newFile = filename + "_parsed.txt"

        # I guess I'm making a parsing object here, but again I didn't write this part
        p = Parser(inp=f, reopen_fn=reopen_fn)

        # Writing to a text file instead of vomiting it to the console
        with open(newFile, 'w') as fout:
            # fout writes it to the opened text file
            p.addSink(TextWriter(stream=fout))
            p.parse()

        # We don't need to keep that file open
        f.close()

    # Parses that big boi but this time in Excel format (slow, don't use unless you wish to look at how it's organized)
    @staticmethod
    def to_excel(filename):
        # Converts the stdf to a data frame... somehow
        # (i do not ever intend on looking how he managed to parse this gross file format)
        tables = STDF2DataFrame(filename)

        # The name of the new file, preserving the directory of the previous
        fname = filename + "_excel.xlsx"

        # Writing object to work with excel documents
        writer = pd.ExcelWriter(fname, engine='xlsxwriter')

        # Not mine and I don't really know what's going on here, but it works, so I won't question him.
        # It actually write the data frame as an excel document
        for k, v in tables.items():
            # Make sure the order of columns complies the specs
            record = [r for r in V4.records if r.__class__.__name__.upper() == k]
            if len(record) == 0:
                print("Ignore exporting table %s: No such record type exists." % k)
            else:
                columns = [field[0] for field in record[0].fieldMap]
                if len(record[0].fieldMap) > 0:
                    # try:
                    v.to_excel(writer, sheet_name=k, columns=columns,
                               index=False, na_rep="N/A")
                # except BaseException:
                #     os.system('pause')

        writer.save()


# Execute me
if __name__ == '__main__':
    app = QApplication(sys.argv)

    nice = Application()

    sys.exit(app.exec_())
