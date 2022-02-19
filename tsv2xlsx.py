import sys
import xlsxwriter
import re

def main(argv):
    if len(argv) != 2:
        print("usage: %s tsvfile xlsxfile" % sys.argv[0])
        return

    with open(argv[0], 'r', encoding='utf-8') as f, xlsxwriter.Workbook(argv[1]) as wb:
        bold = wb.add_format({'bold': True})
        ws_header = wb.add_worksheet()
        ws_body = wb.add_worksheet()
        ws_body.set_column(1, 1, 50)
        ws_body.set_column(3, 4, 70)
        ws_body.write_row(0, 0, ["index", "before", "word", "after", "title"], cell_format=bold)
        ws = WSwrapper(ws_body)
        ws.append([])
        wsh = WSwrapper(ws_header)
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if re.match("\w+=", line):
                wsh.append(line.split('=', 1))
            else:
                parts = line.split('\t')

                # index w0 w1 ... wn title
                # all odd words are selected, all even are plain
                if len(parts) < 5 or len(parts) % 2 != 1:
                    raise Exception("line %d: wrong format" % (i + 1))

                index = parts[0]
                before = parts[1]
                word = parts[2]
                after = list(insert_x_before_odd_and_skip_empty(parts[3:-1], bold))
                title = parts[-1]

                ws.append([index, before, word, after, title])


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
                elif len(c) == 1:
                    self.ws.write(self.line, i, c[0])
            else:
                self.ws.write(self.line, i, c)
        self.line += 1


def insert_x_before_odd_and_skip_empty(data, x):
    for i, d in enumerate(data):
        if not d:
            continue
        if i % 2 == 1:
            yield x
        yield d



if __name__ == "__main__":
    main(sys.argv[1:])
    #main(["result.tsv", "result.xlsx"])