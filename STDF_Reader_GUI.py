# -*- coding:utf-8 -*-
###################################################
# STDF Reader GUI                                 #
# Version: Beta 0.3                               #
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
# import fix_qt_import_error
# from PyQt5.QtWidgets import QWidget, QDesktopWidget, QApplication, QToolTip, QPushButton
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pystdf.IO import Parser
from pystdf.Writers import *

import pystdf.V4 as V4
from pystdf.Importer import STDF2DataFrame

from abc import ABC

import numpy as np

# why not use "import matplotlib.pyplot as plt" simply? 
# Below import statements can avoid "RuntimeError: main thread is not in main loop" in threading
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from decimal import Decimal
import pandas as pd

from matplotlib.backends.backend_pdf import PdfPages
from PyPDF2 import PdfFileMerger, PdfFileReader

import time
import xlsxwriter
import logging

# from numba import jit

Version = 'Beta 0.3.9'


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
        self.number_of_sites = None
        self.list_of_test_numbers = [['', 'ALL DATA']]
        self.list_of_test_numbers_string = []
        self.tnumber_list = []
        self.tname_list = []

        self.test_info_list = []
        self.df_csv = pd.DataFrame()
        self.sdr_parse = []

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
        self.stdf_upload_button_xlsx = QPushButton('Parse STD/STDF to .xlsx table (very slow)')
        self.stdf_upload_button_xlsx.setToolTip(
            'Browse for a file ending in .std to create a parsed .xlsx file')
        self.stdf_upload_button_xlsx.clicked.connect(self.open_parsing_dialog_xlsx)

        # Button to parse to .csv
        self.stdf_upload_button = QPushButton(
            'Parse STD/STDF to .csv log')
        self.stdf_upload_button.setToolTip(
            'Browse for stdf to create .csv file. This is helpful when doing data analysis')
        self.stdf_upload_button.clicked.connect(
            self.open_parsing_dialog_csv)

        # Button to upload the .txt file to work with
        self.txt_upload_button = QPushButton('Upload parsed .csv file')
        self.txt_upload_button.setToolTip(
            'Browse for the .csv file containing the parsed STDF data')
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
        self.select_test_menu = ComboCheckBox()  # ComboCheckBox() # QComboBox()
        self.select_test_menu.setToolTip(
            'Select the tests to produce the PDF results for')

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
        self.setWindowTitle('STDF Reader For AP ' + Version)

        self.test_text = QLabel()
        self.test_text.setText("test")

        self.selected_tests = []

        self.file_selected = False

        self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.df_csv,
                                             ptr_data=self.test_info_list, number_of_sites=self.number_of_sites,
                                             selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                             list_of_test_numbers=self.list_of_test_numbers, site_list=self.sdr_parse)

        self.threaded_task.notify_progress_bar.connect(self.on_progress)
        self.threaded_task.notify_status_text.connect(self.on_update_text)

        self.threaded_csv_parser = CsvParseThread(file_path=self.file_path)
        self.threaded_csv_parser.notify_status_text.connect(
            self.on_update_text)

        self.threaded_xlsx_parser = XlsxParseThread(file_path=self.file_path)
        self.threaded_xlsx_parser.notify_status_text.connect(
            self.on_update_text)

        self.generate_pdf_button.setEnabled(False)
        self.select_test_menu.setEnabled(False)
        self.generate_summary_button.setEnabled(False)
        self.generate_summary_button_split.setEnabled(False)
        self.limit_toggle.setEnabled(False)

        self.main_window()

    # Main interface method
    def main_window(self):
        # self.setGeometry(300, 300, 300, 200)
        # self.resize(900, 700)
        self.setWindowTitle('STDF Reader For AP ' + Version)

        # Layout
        layout = QGridLayout()
        self.setLayout(layout)

        # Adds the widgets together in the grid
        layout.addWidget(self.status_text, 0, 0, 1, 2)
        layout.addWidget(self.stdf_upload_button_xlsx, 1, 0)
        layout.addWidget(self.stdf_upload_button, 1, 1)
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
            self, 'About', 'Author：Chao Zhou \n verion ' + Version + ' \n 感谢您的使用！ \n zhouchao486@gmail.com ',
            QMessageBox.Ok)

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

    # Opens and reads a file to parse the data to an csv
    def open_parsing_dialog_csv(self):
        # I can not figure out the process when parse STDF, so...
        self.progress_bar.setMinimum(0)

        # Move QFileDialog out of QThread, in case of error under win 7
        self.status_text.setText('Parsing to .csv file, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        self.status_text.update()
        self.stdf_upload_button.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.threaded_csv_parser = CsvParseThread(filepath[0])
        self.threaded_csv_parser.notify_status_text.connect(self.on_update_text)
        self.threaded_csv_parser.finished.connect(self.set_progress_bar_max)
        self.threaded_csv_parser.start()
        self.stdf_upload_button.setEnabled(True)
        self.main_window()

    # Opens and reads a file to parse the data to an xlsx
    def open_parsing_dialog_xlsx(self):

        self.progress_bar.setMinimum(0)

        self.status_text.setText('Parsing to .xlsx file, please wait...')
        filterboi = 'STDF (*.stdf *.std)'
        filepath = QFileDialog.getOpenFileName(
            caption='Open STDF File', filter=filterboi)

        self.status_text.update()
        self.stdf_upload_button_xlsx.setEnabled(False)
        self.progress_bar.setMaximum(0)
        self.threaded_xlsx_parser = XlsxParseThread(filepath[0])
        self.threaded_xlsx_parser.notify_status_text.connect(self.on_update_text)
        self.threaded_xlsx_parser.finished.connect(self.set_progress_bar_max)
        self.threaded_xlsx_parser.start()
        self.stdf_upload_button_xlsx.setEnabled(True)
        self.main_window()

    def set_progress_bar_max(self):
        self.progress_bar.setMaximum(100)

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
            # Only accepts text files
            filterboi = 'CSV Table (*.csv)'
            filepath = QFileDialog.getOpenFileName(
                caption='Open .csv File', filter=filterboi)

            self.file_path = filepath[0]

            # Because you can open it and select nothing smh
            if self.file_path != '':

                # self.txt_upload_button.setEnabled(False)

                self.progress_bar.setValue(0)
                self.list_of_test_numbers = []
                list_of_duplicate_test_numbers = []
                startt = time.time()

                if self.file_path.endswith(".txt"):
                    pass
                elif self.file_path.endswith(".std"):
                    pass
                elif self.file_path.endswith(".csv"):
                    self.df_csv = pd.read_csv(self.file_path, header=[0, 1, 2, 3, 4])  # , dtype=str)
                    # self.df_csv.replace(r'\(F\)','',regex=True, inplace=True)
                    # self.df_csv.iloc[:,12:] = self.df_csv.iloc[:,12:].astype('float')

                    # Extracts the test name for the selecting
                    tmp_pd = self.df_csv.columns
                    self.single_columns = tmp_pd.get_level_values(4).values.tolist()[:12]  # Get the part info
                    self.tnumber_list = tmp_pd.get_level_values(4).values.tolist()[12:]
                    self.tname_list = tmp_pd.get_level_values(0).values.tolist()[12:]
                    self.test_info_list = tmp_pd.values.tolist()[12:]
                    self.list_of_test_numbers_string = [j + ' - ' + i for i, j in
                                                        zip(self.tname_list, self.tnumber_list)]
                    # Change the multi-level columns to single level columns
                    self.single_columns = self.single_columns + self.list_of_test_numbers_string
                    self.df_csv.columns = self.single_columns

                    # Data cleaning, get rid of '(F)'
                    self.df_csv.replace(r'\(F\)', '', regex=True, inplace=True)
                    self.df_csv.iloc[:, 12:] = self.df_csv.iloc[:, 12:].astype('float')

                    # Extract the test name and test number list
                    self.list_of_test_numbers = [list(z) for z in (zip(self.tnumber_list, self.tname_list))]

                    # Get site array
                    self.sdr_parse = self.df_csv.iloc[:, 4].unique()
                    self.number_of_sites = len(self.sdr_parse)

                    # Check the duplicate test number
                    test_number_list = self.tnumber_list
                    test_name_list = self.tname_list
                    if len(test_number_list) != len(set(test_number_list)):
                        for i in range(len(test_number_list)):
                            dup_list = self.list_duplicates_of(test_number_list[i:], test_number_list[i], i)
                            if len(dup_list) > 1:
                                list_of_duplicate_test_numbers.append(
                                    [test_number_list[dup_list[0]], test_name_list[i], test_name_list[dup_list[1]]])
                    # Log duplicate test number item from list, if exist
                    if len(list_of_duplicate_test_numbers) > 0:
                        log_csv = pd.DataFrame(list_of_duplicate_test_numbers,
                                               columns=['Test Number', 'Test Name', 'Test Name'])
                        try:
                            log_csv.to_csv(path_or_buf=str(
                                self.file_path[:-11].split('/')[-1] + "_duplicate_test_number.csv"))
                        except PermissionError:
                            self.status_text.setText(
                                str(
                                    "Duplicate test number found! Please close " + "duplicate_test_number.csv file to "
                                                                                   "generate a new one"))

                endt = time.time()
                print('读取时间：', endt - startt)
                # sdr_parse = self.sdr_data[0].split("|")

                self.progress_bar.setValue(35)

                self.file_selected = True

                self.select_test_menu.loadItems(
                    self.list_of_test_numbers_string)

                self.selected_tests = []

                # log parsed document, if duplicate test number exist, show warning !
                if len(list_of_duplicate_test_numbers) > 0:
                    self.status_text.setText(
                        'Parsed .csv uploaded! But Duplicate Test Number Found! Please Check \'duplicate_test_number.csv\'')
                else:
                    self.status_text.setText('Parsed .csv uploaded!')

                self.progress_bar.setValue(100)

                self.generate_pdf_button.setEnabled(True)
                self.select_test_menu.setEnabled(True)
                self.generate_summary_button.setEnabled(True)
                self.generate_summary_button_split.setEnabled(True)
                self.limit_toggle.setEnabled(True)

                self.main_window()

            else:

                self.status_text.setText('Please select a file')

    def list_duplicates_of(self, seq, item, start_index):  # start_index is to reduce the complex
        start_at = -1
        locs = []
        while True:
            try:
                loc = seq.index(item, start_at + 1)
            except ValueError:
                break
            else:
                locs.append(start_index + loc)
                start_at = loc
                # Just find the first duplicate to reduce complex
                if len(locs) == 2:
                    break
        return locs

    # Handler for the summary button to generate a csv table results file for a summary of the data
    def make_csv(self, merge_sites):

        # Won't perform action unless there's actually a file
        if self.file_selected:

            self.progress_bar.setValue(0)

            table = self.get_summary_table(self.df_csv, self.test_info_list, self.number_of_sites,
                                           self.list_of_test_numbers[1: len(self.list_of_test_numbers)], merge_sites)

            self.progress_bar.setValue(90)

            if merge_sites == True:
                csv_summary_name = str(
                    self.file_path[:-11] + "_merge_summary.csv")
            else:
                csv_summary_name = str(
                    self.file_path[:-11] + "_split_summary.csv")

            # In case someone has the file open
            try:
                table.to_csv(path_or_buf=csv_summary_name)
                self.status_text.setText(
                    str(csv_summary_name + " written successfully!"))
                self.progress_bar.setValue(100)
            except PermissionError:
                self.status_text.setText(
                    str("Please close " + csv_summary_name + "_summary.csv"))
                self.progress_bar.setValue(0)
        else:
            self.status_text.setText('Please select a file')

    # Supposedly gets the summary results for all sites in each test (COMPLETELY STOLEN FROM BACKEND LOL)
    def get_summary_table(self, all_test_data, test_info_list, num_of_sites, test_list, merge_sites):

        parameters = ['Units', 'Runs', 'Fails', 'Min', 'Mean',
                      'Max', 'Range', 'STD', 'Cp', 'Cpl', 'Cpu', 'Cpk']

        summary_results = []

        df_csv = all_test_data

        sdr_parse = self.sdr_parse
        startt = time.time()

        # Extract test data per site for later usage, to improve time performance
        if not merge_sites:
            parameters[0] = 'Site'
            site_test_data_dic = {}
            for j in sdr_parse:
                site_test_data_dic[str(j)] = df_csv[df_csv.SITE_NUM == j]

        for i in range(0, len(test_list)):
            # merge all sites data
            all_data_array = df_csv.iloc[:, i + 12].to_numpy()
            ## Get rid of all no-string value to NaN, and replace to None
            # all_data_array = pd.to_numeric(df_csv.iloc[:, i + 12], errors='coerce').to_numpy()
            all_data_array = all_data_array[~np.isnan(all_data_array)]

            ## Get rid of (F) and conver to float on series
            # all_data_array = df_csv.iloc[:, i + 12].str.replace(r'\(F\)', '').astype(float).to_numpy()

            units = Backend.get_units(test_info_list, test_list[i], num_of_sites)

            minimum = Backend.get_plot_min(test_info_list, test_list[i], num_of_sites)

            maximum = Backend.get_plot_max(test_info_list, test_list[i], num_of_sites)

            if merge_sites:
                summary_results.append(Backend.site_array(
                    all_data_array, minimum, maximum, units, units))
            else:
                for j in sdr_parse:
                    site_test_data_df = site_test_data_dic[str(j)]
                    site_test_data = site_test_data_df.iloc[:, i + 12].to_numpy()

                    ## Get rid of (F) and conver to float on series
                    # site_test_data = pd.to_numeric(site_test_data_df.iloc[:, i + 12], errors='coerce').to_numpy()
                    # Series.dropna() can remove NaN, but slower than numpy.isnan
                    site_test_data = site_test_data[~np.isnan(site_test_data)]
                    summary_results.append(Backend.site_array(
                        site_test_data, minimum, maximum, j, units))

            self.progress_bar.setValue(20 + i / len(test_list) * 60)
        endt = time.time()
        print('Site Data Analysis Time: ', endt - startt)
        test_names = []

        for i in range(0, len(test_list)):
            # add for split multi-site
            for j in range(0, len(sdr_parse)):
                test_names.append(test_list[i][1])
                # if merge sites data, only plot test name
                if merge_sites:
                    break

            self.progress_bar.setValue(80 + i / len(test_list) * 10)

        table = pd.DataFrame(
            summary_results, columns=parameters, index=test_names)

        self.progress_bar.setValue(95)

        return table

    # Given a set of data for each test, the full set of ptr data, the number of sites, and the list of names/tests for the
    #   set of data needed, expect each item in this set of data to be plotted in a new figure
    # test_info_list should be an array of arrays of arrays with the same length as test_list, which is an array of tuples
    #   with each tuple representing the test number and name of the test data in that specific trial
    def plot_list_of_tests(self):

        if self.file_selected:

            self.generate_pdf_button.setEnabled(False)
            self.select_test_menu.setEnabled(False)
            self.limit_toggle.setEnabled(False)
            self.selected_tests = self.select_test_menu.Selectlist()
            self.threaded_task = PdfWriterThread(file_path=self.file_path, all_data=self.df_csv,
                                                 ptr_data=self.test_info_list,
                                                 number_of_sites=self.number_of_sites,
                                                 selected_tests=self.selected_tests, limits_toggled=self.limits_toggled,
                                                 list_of_test_numbers=self.list_of_test_numbers,
                                                 site_list=self.sdr_parse)

            self.threaded_task.notify_progress_bar.connect(self.on_progress)
            self.threaded_task.notify_status_text.connect(self.on_update_text)
            self.threaded_task.finished.connect(self.restore_menu)
            self.threaded_task.start()

            # self.generate_pdf_button.setEnabled(False)
            # self.select_test_menu.setEnabled(False)
            # self.limit_toggle.setEnabled(False)
            self.main_window()
        else:

            self.status_text.setText('Please select a file')

    def restore_menu(self):
        self.generate_pdf_button.setEnabled(True)
        self.select_test_menu.setEnabled(True)
        self.limit_toggle.setEnabled(True)

    def on_progress(self, i):
        self.progress_bar.setValue(i)

    def on_update_text(self, txt):
        self.status_text.setText(txt)


class ComboCheckBox(QComboBox):
    def loadItems(self, items):
        self.items = items
        self.items.insert(0, 'ALL DATA')
        self.row_num = len(self.items)
        self.Selectedrow_num = 0
        self.qCheckBox = []
        self.qLineEdit = QLineEdit()
        self.qLineEdit.setReadOnly(True)
        self.qListWidget = QListWidget()
        self.addQCheckBox(0)
        self.qCheckBox[0].stateChanged.connect(self.All)
        for i in range(1, self.row_num):
            self.addQCheckBox(i)
            self.qCheckBox[i].stateChanged.connect(self.showMessage)
        self.setModel(self.qListWidget.model())
        self.setView(self.qListWidget)
        self.setLineEdit(self.qLineEdit)
        # self.qLineEdit.textChanged.connect(self.printResults)

    def showPopup(self):
        #  重写showPopup方法，避免下拉框数据多而导致显示不全的问题
        # select_list = self.Selectlist()  # 当前选择数据
        # self.loadItems(items=self.items[1:])  # 重新添加组件
        # for select in select_list:
        #     index = self.items[:].index(select)
        #     self.qCheckBox[index].setChecked(True)  # 选中组件
        return QComboBox.showPopup(self)

    def addQCheckBox(self, i):
        self.qCheckBox.append(QCheckBox())
        qItem = QListWidgetItem(self.qListWidget)
        self.qCheckBox[i].setText(self.items[i])
        self.qListWidget.setItemWidget(qItem, self.qCheckBox[i])

    def Selectlist(self):
        Outputlist = [ch.text() for ch in self.qCheckBox[1:] if ch.isChecked()]
        # for i in range(1, self.row_num):
        #     if self.qCheckBox[i].isChecked():
        #         Outputlist.append(self.qCheckBox[i].text())
        self.Selectedrow_num = len(Outputlist)
        return Outputlist

    def showMessage(self):
        self.qLineEdit.setReadOnly(False)
        self.qLineEdit.clear()
        Outputlist = self.Selectlist()

        if self.Selectedrow_num == 0:
            self.qCheckBox[0].setCheckState(0)  # Clear, nothing is selected
            show = ''
        elif self.Selectedrow_num == self.row_num - 1:
            self.qCheckBox[0].setCheckState(2)  # All are selected
            show = 'ALL DATA'
        else:
            self.qCheckBox[0].setCheckState(1)  # Part is/are selected
            show = ';'.join(Outputlist)
        self.qLineEdit.setText(show)
        self.qLineEdit.setReadOnly(True)

    def All(self, check_state):
        # disconnect 'showMessage' to improve time performance
        for i in range(1, self.row_num):
            self.qCheckBox[i].stateChanged.disconnect()
        if check_state == 2:
            for i in range(1, self.row_num):
                self.qCheckBox[i].setChecked(True)
            self.showMessage()
        elif check_state == 1:
            if self.Selectedrow_num == 0:
                self.qCheckBox[0].setCheckState(2)
        elif check_state == 0:
            self.clear()
            self.showMessage()
        for i in range(1, self.row_num):
            self.qCheckBox[i].stateChanged.connect(self.showMessage)

    def clear(self):
        for i in range(self.row_num):
            self.qCheckBox[i].setChecked(False)


# Attempt to utilize multithreading so the program doesn't feel like it's crashing every time I do literally anything
class PdfWriterThread(QThread):
    notify_progress_bar = pyqtSignal(int)
    notify_status_text = pyqtSignal(str)

    def __init__(self, file_path, all_data, ptr_data, number_of_sites, selected_tests, limits_toggled,
                 list_of_test_numbers, site_list, parent=None):
        QThread.__init__(self, parent)

        self.file_path = file_path
        self.df_csv = all_data
        self.test_info_list = ptr_data
        self.number_of_sites = number_of_sites
        self.selected_tests = selected_tests
        self.limits_toggled = limits_toggled
        self.list_of_test_numbers = list_of_test_numbers
        self.sdr_parse = site_list

    def run(self):
        startt = time.time()
        self.notify_progress_bar.emit(0)

        pp = PdfFileMerger()

        site_test_data_dic = {}
        for j in self.sdr_parse:
            site_test_data_dic[str(j)] = self.df_csv[self.df_csv.SITE_NUM == j]

        # if self.selected_tests == [['', 'ALL DATA']]:
        if len(self.selected_tests) > 0:

            for i in range(len(self.selected_tests)):
                site_test_data_list = []
                for j in self.sdr_parse:
                    site_test_data = site_test_data_dic[str(j)][self.selected_tests[i]].to_numpy()
                    tmp_site_test_data_list = site_test_data[~np.isnan(site_test_data)].tolist()
                    ## Ignore fail value
                    # site_test_data = pd.to_numeric(site_test_data_dic[str(j)].iloc[:, i - 1 + 12],
                    #                                errors='coerce').dropna().values.tolist()
                    site_test_data_list.append(tmp_site_test_data_list)
                all_data_array = site_test_data_list
                pdfTemp = PdfPages(str(self.file_path + "_results_temp"))

                plt.figure(figsize=(11, 8.5))
                pdfTemp.savefig(Backend.plot_everything_from_one_test(
                    all_data_array, self.sdr_parse, self.test_info_list, self.number_of_sites,
                    self.selected_tests[i].split(' - '), self.limits_toggled))

                pdfTemp.close()

                pp.append(PdfFileReader(
                    str(self.file_path + "_results_temp"), "rb"))

                self.notify_status_text.emit(str(str(
                    i) + "/" + str(len(self.selected_tests)) + " test results completed"))

                self.notify_progress_bar.emit(
                    int((i + 1) / len(self.selected_tests) * 90))

                plt.close()

        else:
            self.notify_status_text.emit(
                str("There is no test instance selected!"))
            self.notify_progress_bar.emit(0)
            return

        endt = time.time()
        print('PDF Data Analysis Time: ', endt - startt)
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


class CsvParseThread(QThread):
    notify_status_text = pyqtSignal(str)

    def __init__(self, file_path, parent=None):

        QThread.__init__(self, parent)
        self.filepath = file_path

    # Opens and reads a file to parse the data
    def run(self):

        if self.filepath == '':

            self.notify_status_text.emit('Please select a file')
            pass

        else:

            FileReaders.to_csv(self.filepath)
            self.notify_status_text.emit(
                str(self.filepath.split('/')[-1] + '_csv_log.csv created!'))


class XlsxParseThread(QThread):
    notify_status_text = pyqtSignal(str)

    def __init__(self, file_path, parent=None):

        QThread.__init__(self, parent)
        self.filepath = file_path

    # Opens and reads a file to parse the data
    def run(self):

        if self.filepath == '':

            self.notify_status_text.emit('Please select a file')
            pass

        else:

            FileReaders.to_excel(self.filepath)
            self.notify_status_text.emit(
                str(self.filepath.split('/')[-1] + '_excel.xlsx created!'))


###################################################

#####################
# BACKEND FUNCTIONS #
#####################
# FORKED FROM CMD ATE DATA READER


# IMPORTANT DOCUMENTATION I NEED TO FILL OUT TO MAKE SURE PEOPLE KNOW WHAT THE HELL IS GOING ON

# ~~~~~~~~~~ Data definition explanations (in functions) ~~~~~~~~~~ #
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
# test_info_list --> list of sets of site_data                      #
#   (sorted in the same order as corresponding tests in test_list)  #
#                                                                   #
# site_data --> array of float data points number_of_sites long     #
#   raw data for a single corresponding test_tuple                  #
#                                                                   #
# test_list and test_info_list are the same length                  #
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
    def plot_everything_from_one_test(test_data, sdr_parse, data, num_of_sites, test_tuple, fail_limit):

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
        table = Backend.table_of_results(test_data, sdr_parse, low_lim, hi_lim, units)
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
        plt.xticks(rotation=45)  # Tilted 45 degree angle
        plt.ylabel("Trials")
        plt.title("Histogram")
        plt.grid(color='0.9', linestyle='--', linewidth=1, axis='y')
        plt.legend(loc='best')

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
            # try:
            # if data[temp].split("|")[1] == test_tuple[0]:
            #     minimum_test = (data[temp].split("|")[13])
            #     maximum_test = (data[temp].split("|")[14])
            #     units = (data[temp].split("|")[15])
            #     not_found = False

            if data[temp][4] == test_tuple[0]:
                minimum_test = data[temp][2]
                maximum_test = data[temp][1]
                units = data[temp][3]
                not_found = False
            temp += 1  # num_of_sites
            # except IndexError:
            #     os.system('pause')
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
    def table_of_results(test_data, sdr_parse, minimum, maximum, units):
        parameters = ['Site', 'Runs', 'Fails', 'Min', 'Mean',
                      'Max', 'Range', 'STD', 'Cp', 'Cpl', 'Cpu', 'Cpk']

        # Clarification
        if 'db' in units.lower():
            parameters[7] = 'STD (%)'

        all_data = np.concatenate(test_data, axis=0)

        test_results = [Backend.site_array(
            all_data, minimum, maximum, 'ALL', units)]

        for i in range(0, len(sdr_parse)):
            test_results.append(Backend.site_array(
                test_data[i], minimum, maximum, sdr_parse[i], units))

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

        if (minimum is None) and (maximum is None):
            minimum = 0
            maximum = 0
        # Big boi initialization
        site_results = []

        if len(site_data) == 0:
            return site_results

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
        # try:
        site_results.append(
            str(Decimal(float(min(site_data))).quantize(Decimal('0.000001'))))
        # except TypeError:
        #     os.system('pause')
        site_results.append(
            str(Decimal(mean_result).quantize(Decimal('0.000001'))))
        site_results.append(
            str(Decimal(float(max(site_data))).quantize(Decimal('0.000001'))))
        site_results.append(
            str(Decimal(float(max(site_data) - min(site_data))).quantize(Decimal('0.000001'))))

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
                test_data[i], new_minimum, new_maximum, test_data, i)

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
    def plot_single_site_hist(site_data, minimum, maximum, test_data, site_num):

        # if (minimum == float('-inf')) or (maximum == float('inf')):
        #     minimum = 0
        #     maximum = 0

        # At the moment the bins are the same as they are in the previous program's results. Will add fail bin later.

        # Damn pass/fail data exceptions everywhere
        if minimum == maximum:
            binboi = np.linspace(minimum - 1, maximum + 1, 21)

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
        plt.hist(site_data, bins=binboi, edgecolor='white', linewidth=0.5, label='site ' + str(site_num))
        # except ValueError:
        #     print(binboi)
        #     print(type(minimum))
        #     print(minimum)
        # np.clip(site_data, binboi[0], binboi[-1])

    # Creates an array of arrays that has the raw data for each test site in one particular test
    # expect a 2D array with each row being the reran test results for each of the sites in a particular test
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

        startt = time.time()  # 9.7s --> TextWriter; 7.15s --> MyTestResultProfiler

        # Writing to a text file instead of vomiting it to the console
        with open(newFile, 'w') as fout:
            # fout writes it to the opened text file
            p.addSink(TextWriter(stream=fout))
            p.parse()

        # We don't need to keep that file open
        f.close()

        endt = time.time()
        print('STDF处理时间：', endt - startt)

    # Parses that big boi but this time in Excel format (slow, don't use unless you wish to look at how it's organized)
    @staticmethod
    def to_csv(filename):

        # Open that bad boi up
        f = open(filename, 'rb')
        reopen_fn = None

        # I guess I'm making a parsing object here, but again I didn't write this part
        p = Parser(inp=f, reopen_fn=reopen_fn)

        fname = filename  # + "_csv_log.csv"
        startt = time.time()  # 9.7s --> TextWriter; 7.15s --> MyTestResultProfiler

        # Writing to a text file instead of vomiting it to the console
        p.addSink(MyTestResultProfiler(filename=fname))
        p.parse()

        endt = time.time()
        print('STDF处理时间：', endt - startt)

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


