# -*- coding:utf-8 -*-
"""
Standalone analysis functions for STDF data processing.
Extracted from STDF_Reader_GUI for use in CLI and other contexts.
No GUI (PyQt5) dependencies.
"""

import numpy as np
import pandas as pd
import datetime
import time
import logging
import csv
import os

import xlsxwriter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pypdf import PdfWriter, PdfReader

from src.Backend import Backend


class StdfData:
    """Container for loaded and processed STDF CSV data."""

    def __init__(self):
        self.df_csv = pd.DataFrame()
        self.test_info_list = []
        self.list_of_test_numbers = []
        self.list_of_test_numbers_string = []
        self.tnumber_list = []
        self.tname_list = []
        self.sdr_parse = []
        self.number_of_sites = 0
        self.file_path = ''  # first file path, used for output naming


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_csv_data(file_paths, cherry_pick_sites=None):
    """
    Load and merge CSV files produced by STDF-to-CSV conversion.

    Args:
        file_paths: list of CSV file paths
        cherry_pick_sites: optional list of site numbers (int), one per file

    Returns:
        StdfData with all loaded and cleaned data
    """
    data = StdfData()
    data.file_path = file_paths[0] if file_paths else ''

    df_csv = pd.DataFrame()
    test_info_list = []

    for i, filename in enumerate(file_paths):
        csv_data = pd.read_csv(filename, header=[0, 1, 2, 3, 4])

        # Extract test metadata from multi-level columns
        tmp_pd = csv_data.columns
        single_columns = tmp_pd.get_level_values(4).values.tolist()[:16]
        tnumber_list = tmp_pd.get_level_values(4).values.tolist()[16:]
        tname_list = tmp_pd.get_level_values(0).values.tolist()[16:]
        test_info_list = list(set(tmp_pd.values.tolist()[16:]).union(test_info_list))
        list_of_test_numbers_string = [j + ' - ' + k for k, j in zip(tname_list, tnumber_list)]

        # Flatten multi-level columns to single level
        single_columns = single_columns + list_of_test_numbers_string
        csv_data.columns = single_columns

        # Cherry pick specific site per file
        if cherry_pick_sites is not None:
            if len(file_paths) != len(cherry_pick_sites):
                raise ValueError(
                    f"File count ({len(file_paths)}) mismatch with site list ({len(cherry_pick_sites)})")
            site_index = int(cherry_pick_sites[i])
            csv_data = csv_data[csv_data['SITE_NUM'].isin([site_index])].copy()

        if df_csv.empty:
            df_csv = csv_data.copy()
        else:
            df_csv = pd.concat([df_csv, csv_data], sort=False, join='outer', ignore_index=True)

    # Process the merged data
    tmp_pd = df_csv.columns
    data.test_info_list = test_info_list
    data.list_of_test_numbers_string = tmp_pd.values.tolist()[16:]

    if df_csv.shape[0] > 0:
        # Data cleaning: remove (F) and (A) markers
        df_csv.replace(r'\((F|A)\)', '', regex=True, inplace=True)
        df_csv.iloc[:, 16:] = df_csv.iloc[:, 16:].astype('float')
        df_csv['X_COORD'] = df_csv['X_COORD'].astype(int)
        df_csv['Y_COORD'] = df_csv['Y_COORD'].astype(int)
        df_csv['SOFT_BIN'] = df_csv['SOFT_BIN'].astype(int)
        df_csv['HARD_BIN'] = df_csv['HARD_BIN'].astype(int)
        df_csv['LOT_ID'].fillna(value=9999, inplace=True)
        df_csv['WAFER_ID'].fillna(value=9999, inplace=True)
        df_csv['PART_ID'].fillna(value=9999, inplace=True)
        df_csv['BIN_DESC'].fillna(value='NA', inplace=True)

        # Extract test name and number lists
        data.list_of_test_numbers = [x.split(" - ") for x in data.list_of_test_numbers_string]
        data.tnumber_list = [x[0] for x in data.list_of_test_numbers]
        data.tname_list = [x[1] for x in data.list_of_test_numbers]

        # Get site info
        data.sdr_parse = df_csv['SITE_NUM'].unique()
        data.number_of_sites = len(data.sdr_parse)
    else:
        raise ValueError("Empty data in loaded file(s)")

    data.df_csv = df_csv
    return data


# ---------------------------------------------------------------------------
# Summary / Statistics
# ---------------------------------------------------------------------------

