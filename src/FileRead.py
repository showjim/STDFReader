# -*- coding:utf-8 -*-
import base64

import pandas as pd
from abc import ABC
import time
import gzip
import os

from pystdf.IO import Parser
import pystdf.V4 as V4
from pystdf.Writers import *
from pystdf.Importer import STDF2DataFrame
from pathlib import Path

############################
# FILE READING AND PARSING #
############################

# So sad there is no detaial document about PySTDF, thanks to Thomas's code as sample
class FileReaders(ABC):

    @staticmethod
    def _build_skip_list(keep_short_names):
        """
        Build a list of record type names to skip during parsing.

        Args:
            keep_short_names: Set of short record type names to KEEP (e.g., {'Dtr', 'Mir', 'Pir'})

        Returns:
            List of full record type names to skip (e.g., ['pystdf.V4.Ptr', 'pystdf.V4.Ftr', ...])
        """
        return [record.name for record in V4.records
                if record.name.split('.')[-1] not in keep_short_names]

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
    def to_csv(file_names, output_file_name, notify_progress_bar, ignore_TNUM=False, ignore_chnum=False):
        data_summary_all = pd.DataFrame()
        i=0
        for filename in file_names:
            # Open std file/s
            if filename.endswith(".std") or filename.endswith(".STD") or filename.endswith(".stdf") or filename.endswith(".STDF"):
                f = open(filename, 'rb')
            elif filename.endswith(".gz") or filename.endswith(".GZ"):
                f = gzip.open(filename, 'rb')
            reopen_fn = None
            # I guess I'm making a parsing object here, but again I didn't write this part
            p = Parser(inp=f, reopen_fn=reopen_fn)
            fsize = os.path.getsize(filename)
            fname = filename  # + "_csv_log.csv"
            startt = time.time()  # 9.7s --> TextWriter; 7.15s --> MyTestResultProfiler

            # Writing to a text file instead of vomiting it to the console
            data_summary = MyTestResultProfiler(filename=fname,file=f, filezise = fsize,
                                                notify_progress_bar=notify_progress_bar,
                                                ignore_tnum=ignore_TNUM, ignore_chnum=ignore_chnum)
            p.addSink(data_summary)
            p.parse(skipType="pystdf.V4.Str")

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
            f.close()
        FileReaders.write_to_csv(data_summary_all, output_file_name)

    @staticmethod
    def write_to_csv(data_summary_all, output_file_name):
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

        writer.close()

    # this function to extract only 1 type of record, in case STDF file is too large
    @staticmethod
    def rec_to_csv(filename, RecName:str, extract_zip:bool=False):

        # Converts the stdf to a dataframe
        table = FileReaders.STDFRec2DataFrame(filename, RecName)

        # Extract zip file from DTR
        if extract_zip:
            FileReaders.extract_zips_binary(table)

        # The name of the new file, preserving the directory of the previous
        fname = filename + "_" + RecName + "_Rec.csv"

        # Make sure the order of columns complies the specs
        record = [r for r in V4.records if r.__class__.__name__.upper() == RecName]
        if len(record) == 0:
            print("Ignore exporting table %s: No such record type exists." % RecName)
        else:
            columns = [field[0] for field in record[0].fieldMap]
            if len(record[0].fieldMap) > 0:
                # try:
                table.to_csv(fname, index=False)
            # except BaseException:
            #     os.system('pause')

    @staticmethod
    def extract_zips_binary(df):
        zip_files = []  # for all ZIP files in byte
        current_zip = []  # for single ZIP file

        for _, row in df.iterrows():
            cell = row["GEN_DATA"]
            content = cell[0]
            if 'Everyone is awesome beginning' in content:
                current_zip = []
            elif 'Write GDR is done' in content:
                if current_zip:  # ensure the data is existing
                    # flatten the data in bytes array
                    flat_data = [num for sublist in current_zip for num in sublist]
                    zip_files.append(bytes(flat_data))
            else:
                current_zip.extend(cell)  # combine ZIP file data

        # Write ZIP
        for i, zip_data in enumerate(zip_files):
            output_path = Path(f"recovered_zip_{i}.zip")
            with open(output_path, "wb") as f:
                f.write(zip_data)
            print(f"成功恢复: {output_path}")

    @staticmethod
    def extract_zips_base64(df):
        zip_files = [] # 存储所有ZIP文件的bytes数据
        current_zip = [] # 当前正在收集的ZIP文件数据

        for _, row in df.iterrows():
            cell = row["GEN_DATA"]
            content = cell[0]
            if 'Everyone is awesome beginning' in content:
                current_zip = []
            elif 'Write GDR is done' in content:
                if current_zip:  # 确保有数据
                    # 展平所有二维列表并转为bytes
                    # flat_data = [num for sublist in current_zip for num in sublist]
                    # zip_files.append(bytes(flat_data))
                    flat_data = ''.join(current_zip)
                    zip_files.append(base64.b64decode(flat_data))
            else:
                current_zip.extend(cell)  # 收集ZIP文件的一部分

        # 写入 ZIP
        for i, zip_data  in enumerate(zip_files):
            output_path = Path(f"recovered_zip_{i}.zip")
            with open(output_path, "wb") as f:
                f.write(zip_data)
            print(f"成功恢复: {output_path}")

    # to extract PSR/STR record and convert to ASCII
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

        # Build skip list programmatically
        # My_STDF_V4_2007_1_Profiler only processes: MIR, WIR, BPS, PMR, PSR, STR, PIR, EPS, PRR, VUR
        # STR is the Scan Test Record we want to extract!
        keep_records = {'Mir', 'Wir', 'Bps', 'Pmr', 'Psr', 'Str', 'Pir', 'Eps', 'Prr', 'Vur'}
        skip_types = FileReaders._build_skip_list(keep_records)

        # Skip all unnecessary record types to improve performance
        p.parse(skipType=skip_types)

        endt = time.time()
        print('STDF处理时间：', endt - startt)

        stdf_df.all_test_result_pd.to_csv(filename + "_diag_log.csv", index=False)

    @staticmethod
    def STDFRec2DataFrame(fname, RecName:str):
        """ Convert selected STDF record to a DataFrame objects
        """
        RecName = RecName.upper()
        data = FileReaders.SearchSTDF(fname, RecName)
        Rec = {}
        BigTable = pd.DataFrame()
        for datum in data:
            RecType = datum[0].__class__.__name__.upper()
            if RecName == RecType:
                if RecType not in BigTable.keys():
                    BigTable[RecType] = {}
                # Rec = BigTable[RecType]
                for k,v in zip(datum[0].fieldMap,datum[1]):
                    if k[0] not in Rec.keys():
                        Rec[k[0]] = []
                    Rec[k[0]].append(v)

        BigTable = pd.DataFrame(Rec)
        return BigTable

    @staticmethod
    def SearchSTDF(fname, rec_name):
        # Map rec_name to short record type name
        rec_name_map = {
            "DTR": "Dtr",
            "GDR": "Gdr",
            "TSR": "Tsr"
        }

        target_rec = rec_name_map.get(rec_name.upper())

        if not target_rec:
            # If not in map, assume it's already a short name
            target_rec = rec_name

        # Build skip list programmatically - skip everything EXCEPT target
        skip_types = FileReaders._build_skip_list({target_rec})

        with open(fname,'rb') as fin:
            p = Parser(inp=fin)
            storage = MyMemoryWriter(rec_name)
            p.addSink(storage)
            # Skip all record types except the one we want
            p.parse(skipType=skip_types)
        return storage.data

