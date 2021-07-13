# -*- coding:utf-8 -*-
import pandas as pd
from abc import ABC
import time
import gzip
import os

from pystdf.IO import Parser
import pystdf.V4 as V4
from pystdf.Writers import *
from pystdf.Importer import STDF2DataFrame

############################
# FILE READING AND PARSING #
############################

# So sad there is no detaial document about PySTDF, thanks to Thomas's code as sample
class FileReaders(ABC):

    # This function is to parse STDF into an ATDF like log, abandon this part now
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
    def to_csv(file_names, output_file_name, notify_progress_bar):
        data_summary_all = pd.DataFrame()
        for filename in file_names:
            # Open std file/s
            if filename.endswith(".std") or filename.endswith(".stdf"):
                f = open(filename, 'rb')
            elif filename.endswith(".gz"):
                f = gzip.open(filename, 'rb')
            reopen_fn = None
            # I guess I'm making a parsing object here, but again I didn't write this part
            p = Parser(inp=f, reopen_fn=reopen_fn)
            fsize = os.path.getsize(filename)
            fname = filename  # + "_csv_log.csv"
            startt = time.time()  # 9.7s --> TextWriter; 7.15s --> MyTestResultProfiler

            # Writing to a text file instead of vomiting it to the console
            data_summary = MyTestResultProfiler(filename=fname,file=f, filezise = fsize, notify_progress_bar=notify_progress_bar)
            p.addSink(data_summary)
            p.parse()

            endt = time.time()
            print('STDF处理时间：', endt - startt)
            # data_summary_all = data_summary_all.append(data_summary.frame)
            # data_summary_all = pd.concat([data_summary_all,data_summary.frame],sort=False,join='outer')
            if data_summary_all.empty:
                data_summary_all = data_summary.frame
            else:
                # data_summary_all = pd.merge(data_summary_all, data_summary.frame, sort=False, how='outer')
                data_summary_all = pd.concat([data_summary_all, data_summary.frame], sort=False,
                                             join='outer', ignore_index=True)
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

    @staticmethod
    def to_ASCII(filename):
        # Open std file/s
        if filename.endswith(".std") or filename.endswith(".stdf"):
            f = open(filename, 'rb')
        elif filename.endswith(".gz"):
            f = gzip.open(filename, 'rb')
        reopen_fn = None

        # I guess I'm making a parsing object here, but again I didn't write this part
        p = Parser(inp=f, reopen_fn=reopen_fn)

        fname = filename  # + "_csv_log.csv"
        startt = time.time()  # 9.7s --> TextWriter; 7.15s --> MyTestResultProfiler

        # Writing to a text file instead of vomiting it to the console
        stdf_df = My_STDF_V4_2007_1_Profiler(filename)
        p.addSink(stdf_df)
        p.parse()

        endt = time.time()
        print('STDF处理时间：', endt - startt)

        stdf_df.all_test_result_pd.to_csv(filename + "_diag_log.csv", index=False)

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
    def __init__(self, filename, file, filezise, notify_progress_bar):
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
        self.exec_type = '' #IG-XL or 93000

        self.tname_tnumber_dict = {}
        self.sbin_description = {}
        self.DIE_ID = []
        self.lastrectype = None
        self.pmr_dict = {}

        self.all_test_result_pd = pd.DataFrame()
        self.frame = pd.DataFrame()

        self.file = file #io.BytesIO(b'')
        self.filezise = filezise
        self.notify_progress_bar = notify_progress_bar

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
        self.exec_type = ''

        self.tname_tnumber_dict = {}
        self.sbin_description = {}
        self.DIE_ID = []
        self.lastrectype = None
        self.pmr_dict = {}

    def after_send(self, dataSource, data):
        rectype, fields = data
        # First, get lot/wafer ID etc.
        if rectype == V4.mir:
            self.tester_nam = str(fields[V4.mir.NODE_NAM])
            start_t = time.localtime(int(fields[V4.mir.START_T]))
            self.start_t = str(time.strftime("%Y/%m/%d-%H:%M:%S", start_t))
            self.job_nam = str(fields[V4.mir.JOB_NAM])
            self.lot_id = str(fields[V4.mir.LOT_ID])
            self.exec_type = str(fields[V4.mir.EXEC_TYP])
        if rectype == V4.wir:
            self.wafer_id = str(fields[V4.wir.WAFER_ID])
            self.DIE_ID = []
        if rectype == V4.pmr:
            if self.exec_type == '93000':
                self.pmr_dict[str(fields[V4.pmr.PMR_INDX])] = str(fields[V4.pmr.CHAN_NAM])
            else:
                self.pmr_dict[str(fields[V4.pmr.PMR_INDX])] = str(fields[V4.pmr.LOG_NAM])
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
            # get rid of channel number in TName, so that the csv file would not split the sites data into different columns
            tname = fields[V4.ptr.TEST_TXT]
            tname_list = tname.split(' ')
            if len(tname_list) == 5:
                tname_list.pop(2) #remove channel number
            tname = ' '.join(tname_list)
            tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + tname #fields[V4.ptr.TEST_TXT]

            # Process the scale unit, but meanless in IG-XL STDF, comment it
            unit = str(fields[V4.ptr.UNITS])
            val_scal = fields[V4.ptr.RES_SCAL]
            # if val_scal == 0:
            #     unit = unit
            # elif val_scal == 2:
            #     unit = '%' + unit
            # elif val_scal == 3:
            #     unit = 'm' + unit
            # elif val_scal == 6:
            #     unit = 'u' + unit
            # elif val_scal == 9:
            #     unit = 'n' + unit
            # elif val_scal == 12:
            #     unit = 'p' + unit
            # elif val_scal == 15:
            #     unit = 'f' + unit
            # elif val_scal == -3:
            #     unit = 'K' + unit
            # elif val_scal == -6:
            #     unit = 'M' + unit
            # elif val_scal == -9:
            #     unit = 'G' + unit
            # elif val_scal == -12:
            #     unit = 'T' + unit

            if not (tname_tnumber in self.tname_tnumber_dict):
                self.tname_tnumber_dict[tname_tnumber] = str(fields[V4.ptr.TEST_NUM]) + '|' + \
                                                         tname + '|' + \
                                                         str(fields[V4.ptr.HI_LIMIT]) + '|' + \
                                                         str(fields[V4.ptr.LO_LIMIT]) + '|' + \
                                                         unit #str(fields[V4.ptr.UNITS])
            # Be careful here, Hi/Low limit only stored in first PTR
            # tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + fields[V4.ptr.TEST_TXT] + '|' + \
            #                 str(fields[V4.ptr.HI_LIMIT]) + '|' + str(fields[V4.ptr.LO_LIMIT]) + '|' + \
            #                 str(fields[V4.ptr.UNITS])
            current_tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + tname #fields[V4.ptr.TEST_TXT]
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

        # This is multiple-result parametric record for a single limit for all the multiple test results
        if rectype == V4.mpr:
            # process tset name and pin name
            tmp_pin_list = [self.pmr_dict[str(number)] for number in fields[V4.mpr.RTN_INDX]]
            tmp_RSLT_list = fields[V4.mpr.RTN_RSLT]
            tname = fields[V4.mpr.TEST_TXT]

            # Process the scale unit, but meanless in IG-XL STDF, comment it
            unit = str(fields[V4.mpr.UNITS])
            # val_scal = fields[V4.mpr.RES_SCAL]
            # if val_scal == 0:
            #     unit = unit
            # elif val_scal == 2:
            #     unit = '%' + unit
            # elif val_scal == 3:
            #     unit = 'm' + unit
            # elif val_scal == 6:
            #     unit = 'u' + unit
            # elif val_scal == 9:
            #     unit = 'n' + unit
            # elif val_scal == 12:
            #     unit = 'p' + unit
            # elif val_scal == 15:
            #     unit = 'f' + unit
            # elif val_scal == -3:
            #     unit = 'K' + unit
            # elif val_scal == -6:
            #     unit = 'M' + unit
            # elif val_scal == -9:
            #     unit = 'G' + unit
            # elif val_scal == -12:
            #     unit = 'T' + unit

            for i in range(len(tmp_pin_list)):
                tname_pinname = tname + '--' + tmp_pin_list[i]
                tname_tnumber = str(fields[V4.mpr.TEST_NUM]) + '|' + tname_pinname
                if not (tname_tnumber in self.tname_tnumber_dict):
                    self.tname_tnumber_dict[tname_tnumber] = str(fields[V4.mpr.TEST_NUM]) + '|' + \
                                                             tname_pinname + '|' + \
                                                             str(fields[V4.mpr.HI_LIMIT]) + '|' + \
                                                             str(fields[V4.mpr.LO_LIMIT]) + '|' + \
                                                             unit
                current_tname_tnumber = str(fields[V4.mpr.TEST_NUM]) + '|' + tname_pinname
                full_tname_tnumber = self.tname_tnumber_dict[current_tname_tnumber]
                if not (full_tname_tnumber in self.test_result_dict):
                    self.test_result_dict[full_tname_tnumber] = [None] * self.site_count
                else:
                    pass
                    # if len(self.test_result_dict[full_tname_tnumber]) >= self.site_count:
                    #     # print('Duplicate test number found for test: ', tname_tnumber)
                    #     return

                for j in range(self.site_count):
                    if fields[V4.mpr.SITE_NUM] == self.test_result_dict['SITE_NUM'][j]:
                        if fields[V4.mpr.TEST_FLG] == 0:
                            mpr_result = str(tmp_RSLT_list[i])
                        else:
                            mpr_result = str(tmp_RSLT_list[i]) + '(F)'
                        self.test_result_dict[full_tname_tnumber][j] = mpr_result

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
        self.notify_progress_bar.emit(int(self.file.tell()/self.filezise*100))
        # print(int(self.file.tell()/self.filezise*100))

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
    def __init__(self, filename):
        self.reset_flag = False
        self.lastrectype = None
        self.is_V4_2007_1 = False
        self.pmr_dict = {}
        self.pat_name = ''
        self.mod_name = ''

        self.file_nam = filename.split('/')[-1]
        self.tester_nam = ''
        self.start_t = ''
        self.pgm_nam = ''
        self.lot_id = ''
        self.wafer_id = ''
        self.job_nam = ''

        self.cont_flag = 0
        self.test_result_dict = {'FILE_NAM': [], 'TESTER_NAM': [], 'START_T': [], 'PGM_NAM': [],
                                 'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [],
                                 'X_COORD': [], 'Y_COORD': [], 'PART_ID': [], 'TEST_NAME': [],
                                 'PAT_NAME': [], 'MOD_NAME': [], 'FAIL_COUNT': [], 'FAIL_CYCLE': [],
                                 'FAIL_PIN': [], 'EXP_DATA': [], 'CAP_DATA': []}
        self.cyc_ofst = []
        self.fail_pin = []
        self.exp_data = []
        self.cap_data = []
        self.all_test_result_pd = pd.DataFrame()
        self.total_logged_count = 0
        self.row_cnt = 0

    def after_begin(self, dataSource):
        self.reset_flag = False
        self.lastrectype = None
        self.is_V4_2007_1 = False
        self.pmr_dict = {}
        self.pat_nam_dict = {}
        self.mod_nam_dict = {}
        self.cont_flag = 0
        self.test_result_dict = {'FILE_NAM': [], 'TESTER_NAM': [], 'START_T': [], 'PGM_NAM': [],
                                 'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [],
                                 'X_COORD': [], 'Y_COORD': [], 'PART_ID': [], 'TEST_NAME': [],
                                 'PAT_NAME': [], 'MOD_NAME': [], 'FAIL_COUNT': [], 'FAIL_CYCLE': [],
                                 'FAIL_PIN': [], 'EXP_DATA': [], 'CAP_DATA': []}

        self.cyc_ofst = []
        self.fail_pin = []
        self.exp_data = []
        self.cap_data = []
        self.all_test_result_pd = pd.DataFrame()
        self.total_logged_count = 0
        self.row_cnt = 0

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
        if rectype == V4.bps:
            self.pgm_nam = str(fields[V4.bps.SEQ_NAME])
        if rectype == V4.pir:
            # Found BPS and EPS in sample stdf, add 'lastrectype' to overcome it
            if self.reset_flag or self.lastrectype != rectype:
                self.reset_flag = False
                self.site_count = 0
                self.site_array = []
                self.row_cnt = []
                self.test_result_dict = {'FILE_NAM': [], 'TESTER_NAM': [], 'START_T': [], 'PGM_NAM': [],
                                         'JOB_NAM': [], 'LOT_ID': [], 'WAFER_ID': [], 'SITE_NUM': [],
                                         'X_COORD': [], 'Y_COORD': [], 'PART_ID': [], 'TEST_NAME': [],
                                         'PAT_NAME': [], 'MOD_NAME': [], 'FAIL_CNT': [], 'LOGGED_FAIL_CNT': [],
                                         'FAIL_CYCLE': [], 'FAIL_PIN': [], 'EXP_DATA': [], 'CAP_DATA': []}

            self.site_count += 1
            self.site_array.append(fields[V4.pir.SITE_NUM])
            # self.test_result_dict['SITE_NUM'] = self.site_array
            self.row_cnt.append(0)

        if rectype == V4.vur and fields[V4.vur.UPD_NAM] == 'Scan:2007.1':
            self.is_V4_2007_1 = True
        if rectype == V4.pmr:
            self.pmr_dict[str(fields[V4.pmr.PMR_INDX])] = str(fields[V4.pmr.LOG_NAM])
        if rectype == V4.psr:
            psr_nam = str(fields[V4.psr.PSR_NAM])
            self.pat_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam.split(':')[0]
            self.mod_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam.split(':')[1]
        if rectype == V4.str:
            for i in range(self.site_count):
                if fields[V4.str.SITE_NUM] == self.site_array[i]:
                    self.cont_flag = fields[V4.str.CONT_FLG]
                    self.cyc_ofst = self.cyc_ofst + fields[V4.str.CYC_OFST]
                    self.fail_pin = self.fail_pin + [self.pmr_dict[str(number)] for number in fields[V4.str.PMR_INDX]] # fields[V4.str.PMR_INDX]
                    self.exp_data = self.exp_data + [chr(number) for number in fields[V4.str.EXP_DATA]] # fields[V4.str.EXP_DATA]
                    self.cap_data = self.cap_data + [chr(number) for number in fields[V4.str.CAP_DATA]] # fields[V4.str.CAP_DATA]

                    if self.cont_flag == 0:
                        self.total_logged_count = fields[V4.str.TOTL_CNT]
                        self.row_cnt[i] = self.row_cnt[i] + self.total_logged_count

                        self.test_result_dict['SITE_NUM'] = self.test_result_dict['SITE_NUM'] + [fields[V4.str.SITE_NUM]] * self.total_logged_count
                        self.test_result_dict['FAIL_CNT'] = self.test_result_dict['FAIL_CNT'] + [fields[V4.str.TOTF_CNT]] * self.total_logged_count
                        self.test_result_dict['LOGGED_FAIL_CNT'] = self.test_result_dict['LOGGED_FAIL_CNT'] + [fields[V4.str.TOTL_CNT]] * self.total_logged_count
                        self.test_result_dict['TEST_NAME'] = self.test_result_dict['TEST_NAME'] + [fields[V4.str.TEST_TXT]] * self.total_logged_count
                        self.test_result_dict['PAT_NAME'] = self.test_result_dict['PAT_NAME'] + [self.pat_nam_dict[str(fields[V4.str.PSR_REF])]] * self.total_logged_count
                        self.test_result_dict['MOD_NAME'] = self.test_result_dict['MOD_NAME'] + [self.mod_nam_dict[str(fields[V4.str.PSR_REF])]] * self.total_logged_count

                        self.test_result_dict['FAIL_CYCLE'] = self.test_result_dict['FAIL_CYCLE'] + self.cyc_ofst
                        self.test_result_dict['FAIL_PIN'] = self.test_result_dict['FAIL_PIN'] + self.fail_pin
                        self.test_result_dict['EXP_DATA'] = self.test_result_dict['EXP_DATA'] + self.exp_data
                        self.test_result_dict['CAP_DATA'] = self.test_result_dict['CAP_DATA'] + self.cap_data
                        # Reset
                        self.cyc_ofst = []
                        self.fail_pin = []
                        self.exp_data = []
                        self.cap_data = []
                        pass
                    else:
                        pass

        if rectype == V4.eps:
            self.reset_flag = True
        if rectype == V4.prr:  # and fields[V4.prr.SITE_NUM]:
            for i in range(self.site_count):
                if fields[V4.prr.SITE_NUM] == self.site_array[i]:
                    die_x = fields[V4.prr.X_COORD]
                    die_y = fields[V4.prr.Y_COORD]
                    part_id = fields[V4.prr.PART_ID]

                    self.test_result_dict['FILE_NAM'] += [self.file_nam] * self.row_cnt[i]
                    self.test_result_dict['TESTER_NAM'] += [self.tester_nam] * self.row_cnt[i]
                    self.test_result_dict['START_T'] += [self.start_t] * self.row_cnt[i]
                    self.test_result_dict['PGM_NAM'] += [self.pgm_nam] * self.row_cnt[i]

                    self.test_result_dict['JOB_NAM'] += [self.job_nam] * self.row_cnt[i]
                    self.test_result_dict['LOT_ID'] += [self.lot_id] * self.row_cnt[i]
                    self.test_result_dict['WAFER_ID'] += [self.wafer_id] * self.row_cnt[i]

                    self.test_result_dict['X_COORD'] += [die_x] * self.row_cnt[i]
                    self.test_result_dict['Y_COORD'] += [die_y] * self.row_cnt[i]
                    self.test_result_dict['PART_ID'] += [part_id] * self.row_cnt[i]
            # Send current part result to all test result pd
            if fields[V4.prr.SITE_NUM] == self.site_array[-1]:
                # tmp_pd = pd.DataFrame(self.test_result_dict)
                tmp_pd = pd.DataFrame.from_dict(self.test_result_dict, orient='index').T
                # tmp_pd.transpose()
                self.all_test_result_pd = self.all_test_result_pd.append(tmp_pd, sort=False, ignore_index=True)
        self.lastrectype = rectype

    def after_complete(self, dataSource):
        pass
