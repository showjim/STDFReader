import csv
def transpose():
    a = zip(*csv.reader(open("test.csv", "rt")))
    csv.writer(open("transposed.csv", "wt")).writerows(a)