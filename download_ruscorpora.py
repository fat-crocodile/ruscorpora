#!/usr/bin/env python

import sys
import time
import re
import argparse
import logging

import urllib.parse
import urllib.request



def main(argv):
    # arguments
    parser = argparse.ArgumentParser(description='Download samples from ruscorpora')
    parser.add_argument('--url', type=str, required=True,
                        help='https://processing.ruscorpora.ru/search.xml?<...query...>')
    parser.add_argument('-s', '--start', metavar="INDEX", type=int, default=1,
                        help='start from document INDEX')
    parser.add_argument('-n', metavar="N", type=int, default=float("inf"),
                        help='download samples from N documents')

    parser.add_argument('-o', '--output', metavar="FILE", type=str, default=None, help='write results to FILE')
    parser.add_argument('-l', '--log', metavar="FILE", type=str, default=None, help='write log to FILE')
    parser.add_argument('-a', '--append', action='store_true', help='append results to output FILE')
    parser.add_argument('-v', '--verbose', action='store_true', help='write verbose log')

    args = parser.parse_args(argv)

    # check arguments
    try:
        url = urllib.parse.urlsplit(args.url)
        if url.scheme not in ["http", "https"] or url.netloc != "processing.ruscorpora.ru" or url.path != "/search.xml":
            raise Exception()
    except:
        print("Incorrect url")
        return

    logging.basicConfig(
        filename=args.log,    # sys.stderr for None
        format="%(asctime)s %(message)s",
        level=logging.INFO if args.verbose else logging.WARN)

    # do work
    try:
        if args.output is not None:
            with open(args.output, "a" if args.append else "w", encoding="utf-8") as f:
                do_work(f, args.url, args.start, args.n)
        else:
            # utf-8?
            do_work(sys.stdout, args.url, args.start, args.n)
    except:
        logging.exception("error")


def do_work(f, url, start, n):
    urliter = gen_page_urls(url, start)
    first, u0 = next(urliter)

    text = download_page(u0)
    docs, cases = get_page_stat(text)

    f.write("url=%s\n" % url)
    f.write("docs=%d\n" % docs)
    f.write("cases=%d\n" % cases)

    if docs == 0:
        return

    for i, title, cases in gen_docs(first, u0, text, urliter, docs):
        if i < start:
            continue
        if i >= start + n:
            break
        for c in cases:
            f.write("%d\t%s\t%s\n" % (i, '\t'.join(c), title))

#
# generating urls and download pages
#

def gen_page_urls(url, start):
    res = urllib.parse.urlsplit(url)
    args = urllib.parse.parse_qs(res.query)
    args['dpp'] = '50'                  # higher values won't work
    args['p'] = str((start - 1) // 50)

    first = ((start - 1) // 50) * 50 + 1
    while True:
        query = urllib.parse.urlencode(args, doseq=True)
        yield first, urllib.parse.urlunsplit((res.scheme, res.netloc, res.path, query, ''))
        args['p'] = str(int(args['p']) + 1)
        first += 50


def download_page(url):
    for _ in range(10):
        try:
            logging.info("download %s", url)
            r = urllib.request.urlopen(url)
            data = r.read()
            return data.decode('utf-8')
        except:
            logging.exception("while downloading %s", url)
            time.sleep(1)
    raise Exception("can't download url " + url)


# this wrapper made for uniform processing of all pages: the first downloaded page and all next ones
def gen_docs(first, u0, text, urliter, docs):
    d = first - 1
    try:
        for title, examples in process_page(text):
            d += 1
            yield d, title, examples
    except Exception as e:
        raise Exception("while processing page %s :\n\t%s" % (u0, str(e)))
    for _, u in urliter:
        time.sleep(1)
        text = download_page(u)
        try:
            for title, examples in process_page(text):
                d += 1
                yield d, title, examples
        except Exception as e:
            raise Exception("while processing page %s :\n\t%s" % (u, str(e)))
        if d >= docs:
            break

#
# parsing html
#

def get_page_stat(text):
    docs, cases = 0, 0
    stat_number = re.compile(re.escape('<span class="stat-number">') + r"([\w\d\s]+)" + re.escape('</span>'), re.M)
    for x in stat_number.finditer(text):
        num = x.group(1).strip().rsplit(' ', 1)
        if len(num) != 2:
            continue
        if re.match("документ", num[1]) is not None:
            docs = int(re.sub('\s', '', num[0]))
        elif re.match("вхождени", num[1]) is not None:
            cases = int(re.sub('\s', '', num[0]))
    return docs, cases


def split_page_to_docs(text):
    doc_start = re.compile(r'<span\s+class="b\-doc\-expl"\s*explain="[\w\d=]+">\s*(.*?)\s*</span>', re.M)
    titles = [(x.start(), x.end(), x.group(1)) for x in doc_start.finditer(text)]
    if not titles:
        raise Exception("can't find any documents on the page")
    titles.append((len(text), 0, ''))
    for s, e in zip(titles[:-1], titles[1:]):
        yield spaces2sp(s[2]), text[s[1]: e[0]]


def split_doc_to_cases(doc):
    ex_end = re.compile(r'<span\s+class="doc">.*?</span>', re.M)
    res = ex_end.split(doc)[:-1]
    if not res:
        raise Exception("can't find any cases in the document html code")
    return res


def make_case(text):
    def selected(s):
        return s is not None and (s.endswith(" g-em") or " g-em " in s)
    word = re.compile(r'<span\s+class="b\-wrd\-expl([\s\w-]+)?"\s*explain="[\w\d=]+"\s*>(.*?)</span>', re.M)
    words = [(x.start(), x.end(), x.group(1), x.group(2)) for x in word.finditer(text)]

    if not words:
        raise Exception("can't find any words in the case html code")
    if not any(selected(w[2]) for w in words):
        raise Exception("can't find any selected words in the case html code")

    res = ['']
    for w, nxt in zip(words[:-1], words[1:]):
        if selected(w[2]):
            res.extend([w[3], ''])
        else:
            res[-1] += w[3]
        res[-1] += text[w[1]:nxt[0]]

    if selected(words[-1][2]):
        res.extend([words[-1][3], ''])
    else:
        res[-1] += words[-1][3]

    before = text[:words[0][0]]          # before
    res[0] = before.rsplit('>')[-1].lstrip() + res[0]
    after = text[words[-1][1]:]          # after
    res[-1] += after.split('<')[0].rstrip()
    return [spaces2sp(s) for s in res]


def process_doc(doc):
    for txt in split_doc_to_cases(doc):
        yield make_case(txt)


def process_page(text):
    for i, (title, body) in enumerate(split_page_to_docs(text)):
        try:
            yield title, list(process_doc(body))
        except Exception as e:
            raise Exception("while processing document %d:\n\t%s" % (i + 1, str(e)))


# Replaces all non-standard space symbols with usual space.
# Keeps tsv format from breaking apart.
def spaces2sp(s):
    return re.sub("\s+", ' ', s)


if __name__ == "__main__":
    main(sys.argv[1:])
    #main(
    #    ["--url=https://processing.ruscorpora.ru/search.xml?env=alpha&api=1.0&mycorp=&mysent=&mysize=&mysentsize=&dpp=&spp=&spd=&mydocsize=&mode=main&lang=ru&sort=i_grtagging&nodia=1&text=lexform&req=мешок",
    #     "--output=result.tsv",
    #     "-s", "123",
    #     "-n", "456",])

