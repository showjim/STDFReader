# -*- coding:utf-8 -*-
import pandas as pd
from abc import ABC
import time

from pystdf.IO import Parser
import pystdf.V4 as V4
from pystdf.Writers import *
from pystdf.Importer import STDF2DataFrame

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
    def to_csv(file_names, output_file_name):
        data_summary_all = pd.DataFrame()
        for filename in file_names:
            # Open std file/s
            f = open(filename, 'rb')
            reopen_fn = None

            # I guess I'm making a parsing object here, but again I didn't write this part
            p = Parser(inp=f, reopen_fn=reopen_fn)

            fname = filename  # + "_csv_log.csv"
            startt = time.time()  # 9.7s --> TextWriter; 7.15s --> MyTestResultProfiler

            # Writing to a text file instead of vomiting it to the console
            data_summary = MyTestResultProfiler(filename=fname)
            p.addSink(data_summary)
            p.parse()

            endt = time.time()
            print('STDF处理时间：', endt - startt)
            # data_summary_all = data_summary_all.append(data_summary.frame)
            # data_summary_all = pd.concat([data_summary_all,data_summary.frame],sort=False,join='outer')
            if data_summary_all.empty:
                data_summary_all = data_summary.frame
            else:
                data_summary_all = pd.merge(data_summary_all, data_summary.frame, sort=False, how='outer')
                # data_summary_all = pd.concat([data_summary_all, data_summary.frame], sort=False, join='outer', ignore_index=True)
        # Set multiple level columns for csv table
        tname_list = []
        tnumber_list = []
        hilimit_list = []
        lolimit_list = []
        unit_vect_nam_list = []
        tmplist = data_summary_all.columns.values.tolist()
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
        data_summary_all.columns = [tname_list, hilimit_list, lolimit_list, unit_vect_nam_list, tnumber_list]

        data_summary_all.to_csv(output_file_name + "_csv_log.csv", index=False)

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

        self.file_nam = self.filename.split('/')[-1]
        self.tester_nam = ''
        self.start_t = ''
        self.pgm_nam = ''
        self.lot_id = ''
        self.wafer_id = ''
        self.job_nam = ''

        self.tname_tnumber_dict = {}
        self.sbin_description = {}
        self.DIE_ID = []
        self.lastrectype = None

        self.all_test_result_pd = pd.DataFrame()
        self.frame = pd.DataFrame()

    def after_begin(self, dataSource):
        self.reset_flag = False
        self.total = 0
        self.count = 0
        self.site_count = 0
        self.site_array = []
        self.test_result_dict = {'FILE_NAM': [], 'TESTER_NAM': [], 'START_T': [], 'PGM_NAM': [],
                                 'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [],
                                 'X_COORD': [], 'Y_COORD': [], 'PART_ID': [], 'RC': [],
                                 'HARD_BIN': [], 'SOFT_BIN': [], 'BIN_DESC': [], 'TEST_T': []}

        self.all_test_result_pd = pd.DataFrame()
        self.frame = pd.DataFrame()

        self.file_nam = self.filename.split('/')[-1]
        self.tester_nam = ''
        self.start_t = ''
        self.pgm_nam = ''
        self.lot_id = ''
        self.wafer_id = ''
        self.job_nam = ''

        self.tname_tnumber_dict = {}
        self.sbin_description = {}
        self.DIE_ID = []
        self.lastrectype = None

    def after_send(self, dataSource, data):
        rectype, fields = data
        # First, get lot/wafer ID etc.
        if rectype == V4.mir:
            self.tester_nam = str(fields[V4.mir.NODE_NAM])
            start_t = time.localtime(int(fields[V4.mir.START_T]))
            self.start_t = str(time.strftime("%Y/%m/%d-%H:%M:%S", start_t))
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
                self.test_result_dict = {'FILE_NAM': [], 'TESTER_NAM': [], 'START_T': [], 'PGM_NAM': [],
                                         'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [],
                                         'X_COORD': [], 'Y_COORD': [], 'PART_ID': [], 'RC': [],
                                         'HARD_BIN': [], 'SOFT_BIN': [], 'BIN_DESC': [], 'TEST_T': []}

            self.site_count += 1
            self.site_array.append(fields[V4.pir.SITE_NUM])
            self.test_result_dict['SITE_NUM'] = self.site_array
        if rectype == V4.bps:
            self.pgm_nam = str(fields[V4.bps.SEQ_NAME])
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
            tname_tnumber = str(fields[V4.ftr.TEST_NUM]) + '|' + fields[V4.ftr.TEST_TXT] + '|-1|-1|' + \
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
                    die_id = self.pgm_nam + '-' + self.job_nam + '-' + self.lot_id + '-' + str(
                        self.wafer_id) + '-' + str(die_x) + '-' + str(die_y)
                    if (part_flg & 0x1) ^ (part_flg & 0x2) == 1 or (die_id in self.DIE_ID):
                        rc = 'Retest'
                    else:
                        rc = 'First'
                    self.DIE_ID.append(die_id)

                    self.test_result_dict['FILE_NAM'].append(self.file_nam)
                    self.test_result_dict['TESTER_NAM'].append(self.tester_nam)
                    self.test_result_dict['START_T'].append(self.start_t)
                    self.test_result_dict['PGM_NAM'].append(self.pgm_nam)

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
                self.all_test_result_pd = self.all_test_result_pd.append(tmp_pd, sort=False, ignore_index=True)
        if rectype == V4.sbr:
            sbin_num = fields[V4.sbr.SBIN_NUM]
            sbin_nam = fields[V4.sbr.SBIN_NAM]
            self.sbin_description[sbin_num] = str(sbin_nam) # str(sbin_num) + ' - ' + str(sbin_nam)

        self.lastrectype = rectype

    def after_complete(self, dataSource):
        start_t = time.time()
        # self.generate_bin_summary()
        # self.generate_wafer_map()
        self.generate_data_summary()
        end_t = time.time()
        print('CSV生成时间：', end_t - start_t)

    def generate_data_summary(self):
        if not self.all_test_result_pd.empty:

            self.frame = self.all_test_result_pd
            self.frame.BIN_DESC = self.frame.SOFT_BIN.replace(self.sbin_description)
            # Edit multi-level header
            # frame.set_index(['JOB_NAM', 'LOT_ID', 'WAFER_ID', 'SITE_NUM', 'X_COORD',
            #                              'Y_COORD', 'PART_ID', 'HARD_BIN', 'SOFT_BIN', 'TEST_T'])

            # tname_list = []
            # tnumber_list = []
            # hilimit_list = []
            # lolimit_list = []
            # unit_vect_nam_list = []
            # tmplist = self.frame.columns.values.tolist()
            # for i in range(len(tmplist)):
            #     if len(str(tmplist[i]).split('|')) == 1:
            #         tname_list.append('')
            #         tnumber_list.append(str(tmplist[i]).split('|')[0])
            #         hilimit_list.append('')
            #         lolimit_list.append('')
            #         unit_vect_nam_list.append('')
            #     else:
            #         tname_list.append(str(tmplist[i]).split('|')[1])
            #         tnumber_list.append(str(tmplist[i]).split('|')[0])
            #         hilimit_list.append(str(tmplist[i]).split('|')[2])
            #         lolimit_list.append(str(tmplist[i]).split('|')[3])
            #         unit_vect_nam_list.append(str(tmplist[i]).split('|')[4])
            # self.frame.columns = [tname_list, hilimit_list, lolimit_list, unit_vect_nam_list, tnumber_list]
            # mcol = pd.MultiIndex.from_arrays([tname_list, tnumber_list])
            # frame.Mu
            # new_frame = pd.DataFrame(frame.iloc[:,:], columns=mcol)
            # frame.to_csv(self.outputname + "_csv_log.csv")
            # f = open(self.outputname + '_csv_log.csv', 'a')
            # self.frame.to_csv(f)
            # f.close()
        else:
            print("No test result samples found :(")


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