class MyMemoryWriter:
    def __init__(self, rec_name):
        self.data = []
        self.rec_name = rec_name
        self.typ = V4.dtr
    def after_send(self, dataSource, data):
        rectype, fields = data
        self.get_typ()
        # First, get lot/wafer ID etc.
        if rectype == self.typ:
            self.data.append(data)
    def get_typ(self):
        if self.rec_name == "DTR":
            self.typ = V4.dtr
        elif self.rec_name == "GDR":
            self.typ = V4.gdr
        elif self.rec_name == "TSR":
            self.typ = V4.tsr

    def write(self,line):
        pass
    def flush(self):
        pass # Do nothing

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
    def __init__(self, filename, file, filezise, notify_progress_bar, ignore_tnum, ignore_chnum):
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

        #for MPR
        self.mpr_pin_dict = {}
        self.mpr_first_field = None

        self.all_test_result_pd = pd.DataFrame()
        self.frame = pd.DataFrame()

        self.file = file #io.BytesIO(b'')
        self.filezise = filezise
        self.notify_progress_bar = notify_progress_bar
        self.ignore_tnum = ignore_tnum
        self.ignore_chnum = ignore_chnum

        # in order to distinguish same name inst in flow
        self.same_name_inst_cnt_dict = {}
        self.cur_inst_name = ""
        self.pre_inst_name = ""

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

        #for MPR
        self.mpr_pin_dict = {}
        self.mpr_first_field = None

        # in order to distinguish same name inst in flow
        self.same_name_inst_cnt_dict = {}
        self.cur_inst_name = ""
        self.pre_inst_name = ""

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

            self.same_name_inst_cnt_dict = {}
            self.cur_inst_name = ""
            self.pre_inst_name = ""
        if rectype == V4.bps:
            self.pgm_nam = str(fields[V4.bps.SEQ_NAME])
            self.same_name_inst_cnt_dict = {}
            self.cur_inst_name = ""
            self.pre_inst_name = ""
        if rectype == V4.ptr:  # and fields[V4.prr.SITE_NUM]:
            # get rid of channel number in TName, so that the csv file would not split the sites data into different columns
            tname = fields[V4.ptr.TEST_TXT]
            # if tname == "IDDQ_top_AA_Scan_iddq_sub0_Debug VDDCORE_Min":
            #     print("OK")
            tnumber = str(fields[V4.ptr.TEST_NUM])
            if self.ignore_tnum:
                tnumber = "0"

            tname_list = tname.split(' ')
            if self.ignore_chnum:
                tname_list.pop(2)  # remove channel number
            # if len(tname_list) == 5:
            #     tname_list.pop(2) #remove channel number
            # elif len(tname_list) == 3 :
            #     tname_list.pop(2)  # remove channel number
            tname = ' '.join(tname_list)
            tname_tnumber = tnumber + '|' + tname #fields[V4.ptr.TEST_TXT]

            # to distinguish same name inst in flow
            site = str(fields[V4.ptr.SITE_NUM])
            self.pre_inst_name = self.cur_inst_name
            self.cur_inst_name = site + '|' + tname_tnumber

            if (self.cur_inst_name != self.pre_inst_name) and (self.pre_inst_name != "") and not(self.cur_inst_name + "_Appeared" in self.pre_inst_name):
                # pure_inst_pre = self.pre_inst_name.split("|")[1].split()[0]
                # pure_inst_cur = self.cur_inst_name.split("|")[1].split()[0]
                # if pure_inst_pre != pure_inst_cur:
                    if self.cur_inst_name in self.same_name_inst_cnt_dict.keys():
                        self.same_name_inst_cnt_dict[self.cur_inst_name] += 1
                        tname_tnumber += "_Appeared" + str(self.same_name_inst_cnt_dict[self.cur_inst_name])
                        self.cur_inst_name = site + "|" + tname_tnumber
                    else:
                        self.same_name_inst_cnt_dict[self.cur_inst_name] = 1
            elif self.cur_inst_name + "_Appeared" in self.pre_inst_name:
                tname_tnumber += "_Appeared" + str(self.same_name_inst_cnt_dict[self.cur_inst_name])
                self.cur_inst_name = site + "|" + tname_tnumber

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
                if (tnumber + '|' + tname) in self.tname_tnumber_dict:
                    self.tname_tnumber_dict[tname_tnumber] = self.tname_tnumber_dict[tnumber + '|' + tname].replace(tnumber + '|' + tname, tname_tnumber)
                else:
                    self.tname_tnumber_dict[tname_tnumber] = tname_tnumber + '|' + \
                                                             str(fields[V4.ptr.HI_LIMIT]) + '|' + \
                                                             str(fields[V4.ptr.LO_LIMIT]) + '|' + \
                                                             unit #str(fields[V4.ptr.UNITS])
            # Be careful here, Hi/Low limit only stored in first PTR
            # tname_tnumber = str(fields[V4.ptr.TEST_NUM]) + '|' + fields[V4.ptr.TEST_TXT] + '|' + \
            #                 str(fields[V4.ptr.HI_LIMIT]) + '|' + str(fields[V4.ptr.LO_LIMIT]) + '|' + \
            #                 str(fields[V4.ptr.UNITS])
            current_tname_tnumber = tname_tnumber # tnumber + '|' + tname #fields[V4.ptr.TEST_TXT]
            full_tname_tnumber = self.tname_tnumber_dict[current_tname_tnumber]
            if not (full_tname_tnumber in self.test_result_dict):
                self.test_result_dict[full_tname_tnumber] = [None] * self.site_count
            else:
                pass
                # if len(self.test_result_dict[full_tname_tnumber]) >= self.site_count:
                #     # print('Duplicate test number found for test: ', tname_tnumber)
                #     return
            test_flag = 0
            for i in range(self.site_count):
                if fields[V4.ptr.SITE_NUM] == self.test_result_dict['SITE_NUM'][i]:
                    test_flag = fields[V4.ptr.TEST_FLG]
                    if test_flag == 0:
                        ptr_result = str(fields[V4.ptr.RESULT])
                    else:
                        if test_flag & 0b1 == 1:
                            ptr_result = str(fields[V4.ptr.RESULT]) + '(A)'
                        else:
                            ptr_result = str(fields[V4.ptr.RESULT]) + '(F)'
                    self.test_result_dict[full_tname_tnumber][i] = ptr_result
                    break

        # This is multiple-result parametric record for a single limit for all the multiple test results
        if rectype == V4.mpr:
            # process tset name and pin name
            tmp_RSLT_list = fields[V4.mpr.RTN_RSLT]
            tname = fields[V4.mpr.TEST_TXT]

            key = str(fields[V4.mpr.TEST_NUM]) + "_" + tname
            if fields[V4.mpr.RTN_INDX] is None:
                # Thanks to Wade Song to figure out this bug in process MPR
                for keyTemp in self.mpr_pin_dict.keys():
                    if tname.split(':')[1] in keyTemp:
                        tmp_pin_list = self.mpr_pin_dict[keyTemp]
                        break

            else:
                self.mpr_pin_dict[key] = [self.pmr_dict[str(number)] for number in fields[V4.mpr.RTN_INDX]]
                self.mpr_first_field = fields # This is because All data beginning with the OPT_FLAG field has a special
                                              # function in the STDF file. The first MPR for each test will have these
                                              # fields filled in. like UNITS/RTN_INDX/HI_LIMIT/LO_LIMIT
                tmp_pin_list = self.mpr_pin_dict[key]

            # Process the scale unit, but meanless in IG-XL STDF, comment it
            unit = str(self.mpr_first_field[V4.mpr.UNITS]) #str(fields[V4.mpr.UNITS])
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
                tname_pinname = tname + '@' + tmp_pin_list[i]
                tname_tnumber = str(fields[V4.mpr.TEST_NUM]) + '|' + tname_pinname
                if not (tname_tnumber in self.tname_tnumber_dict):
                    self.tname_tnumber_dict[tname_tnumber] = str(self.fields[V4.mpr.TEST_NUM]) + '|' + \
                                                             tname_pinname + '|' + \
                                                             str(self.mpr_first_field[V4.mpr.HI_LIMIT]) + '|' + \
                                                             str(self.mpr_first_field[V4.mpr.LO_LIMIT]) + '|' + \
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
                        test_flag = fields[V4.mpr.TEST_FLG]
                        if test_flag == 0:
                            try:
                                mpr_result = str(tmp_RSLT_list[i])
                            except:
                                print("OK")
                        else:
                            if test_flag & 0b1 == 1:
                                mpr_result = str(tmp_RSLT_list[i]) + '(A)'
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
                    test_flag = fields[V4.ftr.TEST_FLG]
                    if test_flag == 0:
                        ftr_result = '-1'
                    else:
                        if test_flag & 0b1 == 1:
                            ftr_result = '0(A)'
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
                    if (part_flg & 0x1) ^ ((part_flg & 0x2)>>1) == 1 or (die_id in self.DIE_ID): # part_flg method cannot cover ENG mode
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
                # self.all_test_result_pd = self.all_test_result_pd.append(tmp_pd, sort=False, ignore_index=True)
                self.all_test_result_pd = pd.concat([self.all_test_result_pd, tmp_pd], sort=False, ignore_index=True)
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
        self.accumulated_fail_cyc_cnt = 0

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
        self.accumulated_fail_cyc_cnt = 0

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
            if ':' in psr_nam:
                self.pat_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam.split(':')[0]
                self.mod_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam.split(':')[1]
            else:
                self.pat_nam_dict[str(fields[V4.psr.PSR_INDX])] = psr_nam
                self.mod_nam_dict[str(fields[V4.psr.PSR_INDX])] = ""
        if rectype == V4.str:
            for i in range(self.site_count):
                if fields[V4.str.SITE_NUM] == self.site_array[i]:
                    self.cont_flag = fields[V4.str.CONT_FLG]
                    self.total_logged_count = fields[V4.str.TOTL_CNT]
                    cycle_offset_cnt = fields[V4.str.CYCO_CNT]
                    self.accumulated_fail_cyc_cnt += cycle_offset_cnt
                    if cycle_offset_cnt > 0:
                        self.cyc_ofst = self.cyc_ofst + fields[V4.str.CYC_OFST]
                        self.fail_pin = self.fail_pin + [self.pmr_dict[str(number)] for number in fields[V4.str.PMR_INDX]] # fields[V4.str.PMR_INDX]
                        if len(fields[V4.str.EXP_DATA]) > 0:
                            self.exp_data = self.exp_data + [chr(number) for number in fields[V4.str.EXP_DATA]] # fields[V4.str.EXP_DATA]
                        else: # in case no Exp data given
                            self.exp_data = self.exp_data + ["Not Provided"] * len(fields[V4.str.CYC_OFST])
                        if len(fields[V4.str.EXP_DATA]) > 0:
                            self.cap_data = self.cap_data + [chr(number) for number in fields[V4.str.CAP_DATA]] # fields[V4.str.CAP_DATA]
                        else: # in case no Cap data given
                            self.cap_data = self.cap_data + ["Not Provided"] * len(fields[V4.str.CYC_OFST])
                    else:
                        print("Empty Fail Cycle STR found, skip...")

                    if self.cont_flag == 0: # and self.total_logged_count == self.accumulated_fail_cyc_cnt:
                        # self.total_logged_count = fields[V4.str.TOTL_CNT]
                        self.row_cnt[i] = self.row_cnt[i] + self.accumulated_fail_cyc_cnt

                        self.test_result_dict['SITE_NUM'] = self.test_result_dict['SITE_NUM'] + [fields[V4.str.SITE_NUM]] * self.accumulated_fail_cyc_cnt
                        self.test_result_dict['FAIL_CNT'] = self.test_result_dict['FAIL_CNT'] + [fields[V4.str.TOTF_CNT]] * self.accumulated_fail_cyc_cnt
                        self.test_result_dict['LOGGED_FAIL_CNT'] = self.test_result_dict['LOGGED_FAIL_CNT'] + [fields[V4.str.TOTL_CNT]] * self.accumulated_fail_cyc_cnt
                        self.test_result_dict['TEST_NAME'] = self.test_result_dict['TEST_NAME'] + [fields[V4.str.TEST_TXT]] * self.accumulated_fail_cyc_cnt
                        self.test_result_dict['PAT_NAME'] = self.test_result_dict['PAT_NAME'] + [self.pat_nam_dict[str(fields[V4.str.PSR_REF])]] * self.accumulated_fail_cyc_cnt
                        self.test_result_dict['MOD_NAME'] = self.test_result_dict['MOD_NAME'] + [self.mod_nam_dict[str(fields[V4.str.PSR_REF])]] * self.accumulated_fail_cyc_cnt

                        self.test_result_dict['FAIL_CYCLE'] = self.test_result_dict['FAIL_CYCLE'] + self.cyc_ofst
                        self.test_result_dict['FAIL_PIN'] = self.test_result_dict['FAIL_PIN'] + self.fail_pin
                        self.test_result_dict['EXP_DATA'] = self.test_result_dict['EXP_DATA'] + self.exp_data
                        self.test_result_dict['CAP_DATA'] = self.test_result_dict['CAP_DATA'] + self.cap_data
                        # Reset
                        self.cyc_ofst = []
                        self.fail_pin = []
                        self.exp_data = []
                        self.cap_data = []
                        self.accumulated_fail_cyc_cnt = 0
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
                self.all_test_result_pd = pd.concat([self.all_test_result_pd, tmp_pd], sort=False, ignore_index=True)
                # self.all_test_result_pd = self.all_test_result_pd.append(tmp_pd, sort=False, ignore_index=True)
        self.lastrectype = rectype

    def after_complete(self, dataSource):
        pass