def get_summary_table(df_csv, test_info_list, num_of_sites, test_list,
                      sdr_parse, merge_sites=True, output_them_both=True,
                      print_data=False, progress_cb=None):
    """
    Get summary results table for all sites / each site in each test.
    Standalone version of Application.get_summary_table().

    Args:
        df_csv: DataFrame with test data
        test_info_list: list of test info tuples
        num_of_sites: number of test sites
        test_list: list of [test_number, test_name] pairs
        sdr_parse: array of site numbers
        merge_sites: if True, include merged ALL-sites row
        output_them_both: if True, include both merged and per-site rows
        print_data: if True, append raw loop data columns
        progress_cb: optional callable(int) for progress (0-100)

    Returns:
        pd.DataFrame with summary statistics
    """
    parameters = ['TNum', 'Site', 'Units', 'Runs', 'Fails', 'LowLimit', 'HiLimit',
                  'Min', 'Mean', 'Max', 'Range', 'STD', 'Cp', 'Cpl', 'Cpu', 'Cpk']

    summary_results = []

    # Extract test data per site for later usage
    site_test_data_dic = {}
    if (not merge_sites) or output_them_both:
        for j in sdr_parse:
            site_test_data_dic[str(j)] = df_csv[df_csv.SITE_NUM == j]

    for i in range(0, len(test_list)):
        # Merge all sites data
        all_data_array = df_csv.iloc[:, i + 16].to_numpy('float64')
        try:
            all_data_array = all_data_array[~np.isnan(all_data_array)]
        except Exception as e:
            print(e)
        if float('-inf') in all_data_array or float('inf') in all_data_array:
            logging.warning("Found inf/-inf in data log!!!")
            print("Warning: Found inf/-inf in data log!!!")
            all_data_array = all_data_array[~np.isinf(all_data_array)]

        units = Backend.get_units(test_info_list, test_list[i], num_of_sites)
        minimum = Backend.get_plot_min(test_info_list, test_list[i], num_of_sites)
        maximum = Backend.get_plot_max(test_info_list, test_list[i], num_of_sites)

        if merge_sites or output_them_both:
            summary_results.append([test_list[i][0]] + Backend.site_array(
                all_data_array, minimum, maximum, 'ALL', units))
        if (not merge_sites) or output_them_both:
            for j in sdr_parse:
                site_test_data_df = site_test_data_dic[str(j)]
                site_test_data = site_test_data_df.iloc[:, i + 16].to_numpy('float64')
                site_test_data = site_test_data[~np.isnan(site_test_data)]
                site_test_data = site_test_data[~np.isinf(site_test_data)]
                if print_data:
                    summary_results.append([test_list[i][0]] + Backend.site_array(
                        site_test_data, minimum, maximum, j, units) + site_test_data.tolist())
                else:
                    summary_results.append([test_list[i][0]] + Backend.site_array(
                        site_test_data, minimum, maximum, j, units))

        if progress_cb:
            progress_cb(20 + int(i / len(test_list) * 50))

    test_names = []
    for i in range(0, len(test_list)):
        if merge_sites or output_them_both:
            test_names.append(test_list[i][1])
        if (not merge_sites) or output_them_both:
            for j in range(0, len(sdr_parse)):
                test_names.append(test_list[i][1])

        if progress_cb:
            progress_cb(70 + int(i / len(test_list) * 10))

    if print_data:
        max_length = max(len(sublist) for sublist in summary_results)
        for i in range(0, max_length - 16):
            parameters += ['LOOP' + str(i)]

    table = pd.DataFrame(summary_results, columns=parameters, index=test_names)

    if progress_cb:
        progress_cb(80)

    return table


def make_data_summary(data, progress_cb=None):
    """Generate data summary table. Returns pd.DataFrame."""
    print_data_flag = '_LOOP' in data.file_path.upper()
    if progress_cb:
        progress_cb(0)
    table = get_summary_table(
        data.df_csv, data.test_info_list, data.number_of_sites,
        data.list_of_test_numbers, data.sdr_parse,
        merge_sites=True, output_them_both=True,
        print_data=print_data_flag, progress_cb=progress_cb)
    if progress_cb:
        progress_cb(80)
    return table


def _list_duplicates_of(seq, item, start_index):
    """Find first duplicate pair of item in seq."""
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
            if len(locs) == 2:
                break
    return locs


def make_duplicate_num_report(tnumber_list, tname_list):
    """
    Check for duplicate test numbers with different names.

    Returns:
        tuple: (report_df, list_of_duplicates)
    """
    list_of_duplicate_test_numbers = []
    if len(tnumber_list) != len(set(tnumber_list)):
        for i in range(len(tnumber_list)):
            dup_list = _list_duplicates_of(tnumber_list[i:], tnumber_list[i], i)
            if len(dup_list) > 1:
                list_of_duplicate_test_numbers.append(
                    [tnumber_list[dup_list[0]], tname_list[i], tname_list[dup_list[1]]])

    log_csv = pd.DataFrame({'name': ['不错哟 !!!']})
    if len(list_of_duplicate_test_numbers) > 0:
        log_csv = pd.DataFrame(list_of_duplicate_test_numbers,
                               columns=['Test Number', 'Test Name', 'Test Name'])
    return log_csv, list_of_duplicate_test_numbers


