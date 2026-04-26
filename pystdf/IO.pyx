# cython: language_level=3
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


# Pre-computed struct sizes
_pack_sizes = {fmt: struct.calcsize(fmt) for fmt in 'cBHIQbhiqfd'}


class Parser(DataSource):
    """STDF binary file parser. Optimized with Cython type declarations."""

    def readAndUnpack(self, header, fmt):
        """Read and unpack a single field value from the input stream."""
        cdef object s = self._struct_cache.get(fmt)
        cdef int size
        cdef bytes buf
        cdef object val
        if s is None:
            s = struct.Struct(self.endian + fmt)
            self._struct_cache[fmt] = s
        size = s.size
        if size > header.len:
            self.inp.read(header.len)
            header.len = 0
            raise EndOfRecordException()
        buf = self.inp.read(size)
        if not buf:
            self.eof = 1
            raise EofException()
        header.len -= size
        val, = s.unpack(buf)
        if isinstance(val, bytes):
            return val.decode("ascii")
        return val

    def readAndUnpackDirect(self, fmt):
        cdef object s = self._struct_cache.get(fmt)
        cdef bytes buf
        cdef object val
        if s is None:
            s = struct.Struct(self.endian + fmt)
            self._struct_cache[fmt] = s
        buf = self.inp.read(s.size)
        if not buf:
            self.eof = 1
            raise EofException()
        val, = s.unpack(buf)
        return val

    def readField(self, header, stdfFmt):
        return self.readAndUnpack(header, packFormatMap[stdfFmt])

    def readFieldDirect(self, stdfFmt):
        return self.readAndUnpackDirect(packFormatMap[stdfFmt])

    def readCn(self, header):
        cdef int slen
        cdef bytes buf
        if header.len == 0:
            raise EndOfRecordException()
        slen = self.readField(header, "U1")
        if slen > header.len:
            self.inp.read(header.len)
            header.len = 0
            raise EndOfRecordException()
        if slen == 0:
            return ""
        buf = self.inp.read(slen)
        if not buf:
            self.eof = 1
            raise EofException()
        header.len -= slen
        try:
            return buf.decode("ascii")
        except UnicodeDecodeError as e:
            print(e)
            result = chardet.detect(buf)
            encoding = result['encoding']
            print("The unknow format is: " + encoding)
            try:
                return buf.decode(encoding)
            except UnicodeDecodeError:
                return buf.decode("utf-8", errors="replace")

    def readBn(self, header):
        cdef int blen
        cdef object s
        cdef bytes buf
        blen = self.readField(header, "U1")
        if blen == 0:
            return []
        fmt = str(blen) + 'B'
        s = self._struct_cache.get(fmt)
        if s is None:
            s = struct.Struct(self.endian + fmt)
            self._struct_cache[fmt] = s
        if s.size > header.len:
            self.inp.read(header.len)
            header.len = 0
            raise EndOfRecordException()
        buf = self.inp.read(s.size)
        if not buf:
            self.eof = 1
            raise EofException()
        header.len -= s.size
        return list(s.unpack(buf))

    def readDn(self, header):
        cdef int dbitlen, dlen
        cdef object s
        cdef bytes buf
        dbitlen = self.readField(header, "U2")
        dlen = (dbitlen + 7) // 8
        if dlen == 0:
            return []
        fmt = str(dlen) + 'B'
        s = self._struct_cache.get(fmt)
        if s is None:
            s = struct.Struct(self.endian + fmt)
            self._struct_cache[fmt] = s
        if s.size > header.len:
            self.inp.read(header.len)
            header.len = 0
            raise EndOfRecordException()
        buf = self.inp.read(s.size)
        if not buf:
            self.eof = 1
            raise EofException()
        header.len -= s.size
        return list(s.unpack(buf))

    def readVn(self, header):
        cdef int vlen, fldtype, i
        vlen = self.readField(header, "U2")
        vn = []
        for i in range(vlen):
            fldtype = self.readField(header, "B1")
            if fldtype in self.vnMap:
                vn.append(self.vnMap[fldtype](header))
        return vn

    def readArray(self, header, indexValue, stdfFmt):
        cdef int count = int(indexValue)
        cdef object s
        cdef bytes buf
        cdef str fmt_char
        if count == 0:
            return []
        if stdfFmt == 'N1':
            return self.readArray(header, count // 2 + count % 2, 'U1')
        if stdfFmt in packFormatMap:
            fmt_char = packFormatMap[stdfFmt]
            fmt = str(count) + fmt_char
            s = self._struct_cache.get(fmt)
            if s is None:
                s = struct.Struct(self.endian + fmt)
                self._struct_cache[fmt] = s
            if s.size > header.len:
                self.inp.read(header.len)
                header.len = 0
                raise EndOfRecordException()
            buf = self.inp.read(s.size)
            if not buf:
                self.eof = 1
                raise EofException()
            header.len -= s.size
            result = s.unpack(buf)
            if fmt_char == 'c':
                return [v.decode('ascii') for v in result]
            return list(result)
        # Fallback for complex types
        arr = []
        for i in range(count):
            arr.append(self.unpackMap[stdfFmt](header, stdfFmt))
        return arr

    def readHeader(self):
        cdef object hdr = RecordHeader()
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
            return '<'
        else:
            return '>'

    def header(self, header): pass

    def parse_records(self, count=0, skipType=""):
        cdef int i = 0
        cdef object header, curRec, bakup, recType, recParser, fields
        cdef tuple key
        self.eof = 0

        if isinstance(skipType, str):
            skip_types = {skipType} if skipType else set()
        else:
            skip_types = set(skipType) if skipType else set()

        try:
            while self.eof == 0:
                header = self.readHeader()
                self.header(header)
                curRec = self.inp.read(header.len)
                bakup = self.inp
                self.inp = io.BytesIO(curRec)

                key = (header.typ, header.sub)
                recType = self.recordMap.get(key)
                if recType is not None:
                    recParser = self.recordParsers.get(key)
                    if recType.name in skip_types:
                        self.inp = bakup
                        continue

                    fields = recParser(self, header, [])
                    if len(fields) < len(recType.columnNames):
                        fields += [None] * (len(recType.columnNames) - len(fields))
                    self.send((recType, fields))
                    if header.len > 0:
                        print(
                            "Warning: Broken header. Unprocessed data left in record of type '%s'. Working around it."
                            % recType.__class__.__name__,
                            file=sys.stderr,
                        )
                        self.inp.read(header.len)
                        header.len = 0
                else:
                    self.inp.read(header.len)
                self.inp = bakup
                if count:
                    i += 1
                    if i >= count:
                        break
        except EofException:
            pass

    def _init_struct_cache(self):
        self._struct_cache = {}
        for fmt in packFormatMap.values():
            self._struct_cache[fmt] = struct.Struct(self.endian + fmt)

    def auto_detect_endian(self):
        if self.inp.tell() == 0:
            self.endian = '@'
            self._struct_cache = {}
            self.endian = self.__detectEndian()
            self._init_struct_cache()

    def parse(self, count=0, skipType=""):
        self.begin()
        try:
            self.auto_detect_endian()
            self.parse_records(count, skipType)
            self.complete()
        except Exception as exception:
            self.cancel(exception)
            raise

    # =================================================================
    # Optimized record parser: flat action list replaces lambda chain
    # =================================================================

    def getFieldParser(self, fieldType):
        """Return (type, ...) tuple instead of a nested lambda closure."""
        if fieldType.startswith("k"):
            fieldIndex, arrayFmt = re.match(
                r'k(\d+)([A-Z][a-z0-9]+)', fieldType
            ).groups()
            return ('array', int(fieldIndex), arrayFmt)
        else:
            parseFn = self.unpackMap[fieldType]
            return ('field', parseFn, fieldType)

    def createRecordParser(self, recType):
        """Build a parser that iterates a flat action list — no nested closures."""
        if (hasattr(recType, 'typ') and hasattr(recType, 'sub')
                and recType.typ == 15 and recType.sub == 30):
            return self.createStrRecordParser(recType)

        # Build flat list of actions: one per field, no nesting
        actions = []
        for stdfType in recType.fieldStdfTypes:
            actions.append(self.getFieldParser(stdfType))

        def recordParser(self, header, fields):
            for action in actions:
                try:
                    if action[0] == 'array':
                        _, fieldIndex, arrayFmt = action
                        fields.append(
                            self.readArray(header, fields[fieldIndex], arrayFmt)
                        )
                    else:
                        _, parseFn, stdfType = action
                        fields.append(parseFn(header, stdfType))
                except EndOfRecordException:
                    pass
            return fields

        return recordParser

    def createStrRecordParser(self, recType):
        """Custom parser for STR (Scan Test Record) with conditional fields."""
        fixed_types = [recType.fieldStdfTypes[i] for i in range(13)]
        remaining_types = recType.fieldStdfTypes[15:]

        def strParser(self, header, fields):
            # Read fixed fields (0-12)
            for ft in fixed_types:
                try:
                    fields.append(self.unpackMap[ft](header, ft))
                except EndOfRecordException:
                    break

            fmu_flg = fields[12] if len(fields) > 12 else 0

            # Conditional fields 13-14
            if fmu_flg > 0:
                try:
                    fields.append(self.readDn(header))
                except EndOfRecordException:
                    fields.append(None)
                try:
                    fields.append(self.readDn(header))
                except EndOfRecordException:
                    fields.append(None)
            else:
                fields.append(None)
                fields.append(None)

            # Remaining fields (15+)
            for field_type in remaining_types:
                try:
                    if field_type.startswith('k'):
                        m = re.match(r'k(\d+)([A-Z][a-z0-9]+)', field_type)
                        if m:
                            idx = int(m.group(1))
                            afmt = m.group(2)
                            fields.append(
                                self.readArray(header, fields[idx], afmt)
                            )
                        else:
                            fields.append(None)
                    else:
                        fields.append(
                            self.unpackMap[field_type](header, field_type)
                        )
                except EndOfRecordException:
                    fields.append(None)
            return fields

        return strParser

    def __init__(self, recTypes=V4.records, inp=sys.stdin, reopen_fn=None,
                 endian=None):
        DataSource.__init__(self, ['header'])
        self.eof = 1
        self.recTypes = set(recTypes)
        self.inp = inp
        self.reopen_fn = reopen_fn
        self.endian = endian
        self._struct_cache = {}

        self.recordMap = {
            (recType.typ, recType.sub): recType
            for recType in recTypes
        }

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
            "Vn": lambda header, fmt: self.readVn(header),
        }

        self.recordParsers = {
            (recType.typ, recType.sub): self.createRecordParser(recType)
            for recType in recTypes
        }

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
            13: lambda header: self.readField(header, "U1"),
        }
