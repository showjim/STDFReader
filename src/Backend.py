# -*- coding:utf-8 -*-
#####################
# BACKEND FUNCTIONS #
#####################
# FORKED FROM CMD ATE DATA READER
from abc import ABC
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from decimal import Decimal


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
        # table = table[0:17]
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
        parameters = ['Site', 'Units', 'Runs', 'Fails', 'LowLimit', 'HiLimit',
                      'Min', 'Mean', 'Max', 'Range', 'STD', 'Cp', 'Cpk']

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

        high_limit = maximum
        low_limit = minimum
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
            # cpl_result = 'n/a'
            # cpu_result = 'n/a'
            cpk_result = 'n/a'

        # The struggles of logarithmic data
        elif 'db' in units.lower():

            for i in range(0, len(site_data)):
                volt_data.append(Backend.db2v(site_data[i]))

            mean_result = Backend.v2db(np.mean(volt_data))
            standard_deviation = np.std(
                volt_data) * 100  # *100 for converting to %
            std_string = str('%.3E' % (Decimal(standard_deviation)))

            cp_result = float(Decimal(Backend.cp(volt_data, Backend.db2v(
                minimum), Backend.db2v(maximum))).quantize(Decimal('0.001')))
            # cpl_result = str(Decimal(Backend.cpl(
            #     volt_data, Backend.db2v(minimum))).quantize(Decimal('0.001')))
            # cpu_result = str(Decimal(Backend.cpu(
            #     volt_data, Backend.db2v(maximum))).quantize(Decimal('0.001')))
            cpk_result = float(Decimal(Backend.cpk(volt_data, Backend.db2v(
                minimum), Backend.db2v(maximum))).quantize(Decimal('0.001')))

        # Yummy linear data instead
        else:
            mean_result = np.mean(site_data)
            # try:
            std_string = str(
                Decimal(np.std(site_data)).quantize(Decimal('0.001')))
            cp_result = float(
                Decimal(Backend.cp(site_data, minimum, maximum)).quantize(Decimal('0.001')))
            # cpl_result = str(
            #     Decimal(Backend.cpu(site_data, minimum)).quantize(Decimal('0.001')))
            # cpu_result = str(
            #     Decimal(Backend.cpl(site_data, maximum)).quantize(Decimal('0.001')))
            cpk_result = float(
                Decimal(Backend.cpk(site_data, minimum, maximum)).quantize(Decimal('0.001')))
            # except decimal.InvalidOperation:
            #     print(type(minimum))
            #     print(minimum)
            #     print(maximum)
            #     os.system("pause")
            # raise UnexpectedSymbol(minimum, maximum)

        # Appending all the important results weow!
        site_results.append(str(site_number))
        site_results.append(units)
        site_results.append(str(len(site_data)))
        site_results.append(
            str(Backend.calculate_fails(site_data, minimum, maximum)))
        # try:
        if low_limit == 'n/a' or low_limit == None or low_limit == float('inf') or low_limit == float('-inf'):
            site_results.append(str(low_limit))
        else:
            site_results.append(str(Decimal(low_limit).quantize(Decimal('0.000001'))))
        if high_limit == 'n/a' or high_limit == None or high_limit == float('inf') or high_limit == float('-inf'):
            site_results.append(str(high_limit))
        else:
            site_results.append(str(Decimal(high_limit).quantize(Decimal('0.000001'))))
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
        # site_results.append(cpl_result)
        # site_results.append(cpu_result)
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
                expand = abs(maximum)
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