def make_bin_summary(df_csv):
    """Generate bin summary tables per lot/wafer. Returns list of DataFrames."""
    all_bin_summary_list = []
    lot_id_list = df_csv['LOT_ID'].unique()
    coord_x_list = df_csv['X_COORD'].unique().tolist()
    coord_y_list = df_csv['Y_COORD'].unique().tolist()

    for lot_id in lot_id_list:
        single_lot_df = df_csv[df_csv['LOT_ID'].isin([lot_id])]
        wafer_id_list = single_lot_df['WAFER_ID'].unique()
        for wafer_id in wafer_id_list:
            single_wafer_df = single_lot_df[single_lot_df['WAFER_ID'].isin([wafer_id])]
            die_id = str(single_wafer_df['LOT_ID'].iloc[0]) + ' - ' + str(
                single_wafer_df['WAFER_ID'].iloc[0])

            if not ((len(coord_x_list) == 1 and coord_x_list[0] == -32768) and
                    (len(coord_y_list) == 1 and coord_y_list[0] == -32768)):
                retest_die_df = single_wafer_df[single_wafer_df['RC'].isin(['Retest'])]
                retest_die_np = retest_die_df[['X_COORD', 'Y_COORD']].values
                if len(retest_die_np) > 0:
                    mask = (single_wafer_df.X_COORD.values == retest_die_np[:, None, 0]) & \
                           (single_wafer_df.Y_COORD.values == retest_die_np[:, None, 1]) & \
                           (single_wafer_df['RC'].isin(['First']).to_numpy())
                    single_wafer_df = single_wafer_df[~mask.any(axis=0)]

            bin_summary_pd = single_wafer_df.pivot_table(
                'PART_ID', index=['SOFT_BIN', 'BIN_DESC'],
                columns='SITE_NUM', aggfunc='count', margins=True, fill_value=0).copy()
            bin_summary_pd.index.rename([die_id, 'BIN_DESC'], inplace=True)
            bin_summary_pd["%Bin"] = (bin_summary_pd['All'] / bin_summary_pd['All'][:-1].sum()) * 100
            all_bin_summary_list.append(bin_summary_pd)

    return all_bin_summary_list


def make_wafer_map(df_csv):
    """Generate wafer map tables per lot/wafer/site. Returns nested list of DataFrames."""
    all_wafer_map_list = []
    lot_id_list = df_csv['LOT_ID'].unique()

    for lot_id in lot_id_list:
        single_lot_df = df_csv[df_csv['LOT_ID'].isin([lot_id])]
        wafer_id_list = single_lot_df['WAFER_ID'].unique()
        for wafer_id in wafer_id_list:
            tmp_wafer_map_list = []
            single_wafer_df = single_lot_df[single_lot_df['WAFER_ID'].isin([wafer_id])]
            die_id = str(single_wafer_df['LOT_ID'].iloc[0]) + ' - ' + str(
                single_wafer_df['WAFER_ID'].iloc[0])
            wafer_map_df = single_wafer_df.pivot_table(
                values='SOFT_BIN', index='Y_COORD', columns='X_COORD',
                aggfunc=lambda x: int(tuple(x)[-1]))
            wafer_map_df.index.name = die_id
            wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
            tmp_wafer_map_list.append(wafer_map_df)

            site_num_list = single_wafer_df['SITE_NUM'].unique()
            for site_num in site_num_list:
                single_site_df = single_wafer_df[single_wafer_df['SITE_NUM'].isin([site_num])]
                site_id = die_id + ' - Site ' + str(site_num)
                single_site_wafer_map_df = single_site_df.pivot_table(
                    values='SOFT_BIN', index='Y_COORD', columns='X_COORD',
                    aggfunc=lambda x: int(tuple(x)[-1]))
                single_site_wafer_map_df.index.name = site_id
                single_site_wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
                tmp_wafer_map_list.append(single_site_wafer_map_df)
            all_wafer_map_list.append(tmp_wafer_map_list)

    return all_wafer_map_list


# ---------------------------------------------------------------------------
# Report Generation (XLSX)
# ---------------------------------------------------------------------------

