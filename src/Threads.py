# -*- coding:utf-8 -*-
# why not use "import matplotlib.pyplot as plt" simply?
# Below import statements can avoid "RuntimeError: main thread is not in main loop" in threading
import os
import time
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PyPDF2 import PdfFileMerger, PdfFileReader
from src.Backend import Backend
from src.FileRead import FileReaders


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
                    self.selected_tests[i].split(' - '), self.limits_toggled, True))
                # plt.figure(figsize=(11, 8.5))
                pdfTemp.savefig(Backend.plot_everything_from_one_test(
                    all_data_array, self.sdr_parse, self.test_info_list, self.number_of_sites,
                    self.selected_tests[i].split(' - '), self.limits_toggled, False))

                pdfTemp.close()

                pp.append(PdfFileReader(str(self.file_path + "_results_temp")))

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

        if len(self.filepath[0]) == 0:

            self.notify_status_text.emit('Please select a file')
            pass

        else:
            if len(self.filepath[0]) == 1:
                output_file_name = self.filepath[0][0]
            else:
                t = time.localtime()
                current_time = str(time.strftime("%Y%m%d%H%M%S", t))
                output_file_name = os.path.dirname(self.filepath[0][0]) + '/output_data_summary'  # + current_time
            FileReaders.to_csv(self.filepath[0], output_file_name)
            self.notify_status_text.emit(
                str(output_file_name.split('/')[-1] + '_csv_log.csv created!'))


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