# Get the test time, small case from pystdf
class MyTestTimeProfiler:
    def __init__(self):
        self.total = 0
        self.count = 0

    def after_begin(self):
        self.total = 0
        self.count = 0

    def after_send(self, data):
        rectype, fields = data
        if rectype == V4.prr and fields[V4.prr.TEST_T]:
            self.total += fields[V4.prr.TEST_T]
            self.count += 1

    def after_complete(self):
        if self.count:
            mean = self.total / self.count
            print("Total test time: %f s, avg: %f s" % (self.total / 1000.0, mean))
        else:
            print("No test time samples found :(")


# Get all PTR,PIR,FTR result
class MyTestResultProfiler:
    def __init__(self, filename):
        self.filename = filename
        self.reset_flag = False
        self.total = 0
        self.count = 0
        self.site_count = 0
        self.site_array = []
        self.test_result_dict = {}

        self.lot_id = ''
        self.wafer_id = ''
        self.job_nam = ''

        self.tname_tnumber_dict = {}
        self.sbin_description = {}
        self.DIE_ID = []
        self.lastrectype = None

    def after_begin(self, dataSource):
        self.reset_flag = False
        self.total = 0
        self.count = 0
        self.site_count = 0
        self.site_array = []
        self.test_result_dict = {'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [], 'X_COORD': [],
                                 'Y_COORD': [], 'PART_ID': [], 'RC': [], 'HARD_BIN': [], 'SOFT_BIN': [], 'TEST_T': []}

        self.all_test_result_pd = pd.DataFrame()

        self.lot_id = ''
        self.wafer_id = ''

        self.tname_tnumber_dict = {}
        self.sbin_description = {}
        self.DIE_ID = []
        self.lastrectype = None

    def after_send(self, dataSource, data):
        rectype, fields = data
        # First, get lot/wafer ID etc.
        if rectype == V4.mir:
            self.job_nam = str(fields[V4.mir.JOB_NAM])
            self.lot_id = str(fields[V4.mir.LOT_ID])
        if rectype == V4.wir:
            self.wafer_id = str(fields[V4.wir.WAFER_ID])
            self.DIE_ID = []
        # Then, yummy parametric results
        if rectype == V4.pir:
            # Found BPS and EPS in sample stdf, add 'lastrectype' to overcome it
            if self.reset_flag or self.lastrectype != rectype:
                self.reset_flag = False
                self.site_count = 0
                self.site_array = []
                # self.all_test_result_pd = self.all_test_result_pd.append(pd.DataFrame(self.test_result_dict))
                self.test_result_dict = {'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [], 'X_COORD': [],
                                         'Y_COORD': [], 'PART_ID': [], 'RC': [], 'HARD_BIN': [], 'SOFT_BIN': [],
                                         'TEST_T': []}

            self.site_count += 1
            self.site_array.append(fields[V4.pir.SITE_NUM])
            self.test_result_dict['SITE_NUM'] = self.site_array
        if rectype == V4.ptr:  # and fields[V4.prr.SITE_NUM]:
            tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + fields[V4.ptr.TEST_TXT]
            if not (tname_tnumber in self.tname_tnumber_dict):
                self.tname_tnumber_dict[tname_tnumber] = str(fields[V4.ptr.TEST_NUM]) + '|' + \
                                                         str(fields[V4.ptr.TEST_TXT]) + '|' + \
                                                         str(fields[V4.ptr.HI_LIMIT]) + '|' + \
                                                         str(fields[V4.ptr.LO_LIMIT]) + '|' + \
                                                         str(fields[V4.ptr.UNITS])
            # Be careful here, Hi/Low limit only stored in first PTR
            # tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + fields[V4.ptr.TEST_TXT] + '|' + \
            #                 str(fields[V4.ptr.HI_LIMIT]) + '|' + str(fields[V4.ptr.LO_LIMIT]) + '|' + \
            #                 str(fields[V4.ptr.UNITS])
            current_tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + fields[V4.ptr.TEST_TXT]
            full_tname_tnumber = self.tname_tnumber_dict[current_tname_tnumber]
            if not (full_tname_tnumber in self.test_result_dict):
                self.test_result_dict[full_tname_tnumber] = [None] * self.site_count
            else:
                pass
                # if len(self.test_result_dict[full_tname_tnumber]) >= self.site_count:
                #     # print('Duplicate test number found for test: ', tname_tnumber)
                #     return

            for i in range(self.site_count):
                if fields[V4.ptr.SITE_NUM] == self.test_result_dict['SITE_NUM'][i]:
                    if fields[V4.ptr.TEST_FLG] == 0:
                        ptr_result = str(fields[V4.ptr.RESULT])
                    else:
                        ptr_result = str(fields[V4.ptr.RESULT]) + '(F)'
                    self.test_result_dict[full_tname_tnumber][i] = ptr_result

        # This is the functional test results
        if rectype == V4.ftr:
            tname_tnumber = str(fields[V4.ftr.TEST_NUM]) + '|' + fields[V4.ftr.TEST_TXT] + '|' + '|' + '|' + \
                            fields[V4.ftr.VECT_NAM]
            if not (tname_tnumber in self.test_result_dict):
                self.test_result_dict[tname_tnumber] = [None] * self.site_count
            else:
                pass
                # if len(self.test_result_dict[tname_tnumber]) >= self.site_count:
                #     # print('Duplicate test number found for test: ', tname_tnumber)
                #     return
            for i in range(self.site_count):
                if fields[V4.ftr.SITE_NUM] == self.test_result_dict['SITE_NUM'][i]:
                    if fields[V4.ftr.TEST_FLG] == 0:
                        ftr_result = '-1'
                    else:
                        ftr_result = '0(F)'
                    self.test_result_dict[tname_tnumber][i] = ftr_result

        if rectype == V4.eps:
            self.reset_flag = True
        if rectype == V4.prr:  # and fields[V4.prr.SITE_NUM]:
            for i in range(self.site_count):
                if fields[V4.prr.SITE_NUM] == self.test_result_dict['SITE_NUM'][i]:
                    die_x = fields[V4.prr.X_COORD]
                    die_y = fields[V4.prr.Y_COORD]
                    part_id = fields[V4.prr.PART_ID]
                    part_flg = fields[V4.prr.PART_FLG]
                    h_bin = fields[V4.prr.HARD_BIN]
                    s_bin = fields[V4.prr.SOFT_BIN]
                    test_time = fields[V4.prr.TEST_T]
                    # To judge the device is retested or not
                    die_id = self.job_nam + '-' + self.lot_id + '-' + str(self.wafer_id) + '-' + str(die_x) + '-' + str(
                        die_y)
                    if (part_flg & 0x1) ^ (part_flg & 0x2) == 1 or (die_id in self.DIE_ID):
                        rc = 'Retest'
                    else:
                        rc = 'First'
                    self.DIE_ID.append(die_id)

                    self.test_result_dict['JOB_NAM'].append(self.job_nam)
                    self.test_result_dict['LOT_ID'].append(self.lot_id)
                    self.test_result_dict['WAFER_ID'].append(self.wafer_id)

                    self.test_result_dict['X_COORD'].append(die_x)
                    self.test_result_dict['Y_COORD'].append(die_y)
                    self.test_result_dict['PART_ID'].append(part_id)
                    self.test_result_dict['RC'].append(rc)
                    self.test_result_dict['HARD_BIN'].append(h_bin)
                    self.test_result_dict['SOFT_BIN'].append(s_bin)
                    self.test_result_dict['TEST_T'].append(test_time)

            # Send current part result to all test result pd
            if fields[V4.prr.SITE_NUM] == self.test_result_dict['SITE_NUM'][-1]:
                # tmp_pd = pd.DataFrame(self.test_result_dict)
                tmp_pd = pd.DataFrame.from_dict(self.test_result_dict, orient='index').T
                # tmp_pd.transpose()
                self.all_test_result_pd = self.all_test_result_pd.append(tmp_pd, sort=False)
        if rectype == V4.sbr:
            sbin_num = fields[V4.sbr.SBIN_NUM]
            sbin_nam = fields[V4.sbr.SBIN_NAM]
            self.sbin_description[sbin_num] = str(sbin_num) + ' - ' + str(sbin_nam)

        self.lastrectype = rectype

    def after_complete(self, dataSource):
        start_t = time.time()
        self.generate_bin_summary()
        self.generate_wafer_map()
        self.generate_data_summary()
        end_t = time.time()
        print('CSV生成时间：', end_t - start_t)

    def generate_data_summary(self):
        if not self.all_test_result_pd.empty:

            frame = self.all_test_result_pd
            # Edit multi-level header
            # frame.set_index(['JOB_NAM', 'LOT_ID', 'WAFER_ID', 'SITE_NUM', 'X_COORD',
            #                              'Y_COORD', 'PART_ID', 'HARD_BIN', 'SOFT_BIN', 'TEST_T'])

            tname_list = []
            tnumber_list = []
            hilimit_list = []
            lolimit_list = []
            unit_vect_nam_list = []
            tmplist = frame.columns.values.tolist()
            for i in range(len(tmplist)):
                if len(str(tmplist[i]).split('|')) == 1:
                    tname_list.append('')
                    tnumber_list.append(str(tmplist[i]).split('|')[0])
                    hilimit_list.append('')
                    lolimit_list.append('')
                    unit_vect_nam_list.append('')
                else:
                    tname_list.append(str(tmplist[i]).split('|')[1])
                    tnumber_list.append(str(tmplist[i]).split('|')[0])
                    hilimit_list.append(str(tmplist[i]).split('|')[2])
                    lolimit_list.append(str(tmplist[i]).split('|')[3])
                    unit_vect_nam_list.append(str(tmplist[i]).split('|')[4])
            frame.columns = [tname_list, hilimit_list, lolimit_list, unit_vect_nam_list, tnumber_list]
            # mcol = pd.MultiIndex.from_arrays([tname_list, tnumber_list])
            # frame.Mu
            # new_frame = pd.DataFrame(frame.iloc[:,:], columns=mcol)
            frame.to_csv(self.filename + "_csv_log.csv")
        else:
            print("No test result samples found :(")

    def generate_bin_summary(self):
        all_bin_summary_list = []
        lot_id_list = self.all_test_result_pd['LOT_ID'].unique()
        for lot_id in lot_id_list:
            wafer_id_list = self.all_test_result_pd['WAFER_ID'].unique()
            for wafer_id in wafer_id_list:
                self.single_wafer_df = self.all_test_result_pd[self.all_test_result_pd['LOT_ID'].isin([lot_id]) &
                                                               self.all_test_result_pd['WAFER_ID'].isin([wafer_id])]
                die_id = self.single_wafer_df['LOT_ID'].iloc[0] + ' - ' + self.single_wafer_df['WAFER_ID'].iloc[0]
                retest_die_df = self.single_wafer_df[self.single_wafer_df['RC'].isin(['Retest'])]
                retest_die_np = retest_die_df[['X_COORD', 'Y_COORD']].values
                mask = (self.single_wafer_df.X_COORD.values == retest_die_np[:, None, 0]) & \
                       (self.single_wafer_df.Y_COORD.values == retest_die_np[:, None, 1]) & \
                       (self.single_wafer_df['RC'].isin(['First']).to_numpy())
                self.single_wafer_df = self.single_wafer_df[~mask.any(axis=0)]
                sbin_counts = self.single_wafer_df.pivot_table('PART_ID', index='SOFT_BIN', columns='SITE_NUM',
                                                               aggfunc='count', margins=True, fill_value=0).copy()
                bin_summary_pd = sbin_counts.rename(index=self.sbin_description).copy()
                bin_summary_pd.index.name = die_id
                all_bin_summary_list.append(bin_summary_pd)
        # self.bin_summary_pd.to_csv(self.filename + '_bin_summary.csv')
        f = open(self.filename + '_bin_summary.csv', 'w')
        for temp_df in all_bin_summary_list:
            temp_df.to_csv(f, line_terminator='\n')
            f.write('\n')
        f.close()

    def generate_wafer_map(self):
        # Get wafer map
        all_wafer_map_list = []
        lot_id_list = self.all_test_result_pd['LOT_ID'].unique()
        for lot_id in lot_id_list:
            wafer_id_list = self.all_test_result_pd['WAFER_ID'].unique()
            for wafer_id in wafer_id_list:
                self.single_wafer_df = self.all_test_result_pd[self.all_test_result_pd['LOT_ID'].isin([lot_id]) &
                                                               self.all_test_result_pd['WAFER_ID'].isin([wafer_id])]
                die_id = self.single_wafer_df['LOT_ID'].iloc[0] + ' - ' + self.single_wafer_df['WAFER_ID'].iloc[0]
                wafer_map_df = self.single_wafer_df.pivot_table(values='SOFT_BIN', index='Y_COORD', columns='X_COORD',
                                                                aggfunc=lambda x: int(tuple(x)[-1]))
                wafer_map_df.index.name = die_id
                # Sort Y from low to high
                wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
                all_wafer_map_list.append(wafer_map_df)
        # wafer_map_df.to_csv(self.filename + '_wafer_map.csv')
        # pd.concat(all_wafer_map_list).to_csv(self.filename + '_wafer_map.csv')
        f = open(self.filename + '_wafer_map.csv', 'w')
        for temp_df in all_wafer_map_list:
            temp_df.to_csv(f, line_terminator='\n')
            f.write('\n')
        f.close()