def generate_analysis_report(data, output_path=None, progress_cb=None):
    """
    Generate comprehensive XLSX analysis report.

    Args:
        data: StdfData object
        output_path: output xlsx path (auto-generated if None)
        progress_cb: optional callable(int) for progress (0-100)
    """
    if progress_cb:
        progress_cb(0)

    now_time = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    if output_path is None:
        base = data.file_path
        if base.endswith('_csv_log.csv'):
            base = base[:-12]
        output_path = base + "_analysis_report_" + now_time + ".xlsx"

    print(f"  Generating: {os.path.basename(output_path)}")

    startt = time.time()
    data_summary = make_data_summary(data, progress_cb)
    print(f'  Data summary time: {time.time() - startt:.2f}s')

    startt = time.time()
    duplicate_number_report, _ = make_duplicate_num_report(data.tnumber_list, data.tname_list)
    if progress_cb:
        progress_cb(82)
    print(f'  Duplicate number check time: {time.time() - startt:.2f}s')

    startt = time.time()
    bin_summary_list = make_bin_summary(data.df_csv)
    if progress_cb:
        progress_cb(85)
    print(f'  Bin summary time: {time.time() - startt:.2f}s')

    startt = time.time()
    wafer_map_list = make_wafer_map(data.df_csv)
    if progress_cb:
        progress_cb(88)
    print(f'  Wafer map time: {time.time() - startt:.2f}s')

    startt = time.time()
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            format_2XXX = workbook.add_format({'bg_color': '#FF0000'})
            format_3XXX = workbook.add_format({'bg_color': '#FF6600'})
            format_4XXX = workbook.add_format({'bg_color': '#FFC7CE'})
            format_6XXX = workbook.add_format({'bg_color': '#FFEB9C'})
            format_9XXX = workbook.add_format({'bg_color': '#9C6500'})
            format_1XXX = workbook.add_format({'bg_color': '#008000'})
            format_7XXX = workbook.add_format({'bg_color': '#C6EFCE'})
            format1 = workbook.add_format({'align': 'left'})

            # Data Statistics sheet
            data_summary.to_excel(writer, sheet_name='Data Statistics')
            row_table, column_table = data_summary.shape
            worksheet = writer.sheets['Data Statistics']
            worksheet.freeze_panes(1, 0)
            worksheet.set_column('A:A', 25, format1)
            worksheet.conditional_format(1, 13, row_table, 13,
                                         {'type': 'cell', 'criteria': '<',
                                          'value': 3.3, 'format': format_4XXX})
            worksheet.conditional_format(1, 14, row_table, 14,
                                         {'type': 'cell', 'criteria': '<',
                                          'value': 1.33, 'format': format_4XXX})
            worksheet.conditional_format(1, 15, row_table, 15,
                                         {'type': 'cell', 'criteria': '<',
                                          'value': 1.33, 'format': format_4XXX})
            worksheet.conditional_format(1, 16, row_table, 16,
                                         {'type': 'cell', 'criteria': '<',
                                          'value': 1.33, 'format': format_4XXX})
            worksheet.autofilter(0, 0, row_table, column_table)
            if progress_cb:
                progress_cb(89)

            # Duplicate Test Number sheet
            duplicate_number_report.to_excel(writer, sheet_name='Duplicate Test Number')
            if progress_cb:
                progress_cb(90)

            # Bin Summary sheet
            start_row = 0
            for i in range(len(bin_summary_list)):
                bin_summary = bin_summary_list[i]
                row_table, column_table = bin_summary.shape
                bin_summary.to_excel(writer, sheet_name='Bin Summary', startrow=start_row)
                worksheet = writer.sheets['Bin Summary']
                for bin_range, fmt in [
                    ((1, 1999), format_1XXX), ((2000, 2999), format_2XXX),
                    ((3000, 3999), format_3XXX), ((4000, 4999), format_4XXX),
                    ((6000, 6999), format_6XXX), ((7000, 7999), format_7XXX),
                    ((9000, 9999), format_9XXX)]:
                    worksheet.conditional_format(
                        start_row + 1, 0, start_row + row_table, 0,
                        {'type': 'cell', 'criteria': 'between',
                         'minimum': bin_range[0], 'maximum': bin_range[1], 'format': fmt})
                if progress_cb:
                    progress_cb(90 + int(i / max(len(bin_summary_list), 1) * 5))
                start_row = start_row + row_table + 3

            # Wafer Map sheet
            start_row = 0
            for i in range(len(wafer_map_list)):
                start_column = 0
                for j in range(len(wafer_map_list[i])):
                    wafer_map = wafer_map_list[i][j]
                    row_table, column_table = wafer_map.shape
                    wafer_map.to_excel(writer, sheet_name='Wafer Map',
                                       startrow=start_row, startcol=start_column)
                    worksheet = writer.sheets['Wafer Map']
                    for bin_range, fmt in [
                        ((1, 1999), format_1XXX), ((2000, 2999), format_2XXX),
                        ((3000, 3999), format_3XXX), ((4000, 4999), format_4XXX),
                        ((6000, 6999), format_6XXX), ((7000, 7999), format_7XXX),
                        ((9000, 9999), format_9XXX)]:
                        worksheet.conditional_format(
                            start_row + 1, start_column + 1,
                            start_row + row_table, start_column + column_table,
                            {'type': 'cell', 'criteria': 'between',
                             'minimum': bin_range[0], 'maximum': bin_range[1], 'format': fmt})
                    start_column = start_column + column_table + 3
                    if progress_cb:
                        progress_cb(95 + int(i / max(len(bin_summary_list), 1) * 5))
                start_row = start_row + row_table + 3

            if progress_cb:
                progress_cb(100)
            print(f'  XLSX generation time: {time.time() - startt:.2f}s')
            print(f"  ✓ Written: {os.path.basename(output_path)}")

    except xlsxwriter.exceptions.FileCreateError:
        print(f"  ✗ Error: Please close {os.path.basename(output_path)} and try again")
        raise


