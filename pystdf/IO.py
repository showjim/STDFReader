#
# PySTDF - The Pythonic STDF Parser
# Copyright (C) 2006 Casey Marshall
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import io
import sys

import struct
import re
import chardet

from pystdf.Types import *
from pystdf import V4

from pystdf.Pipeline import DataSource

def appendFieldParser(fn, action):
    """Append a field parsing function to a record parsing function.
    This is used to build record parsing functions based on the record type specification."""
    def newRecordParser(*args):
        fields = fn(*args)
        try:
            fields.append(action(*args))
        except EndOfRecordException: pass
        return fields
    return newRecordParser

class Parser(DataSource):
    def readAndUnpack(self, header, fmt):
        size = struct.calcsize(fmt)
        if (size > header.len):
            self.inp.read(header.len)
            header.len = 0
            raise EndOfRecordException()
        buf = self.inp.read(size)
        if len(buf) == 0:
            self.eof = 1
            raise EofException()
        header.len -= len(buf)
        val,=struct.unpack(self.endian + fmt, buf)
        if isinstance(val,bytes):
            return val.decode("ascii")
        else:
            return val

    def readAndUnpackDirect(self, fmt):
        size = struct.calcsize(fmt)
        buf = self.inp.read(size)
        if len(buf) == 0:
            self.eof = 1
            raise EofException()
        val,=struct.unpack(self.endian + fmt, buf)
        return val

    def readField(self, header, stdfFmt):
        return self.readAndUnpack(header, packFormatMap[stdfFmt])

    def readFieldDirect(self, stdfFmt):
        return self.readAndUnpackDirect(packFormatMap[stdfFmt])

    def readCn(self, header):
        if header.len == 0:
            raise EndOfRecordException()
        slen = self.readField(header, "U1")
        if slen > header.len:
            self.inp.read(header.len)
            header.len = 0
            raise EndOfRecordException()
        if slen == 0:
            return ""
        buf = self.inp.read(slen);
        if len(buf) == 0:
            self.eof = 1
            raise EofException()
        header.len -= len(buf)
        val,=struct.unpack(str(slen) + "s", buf)
        try:
            return val.decode("ascii")
        except Exception as e:
            # to process when UnicodeDecodeError
            print(e)
            result = chardet.detect(val)
            encoding = result['encoding']
            print("The unknow format is: " + encoding)
            try:
                return val.decode(encoding)
            except UnicodeDecodeError:
                return val.decode("utf-8", errors="replace when UnicodeDecodeError")

    def readBn(self, header):
        blen = self.readField(header, "U1")
        bn = []
        for i in range(0, blen):
            bn.append(self.readField(header, "B1"))
        return bn

    def readDn(self, header):
        dbitlen = self.readField(header, "U2")
        dlen = dbitlen / 8
        if dbitlen % 8 > 0:
            dlen+=1
        dn = []
        for i in range(0, int(dlen)):
            dn.append(self.readField(header, "B1"))
        return dn

    def readVn(self, header):
        vlen = self.readField(header, "U2")
        vn = []
        for i in range(0, vlen):
            fldtype = self.readField(header, "B1")
            if fldtype in self.vnMap:
                vn.append(self.vnMap[fldtype](header))
        return vn

    def readArray(self, header, indexValue, stdfFmt):
        if (stdfFmt == 'N1'):
            self.readArray(header, indexValue/2+indexValue%2, 'U1')
            return
        arr = []
        for i in range(int(indexValue)):
            arr.append(self.unpackMap[stdfFmt](header, stdfFmt))
        return arr

    def readHeader(self):
        hdr = RecordHeader()
        hdr.len = self.readFieldDirect("U2")
        hdr.typ = self.readFieldDirect("U1")
        hdr.sub = self.readFieldDirect("U1")
        return hdr

    def __detectEndian(self):
        self.eof = 0
        header = self.readHeader()
        if header.typ != 0 and header.sub != 10:
            raise InitialSequenceException()
        cpuType = self.readFieldDirect("U1")
        if self.reopen_fn:
            self.inp = self.reopen_fn()
        else:
            self.inp.seek(0)
        if cpuType == 2:
            return '<' #'<'
        else:
            return '>'

    def header(self, header): pass

    def parse_records(self, count=0, skipType=""):
        i = 0
        self.eof = 0
        fields = None
        try:
            while self.eof==0:
                header = self.readHeader()
                self.header(header)
                curRec = self.inp.read(header.len)
                bakup = self.inp # backup current position
                self.inp = io.BytesIO(curRec) # make current position to the beginning of type

                if (header.typ, header.sub) in self.recordMap:
                    recType = self.recordMap[(header.typ, header.sub)]
                    recParser = self.recordParsers[(header.typ, header.sub)]
                    # add skipType to bypass parse some certain recType
                    if recType.name == skipType:
                        self.inp = bakup # restore file position
                        continue

                    fields = recParser(self, header, [])
                    if len(fields) < len(recType.columnNames):
                        fields += [None] * (len(recType.columnNames) - len(fields))
                    self.send((recType, fields))
                    if header.len > 0:
                        print(
			              "Warning: Broken header. Unprocessed data left in record of type '%s'. Working around it." % recType.__class__.__name__,
			              file=sys.stderr,
			            )
                        self.inp.read(header.len)
                        header.len = 0
                else:
                    self.inp.read(header.len)
                self.inp = bakup # restore file position
                if count:
                    i += 1
                    if i >= count: break
        except EofException: pass

    def auto_detect_endian(self):
        if self.inp.tell() == 0:
            self.endian = '@'
            self.endian = self.__detectEndian()

    def parse(self, count=0, skipType=""):
        self.begin()

        try:
            self.auto_detect_endian()
            self.parse_records(count, skipType)
            self.complete()
        except Exception as exception:
            self.cancel(exception)
            raise

    def getFieldParser(self, fieldType):
        if (fieldType.startswith("k")):
            fieldIndex, arrayFmt = re.match('k(\d+)([A-Z][a-z0-9]+)', fieldType).groups()
            return lambda self, header, fields: self.readArray(header, fields[int(fieldIndex)], arrayFmt)
        else:
            parseFn = self.unpackMap[fieldType]
            return lambda self, header, fields: parseFn(header, fieldType)

    def createRecordParser(self, recType):
        # Special handling for STR record with conditional fields
        if hasattr(recType, 'typ') and hasattr(recType, 'sub') and recType.typ == 15 and recType.sub == 30:
            return self.createStrRecordParser(recType)

        fn = lambda self, header, fields: fields
        for stdfType in recType.fieldStdfTypes:
            fn = appendFieldParser(fn, self.getFieldParser(stdfType))
        return fn

    def createStrRecordParser(self, recType):
        """
        Custom parser for STR (Scan Test Record) that handles conditional fields.
        MASK_MAP and FAL_MAP fields are only present when FMU_FLG > 0.
        """
        def strParser(self, header, fields):
            # Field indices for STR record (from V4.py)
            # 0-12: Fixed fields up to FMU_FLG
            fixed_field_indices = [
                0,   # CONT_FLG
                1,   # TEST_NUM
                2,   # HEAD_NUM
                3,   # SITE_NUM
                4,   # PSR_REF
                5,   # TEST_FLG
                6,   # LOG_TYP
                7,   # TEST_TXT
                8,   # ALARM_ID
                9,   # PROG_TXT
                10,  # RSLT_TXT
                11,  # Z_VAL
                12   # FMU_FLG
            ]

            # Read fixed fields (0-12)
            for i in fixed_field_indices:
                try:
                    field_value = self.unpackMap[recType.fieldStdfTypes[i]](header, recType.fieldStdfTypes[i])
                    fields.append(field_value)
                except EndOfRecordException:
                    break

            # Check FMU_FLG value (field 12)
            fmu_flg = fields[12] if len(fields) > 12 else 0

            # Fields 13-14: MASK_MAP and FAL_MAP (conditional, only if FMU_FLG > 0)
            if fmu_flg > 0:
                # Read MASK_MAP (field 13)
                try:
                    mask_map = self.readDn(header)
                    fields.append(mask_map)
                except EndOfRecordException:
                    fields.append(None)

                # Read FAL_MAP (field 14)
                try:
                    fal_map = self.readDn(header)
                    fields.append(fal_map)
                except EndOfRecordException:
                    fields.append(None)
            else:
                # FMU_FLG = 0, these fields don't exist in data
                # Insert None placeholders to maintain field positions
                fields.append(None)  # MASK_MAP
                fields.append(None)  # FAL_MAP

            # Read remaining fields (15 onwards)
            # These are fixed fields, need to handle array fields specially
            for i in range(15, len(recType.fieldStdfTypes)):
                try:
                    field_type = recType.fieldStdfTypes[i]

                    # Check if it's an array field (starts with 'k')
                    if field_type.startswith('k'):
                        match = re.match('k(\d+)([A-Z][a-z0-9]+)', field_type)
                        if match:
                            field_index = int(match.group(1))
                            array_fmt = match.group(2)

                            # For array fields, the index refers to the field position
                            # When FMU_FLG = 0, fields 13-14 are None, but indices are preserved
                            # So we can directly access fields[field_index]
                            try:
                                array_value = self.readArray(header, fields[field_index], array_fmt)
                                fields.append(array_value)
                            except (IndexError, EndOfRecordException):
                                fields.append(None)
                    else:
                        # Regular field
                        field_value = self.unpackMap[field_type](header, field_type)
                        fields.append(field_value)
                except EndOfRecordException:
                    # If we run out of data, append None for remaining fields
                    fields.append(None)

            return fields

        return strParser

    def __init__(self, recTypes=V4.records, inp=sys.stdin, reopen_fn=None, endian=None):
        DataSource.__init__(self, ['header']);
        self.eof = 1
        self.recTypes = set(recTypes)
        self.inp = inp
        self.reopen_fn = reopen_fn
        self.endian = endian

        self.recordMap = dict(
            [ ( (recType.typ, recType.sub), recType )
              for recType in recTypes ])

        self.unpackMap = {
            "C1": self.readField,
            "B1": self.readField,
            "U1": self.readField,
            "U2": self.readField,
            "U4": self.readField,
            "U8": self.readField,
            "I1": self.readField,
            "I2": self.readField,
            "I4": self.readField,
            "I8": self.readField,
            "R4": self.readField,
            "R8": self.readField,
            "Cn": lambda header, fmt: self.readCn(header),
            "Bn": lambda header, fmt: self.readBn(header),
            "Dn": lambda header, fmt: self.readDn(header),
            "Vn": lambda header, fmt: self.readVn(header)
        }

        self.recordParsers = dict(
            [ ( (recType.typ, recType.sub), self.createRecordParser(recType) )
              for recType in recTypes ])

        self.vnMap = {
            0: lambda header: self.inp.read(header, 1),
            1: lambda header: self.readField(header, "U1"),
            2: lambda header: self.readField(header, "U2"),
            3: lambda header: self.readField(header, "U4"),
            4: lambda header: self.readField(header, "I1"),
            5: lambda header: self.readField(header, "I2"),
            6: lambda header: self.readField(header, "I4"),
            7: lambda header: self.readField(header, "R4"),
            8: lambda header: self.readField(header, "R8"),
            10: lambda header: self.readCn(header),
            11: lambda header: self.readBn(header),
            12: lambda header: self.readDn(header),
            13: lambda header: self.readField(header, "U1")
        }