# Get STR, PSR data from STDF V4-2007.1
class My_STDF_V4_2007_1_Profiler:
    def __init__(self):
        self.is_V4_2007_1 = False
        self.pmr_dict = {}
        self.pat_nam_dict = {}
        self.mod_nam_dict = {}
        self.str_cyc_ofst_dict = {}
        self.str_fail_pin_dict = {}
        self.str_exp_data_dict = {}
        self.str_cap_data_dict = {}

    def after_begin(self):
        self.reset_flag = False
        self.is_V4_2007_1 = False
        self.pmr_dict = {}
        self.pat_nam_dict = {}
        self.mod_nam_dict = {}
        self.str_cyc_ofst_dict = {}
        self.str_fail_pin_dict = {}
        self.str_exp_data_dict = {}
        self.str_cap_data_dict = {}

    def after_send(self, data):
        rectype, fields = data
        if rectype == V4.vur and fields[V4.vur.UPD_NAM] == 'Scan:2007.1':
            self.is_V4_2007_1 = True
        if rectype == V4.pmr:
            self.pmr_dict[str(fields[V4.pmr.PMR_INDX])] = str(fields[V4.pmr.LOG_NAM])
        if rectype == V4.psr:
            psr_nam = str(fields[V4.psr.PSR_NAM])
            self.pat_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam.split(':')[0]
            self.mod_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam.split(':')[1]
        if rectype == V4.str:
            self.str_cyc_ofst_dict[str(fields[V4.psr.PSR_REF])] = fields[V4.str.CYC_OFST]
            self.str_fail_pin_dict[str(fields[V4.psr.PSR_REF])] = fields[V4.str.PMR_INDX]
            self.str_exp_data_dict[str(fields[V4.psr.PSR_REF])] = fields[V4.str.EXP_DATA]
            self.str_cap_data_dict[str(fields[V4.psr.PSR_REF])] = fields[V4.str.CAP_DATA]
        if rectype == V4.eps:
            pass
        if rectype == V4.prr:
            pass

    def after_complete(self):
        if self.count:
            mean = self.total / self.count
            print("Total test time: %f s, avg: %f s" % (self.total / 1000.0, mean))
        else:
            print("No test time samples found :(")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.exit(0)

# Execute me
if __name__ == '__main__':
    # initialize the log settings
    if getattr(sys, 'frozen', False):
        pathname = os.path.dirname(sys.executable)
    else:
        pathname = os.path.dirname(__file__)
    logging.basicConfig(filename=pathname+'\\app.log', level=logging.ERROR,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    sys.excepthook = handle_exception
    app = QApplication(sys.argv)
    nice = Application()
    sys.exit(app.exec_())