# ---------------------------------------------------------------------------
# Correlation Analysis
# ---------------------------------------------------------------------------

def make_correlation_table(data, progress_cb=None):
    """
    Generate correlation table comparing means across multiple STDF files.

    Returns:
        tuple: (correlation_df, file_list)
    """
    parameters = ['Site', 'Units', 'LowLimit', 'HiLimit']
    file_list = data.df_csv['FILE_NAM'].unique()
    correlation_df = pd.DataFrame()

    if len(file_list) <= 1:
        raise ValueError("Need 2 or more STDF files in the CSV for correlation analysis")

    table_list = []
    for file_name in file_list:
        tmp_df = data.df_csv[data.df_csv.FILE_NAM == file_name]
        table_list.append(get_summary_table(
            tmp_df, data.test_info_list, data.number_of_sites,
            data.list_of_test_numbers, data.sdr_parse,
            merge_sites=False, output_them_both=True, print_data=False,
            progress_cb=None))

    hiLimit_df = table_list[0].HiLimit.replace('n/a', 0).astype(float)
    lowlimit_df = table_list[0].LowLimit.replace('n/a', 0).astype(float)

    correlation_df = pd.concat([
        table_list[0].Site, table_list[0].Units,
        table_list[0].LowLimit, table_list[0].HiLimit], axis=1)

    for i in range(len(file_list)):
        correlation_df = pd.concat(
            [correlation_df, table_list[i].Mean.astype('float')], axis=1)
        parameters = parameters + ['Mean(' + file_list[i] + ')']

    correlation_df.columns = parameters
    parameters = parameters + [
        'Mean Diff(max - min)',
        'Mean Diff Over Limit(dif/delta limit)',
        'Mean Diff Over Base(dif/first file data)']

    mean_delta = correlation_df.iloc[:, 5] - correlation_df.iloc[:, 4]
    mean_delta_over_limit = mean_delta / (hiLimit_df - lowlimit_df)
    mean_delta_over_base = mean_delta / table_list[0].Mean.astype(float)
    correlation_df = pd.concat(
        [correlation_df, mean_delta, mean_delta_over_limit, mean_delta_over_base], axis=1)
    correlation_df.columns = parameters

    return correlation_df, file_list


def make_wafer_map_cmp(df_csv, progress_cb=None):
    """Compare wafer maps between first two files. Returns [result_df, axis_df]."""
    all_wafer_map_list = []
    file_list = df_csv['FILE_NAM'].unique()

    for file_name in file_list:
        single_file_df = df_csv[df_csv['FILE_NAM'].isin([file_name])]
        lot_id_list = single_file_df['LOT_ID'].unique()
        for lot_id in lot_id_list:
            single_lot_df = single_file_df[single_file_df['LOT_ID'].isin([lot_id])]
            wafer_id_list = single_lot_df['WAFER_ID'].unique()
            for wafer_id in wafer_id_list:
                single_wafer_df = single_lot_df[single_lot_df['WAFER_ID'].isin([wafer_id])]
                die_id = str(single_wafer_df['LOT_ID'].iloc[0]) + ' - ' + str(
                    single_wafer_df['WAFER_ID'].iloc[0])
                wafer_map_df = single_wafer_df.pivot_table(
                    values='SOFT_BIN', index='Y_COORD', columns='X_COORD',
                    aggfunc=lambda x: int(tuple(x)[-1]))
                wafer_map_df.index.name = die_id
                wafer_map_df.sort_index(axis=0, ascending=False, inplace=True)
                all_wafer_map_list.append([wafer_map_df])

    cmp_result_list = []
    if len(all_wafer_map_list) >= 2:
        base_df = all_wafer_map_list[0][0].fillna(value='')
        cmp_df = all_wafer_map_list[1][0].fillna(value='')
        df1_r, df1_c = base_df.shape
        df2_r, df2_c = cmp_df.shape

        if (df1_r != df2_r) or (df1_c != df2_c):
            result_df = pd.DataFrame({'name': ['Dimension Mismatch of First 2 Wafer Map !!!']})
            axis_df = pd.DataFrame({'name': ['这也没有 !!!']})
        else:
            result_df = base_df.copy()
            row_names = result_df.index.values
            col_names = result_df.columns.values
            axis_dic = {'Axis': [], 'Base Bin Number': [], 'CMP Bin Number': []}
            for i in range(df1_c):
                result_df.iloc[:, i] = np.where(
                    base_df.iloc[:, i] == cmp_df.iloc[:, i],
                    base_df.iloc[:, i],
                    base_df.iloc[:, i].astype(str) + '-->' + cmp_df.iloc[:, i].astype(str))
                row_name = row_names[np.where(base_df.iloc[:, i] != cmp_df.iloc[:, i])]
                col_name = int(col_names[i])
                for j in row_name:
                    axis_dic['Axis'].append([col_name, int(j)])
                    axis_dic['Base Bin Number'].append(base_df.loc[j, col_name])
                    axis_dic['CMP Bin Number'].append(cmp_df.loc[j, col_name])
            axis_df = pd.DataFrame.from_dict(axis_dic, orient='index').T
        cmp_result_list = [result_df, axis_df]

    return cmp_result_list


