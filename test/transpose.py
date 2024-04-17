import csv
def transpose():
    a = zip(*csv.reader(open(r".\volt_GPU_site_8_0412.std.gz_csv_log.csv", "rt")))
    b = list(a)
    csv.writer(open(r".\volt_GPU_site_8_0412.std.gz_csv_log_transposed.csv", "wt"),lineterminator="\n").writerows(b)

if __name__ == '__main__':
    transpose()