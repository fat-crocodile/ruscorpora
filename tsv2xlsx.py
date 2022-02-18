import sys
import xlsxwriter
import re

class WSwrapper:
    def __init__(self, ws):
        self.ws = ws
        self.line = 0
    def empty(self):
        return self.line == 0
    def append(self, data):
        for i, c in enumerate(data):
            if isinstance(c, (list, tuple)):
                if len(c) > 1:
                    self.ws.write_rich_string(self.line, i, *c)
                else:
                    self.ws.write(self.line, i, c[0])
            else:
                self.ws.write(self.line, i, c)
        self.line += 1


def insert_x_before_odd(data, x):
    for i, d in enumerate(data):
        if i % 2 == 1:
            yield x
        yield d


with open(sys.argv[1], 'r', encoding='utf-8') as f, xlsxwriter.Workbook(sys.argv[2]) as wb:
    worksheet = wb.add_worksheet()
    worksheet.set_column(1, 1, 50)
    worksheet.set_column(3, 4, 70)
    bold = wb.add_format({'bold': True})
    ws = WSwrapper(worksheet)

    header = True
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        if re.match("\w+=", line):
            if header:
                ws.append(line.split('=', 1))
        else:
            if header and not ws.empty():
                ws.append([])
            header = False
            parts = line.split('\t')

            # index w0 w1 ... wn title
            # all odd words are selected, all even are plain
            if len(parts) < 5 or len(parts) % 2 != 1:
                raise Exception("line %d: wrong format" % (i+1))

            index = parts[0]
            before = parts[1]
            word = parts[2]
            after = list(insert_x_before_odd(parts[3:-1], bold))
            title = parts[-1]

            ws.append([index, before, word, after, title])