def generate_correlation_report(data, output_path=None, progress_cb=None):
    """Generate correlation report XLSX comparing 2+ STDF files."""
    now_time = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    if output_path is None:
        base = data.file_path
        if base.endswith('_csv_log.csv'):
            base = base[:-12]
        output_path = base + "_correlation_report_" + now_time + ".xlsx"

    print(f"  Generating: {os.path.basename(output_path)}")

    correlation_table, file_list = make_correlation_table(data, progress_cb)
    wafer_map_cmp_list = make_wafer_map_cmp(data.df_csv, progress_cb)
    meanShiftPivot_df = correlation_table.pivot_table(
        values='Mean Diff(max - min)', index=correlation_table.index,
        columns='Site', aggfunc='mean')
    if progress_cb:
        progress_cb(95)

    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            format_4XXX = workbook.add_format({'bg_color': '#FFC7CE'})
            format1 = workbook.add_format({'align': 'left'})

            # Correlation table sheet
            correlation_table.to_excel(writer, sheet_name='2 STDF correlation table')
            row_table, column_table = correlation_table.shape
            worksheet = writer.sheets['2 STDF correlation table']
            worksheet.freeze_panes(1, 0)
            worksheet.set_column('A:A', 25, format1)
            worksheet.conditional_format(1, column_table - 1, row_table, column_table - 1,
                                         {'type': 'cell', 'criteria': '>=',
                                          'value': 0.05, 'format': format_4XXX})
            worksheet.conditional_format(1, column_table, row_table, column_table,
                                         {'type': 'cell', 'criteria': '>=',
                                          'value': 0.1, 'format': format_4XXX})
            for i in range(1, row_table):
                worksheet.conditional_format(i, 5, i, column_table - 3, {'type': '3_color_scale'})
            worksheet.write_string(row_table + 2, 0, 'Base: ' + file_list[0])
            worksheet.write_string(row_table + 3, 0, 'CMP: ' + file_list[1])
            worksheet.autofilter(0, 0, row_table, column_table)
            if progress_cb:
                progress_cb(97)

            # Wafer map compare sheet
            if wafer_map_cmp_list:
                wafer_map_cmp = wafer_map_cmp_list[0]
                bin_swap_table = wafer_map_cmp_list[1]
                wafer_map_cmp.to_excel(writer, sheet_name='2 STDF wafer map compare', startrow=0)
                row_table, column_table = wafer_map_cmp.shape
                bin_swap_table.to_excel(writer, sheet_name='2 STDF wafer map compare',
                                         startrow=row_table + 2)
                worksheet = writer.sheets['2 STDF wafer map compare']
                worksheet.conditional_format(1, 1, row_table, column_table,
                                             {'type': 'text', 'criteria': 'containing',
                                              'value': '-->', 'format': format_4XXX})

            # Mean shift sheet
            row_table, column_table = meanShiftPivot_df.shape
            meanShiftPivot_df.to_excel(writer, sheet_name='3 STDF mean shift')
            worksheet = writer.sheets['3 STDF mean shift']
            for i in range(column_table):
                worksheet.conditional_format(1, 1 + i, row_table, 1 + i,
                                             {'type': 'data_bar', 'data_bar_2010': True})
            chart = workbook.add_chart({'type': 'line'})
            chart.set_title({'name': 'Mean shift'})
            chart.set_x_axis({'name': 'Test Instance', 'position_axis': 'on_tick'})
            chart.set_y_axis({'name': 'Mean shift', 'position_axis': 'on_tick'})
            chart.set_style(10)
            for i in range(column_table):
                chart.add_series({
                    'name': ["3 STDF mean shift", 0, 1 + i],
                    'categories': ["3 STDF mean shift", 1, 0, row_table, 0],
                    'values': ["3 STDF mean shift", 1, 1 + i, row_table, 1 + i],
                })
            worksheet.insert_chart("D2", chart, {"x_offset": 25, "y_offset": 10})
            worksheet.set_column(0, column_table, 12)

        if progress_cb:
            progress_cb(100)
        print(f"  ✓ Written: {os.path.basename(output_path)}")

    except xlsxwriter.exceptions.FileCreateError:
        print(f"  ✗ Error: Please close {os.path.basename(output_path)} and try again")
        raise


