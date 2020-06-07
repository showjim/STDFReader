# -*- coding:utf-8 -*-
import pandas as pd
from abc import ABC
import time
import xlsxwriter

from pystdf.IO import Parser
from pystdf.Writers import *
from pystdf.Importer import STDF2DataFrame

from MySink_Module import MyTestResultProfiler


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
        data_summary_all.to_csv(output_file_name + "_csv_log.csv")

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