def make_s2s_correlation_table(data, progress_cb=None):
    """Generate site-to-site correlation table. Returns pd.DataFrame."""
    correlation_df = pd.DataFrame()
    table = get_summary_table(
        data.df_csv, data.test_info_list, data.number_of_sites,
        data.list_of_test_numbers, data.sdr_parse,
        merge_sites=False, output_them_both=False, print_data=False,
        progress_cb=progress_cb)

    site_list = table.Site.unique()
    if len(site_list) <= 1:
        raise ValueError("Only 1 site data found — need 2+ sites for S2S correlation")

    correlation_df = pd.concat([
        table[table.Site == site_list[0]].LowLimit,
        table[table.Site == site_list[0]].HiLimit], axis=1)
    columns = ['LowLimit', 'HiLimit']

    for site in site_list:
        if site is not None:
            tmp = table[table.Site == site].Mean.astype('float')
            tmp = tmp[~tmp.index.duplicated()]
            correlation_df = correlation_df[~correlation_df.index.duplicated()]
            correlation_df = pd.concat([correlation_df, tmp], axis=1)
            columns = columns + ['Mean(site' + site + ')']

    mean_delta = correlation_df.iloc[:, 2:].max(axis=1) - correlation_df.iloc[:, 2:].min(axis=1)
    correlation_df = pd.concat([correlation_df, mean_delta], axis=1)
    columns = columns + ['Mean Delta(Max - Min)']

    hiLimit_df = correlation_df.HiLimit.replace('n/a', 0).astype(float)
    lowlimit_df = correlation_df.LowLimit.replace('n/a', 0).astype(float)
    mean_delta_over_limit = mean_delta / (hiLimit_df - lowlimit_df)
    correlation_df = pd.concat([correlation_df, mean_delta_over_limit], axis=1)
    columns = columns + ['Mean Delta Over Limit']

    correlation_df.columns = columns
    return correlation_df


def generate_s2s_correlation_report(data, output_path=None, progress_cb=None):
    """Generate site-to-site correlation report XLSX."""
    now_time = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    if output_path is None:
        output_path = data.file_path + "_s2s_correlation_table" + now_time + ".xlsx"

    print(f"  Generating: {os.path.basename(output_path)}")

    s2s_df = make_s2s_correlation_table(data, progress_cb)
    if progress_cb:
        progress_cb(95)

    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            format_4XXX = workbook.add_format({'bg_color': '#FFC7CE'})
            format1 = workbook.add_format({'align': 'left'})

            s2s_df.to_excel(writer, sheet_name='Site2Site correlation table')
            row_table, column_table = s2s_df.shape
            worksheet = writer.sheets['Site2Site correlation table']
            worksheet.conditional_format(1, column_table, row_table, column_table,
                                         {'type': 'cell', 'criteria': '>=',
                                          'value': 0.05, 'format': format_4XXX})
            worksheet.freeze_panes(1, 0)
            worksheet.set_column('A:A', 25, format1)
            for i in range(1, row_table):
                worksheet.conditional_format(i, 3, i, column_table - 2,
                                             {'type': '3_color_scale'})
            worksheet.autofilter(0, 0, row_table, column_table)

        if progress_cb:
            progress_cb(100)
        print(f"  ✓ Written: {os.path.basename(output_path)}")

    except xlsxwriter.exceptions.FileCreateError:
        print(f"  ✗ Error: Please close {os.path.basename(output_path)} and try again")
        raise

    return s2s_df


# ---------------------------------------------------------------------------
# Test Extraction and PDF
# ---------------------------------------------------------------------------

def extract_sub_csv(data, selected_tests, output_path=None):
    """
    Extract a sub-CSV containing only selected tests.

    Args:
        data: StdfData object
        selected_tests: list of test name strings (format: "TNUM - TNAME")
        output_path: output CSV path
    """
    if output_path is None:
        base = data.file_path
        if base.endswith('_csv_log.csv'):
            base = base[:-12]
        output_path = base + "_extract_tests.csv"

    tmp_df = data.df_csv.iloc[:, :16]

    if len(selected_tests) < 1:
        raise ValueError("Please select one or more tests")

    for test in selected_tests:
        if test in data.df_csv.columns:
            tmp_df = pd.concat([tmp_df, data.df_csv[test]], axis=1, sort=False, join='outer')
        else:
            print(f"  Warning: Test '{test}' not found in data, skipping")

    # Re-build multi-level columns
    tname_list = []
    tnumber_list = []
    hilimit_list = []
    lolimit_list = []
    unit_vect_nam_list = []
    tmplist = tmp_df.columns.values.tolist()

    for i in range(len(tmplist)):
        if len(str(tmplist[i]).split(' - ')) == 1:
            tname_list.append('')
            tnumber_list.append(str(tmplist[i]))
            hilimit_list.append('')
            lolimit_list.append('')
            unit_vect_nam_list.append('')
        else:
            tmp_tuple = str(tmplist[i]).split(' - ')
            low_lim = Backend.get_plot_min(data.test_info_list, tmp_tuple, 0)
            hi_lim = Backend.get_plot_max(data.test_info_list, tmp_tuple, 0)
            units = Backend.get_units(data.test_info_list, tmp_tuple, 0)
            if units.startswith('Unnamed'):
                units = ''
            tname_list.append(tmp_tuple[1])
            tnumber_list.append(tmp_tuple[0])
            hilimit_list.append(hi_lim)
            lolimit_list.append(low_lim)
            unit_vect_nam_list.append(units)

    tmp_df.columns = [tname_list, hilimit_list, lolimit_list, unit_vect_nam_list, tnumber_list]

    tmp_df.to_csv(output_path, index=False)
    print(f"  ✓ Written: {os.path.basename(output_path)}")


def generate_pdf_report(data, selected_tests, output_path=None,
                        limits_toggled=True, group_by_file=False, progress_cb=None):
    """
    Generate PDF report with trendline/histogram charts for selected tests.

    Args:
        data: StdfData object
        selected_tests: list of test name strings
        output_path: output PDF path
        limits_toggled: plot failure limits
        group_by_file: group trends by file instead of by site
        progress_cb: optional callable(int)
    """
    matplotlib.use('Agg')

    if output_path is None:
        output_path = data.file_path + "_results.pdf"

    if len(selected_tests) == 0:
        raise ValueError("No test instances selected")

    if progress_cb:
        progress_cb(0)

    pp = PdfWriter()

    site_test_data_dic = {}
    if group_by_file:
        file_list = data.df_csv['FILE_NAM'].unique()
        for j in file_list:
            site_test_data_dic[str(j)] = data.df_csv[data.df_csv.FILE_NAM == j]
        label_list = file_list
    else:
        for j in data.sdr_parse:
            site_test_data_dic[str(j)] = data.df_csv[data.df_csv.SITE_NUM == j]
        label_list = data.sdr_parse

    temp_path = output_path + "_temp"

    for i in range(len(selected_tests)):
        site_test_data_list = []
        for j in label_list:
            site_test_data = site_test_data_dic[str(j)][selected_tests[i]].to_numpy('float64')
            tmp_list = site_test_data[~np.isnan(site_test_data)].tolist()
            site_test_data_list.append(tmp_list)

        all_data_array = site_test_data_list
        pdfTemp = PdfPages(temp_path)
        plt.figure(figsize=(11, 8.5))
        pdfTemp.savefig(Backend.plot_everything_from_one_test(
            all_data_array, label_list, data.test_info_list, data.number_of_sites,
            selected_tests[i].split(' - '), limits_toggled, group_by_file))
        pdfTemp.close()
        pp.append(PdfReader(temp_path))

        if progress_cb:
            progress_cb(int((i + 1) / len(selected_tests) * 90))

        print(f"  {i + 1}/{len(selected_tests)} test results completed")
        plt.close()

    if os.path.exists(temp_path):
        os.remove(temp_path)

    pp.write(output_path)
    del pp
    if progress_cb:
        progress_cb(100)
    print(f"  ✓ Written: {os.path.basename(output_path)}")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def transpose_csv(input_path, output_path=None):
    """Transpose a CSV file (rows ↔ columns)."""
    if output_path is None:
        output_path = input_path + "_transposed.csv"

    a = zip(*csv.reader(open(input_path, "rt")))
    csv.writer(open(output_path, "wt"), lineterminator="\n").writerows(a)
    print(f"  ✓ Written: {os.path.basename(output_path)}")
