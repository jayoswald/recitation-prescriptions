#!/usr/bin/env python3
import argparse
import tempfile
import os
import csv
import subprocess
import multiprocessing

def main():
    parser = argparse.ArgumentParser(description = 'todo.')
    parser.add_argument('--rubric', nargs='+', action='append',
                        help='rubric item numbers to use.')
    parser.add_argument('--evaluations', required=True,
                        help='path to Gradescope csv file')
    parser.add_argument('--quiz', required=True, 
                        help='name of assignment, e.g. "Quiz 1"')
    args = parser.parse_args()
    
    # Reads the Gradescope evaluation file.
    evaluations = read_evaluations(args.evaluations)

    # Stores all html files in a temporary directory.
    temp_dir = tempfile.TemporaryDirectory()
    html_files = []
    for s in evaluations.students:
        html = create_student_html(args, s, temp_dir.name)
        if html:
            html_files.append(html)

    # Converts all html files to PDFs and then combine into a single document.
    p = multiprocessing.Pool(16)
    pdfs = p.starmap(html2pdf, [(f, temp_dir.name) for f in html_files])
    cmd = 'gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile={}'
    output_path = '{}-prescriptions.pdf'.format(args.quiz.replace(' ', ''))
    cmd.format(output_path).split()
    subprocess.call(cmd.format(output_path).split() + pdfs)

    # Generate a stand alone blank prescription.
    blank = student('', '', 'missedquiz')
    blank.scores = [True for _ in evaluations.students[0].scores]
    html = create_student_html(args, blank, temp_dir.name)
    pdf =  html2pdf(html, '.')

    temp_dir.cleanup()


def html2pdf(f, temp):
    outpdf = os.path.join(temp, os.path.basename(f))[:-4] + 'pdf'
    cmd = 'xvfb-run -a wkhtmltopdf -s Letter'.split() + [f, outpdf]
    subprocess.call(cmd, stdout = subprocess.DEVNULL)
    return outpdf


def create_student_html(args, student, temp_dir):
    # 1-indexed list of rubric items to check (parsed from command line).
    rubric_items = [int(x[0]) for x in args.rubric]
    missed_rubrics = [r for r in args.rubric if student.scores[int(r[0])-1]]
    if not missed_rubrics:
        return None

    output_path = os.path.join(temp_dir, str(student.sid) + '.html')
    out = open(output_path, 'w')
    out.write(html_head)
    if student.sid == 'missedquiz':
        out.write(html_name.format(' ', args.quiz, ' '))
    else:
        out.write(html_name.format(' '.join(student.name), args.quiz, student.sid))
    # Loop over all rubrics, but write invisible rows if not incorrect.
    for r in args.rubric:
        problems = r[1:]
        ncols = 2*len(problems)-1
        column_styles = ncols * '<col style="width:50px">'

        # First writes out a blank row.
        cells = ['<tr>', '<td></td>']
        for _ in problems:
            cells += ['<td class="tg-invisible-box"></td>']
            cells += ['<td></td>']
        cells[-1] = '</tr>'
        out.write(html_boxes.format(column_styles, ''.join(cells)))

        # Now write out a row w/ the problem numbers.
        incorrect = student.scores[int(r[0])-1]
        title = 'Concept ' + str(r[0])
        cells = ['<tr>', '<td>{}</td>'.format(title)]
        for p in problems:
            if incorrect:
                cells.append('<td class="tg-box">{}</td>'.format(p))
            else:
                cells.append('<td class="tg-disabled-box">X</td>')
            cells.append('<td></td>')
        cells[-1] = '</tr>'
        out.write(html_boxes.format(column_styles, ''.join(cells)))
    return output_path


class evaluations:
    def __init__(self):
        ''' Rubric items are the names of each of the rubrics extracted from
        the header row of the csv file. '''
        self.rubric_items = []
        self.students = []


class student:
    ''' Student information containing first, last and student id .'''
    def __init__(self, first, last, sid):
        self.name = (first, last)
        self.sid = sid

def read_evaluations(p):
    evals = evaluations()
    try:
        with open(p) as fid:
            reader = csv.reader(fid)
            header = next(reader)

            i = header.index('Submission Time') + 1
            j = header.index('Adjustment')
            evals.rubric_items = header[i:j] 
            for row in reader:
                # First line w/ empty submission ID means end of student data.
                if not row:
                    break
                try:
                    sid = int(row[header.index('SID')])
                    first = row[header.index('First Name')]
                    last = row[header.index('Last Name')]
                    s = student(first, last, sid)
                    s.scores = [x.lower() == 'true' for x in row[i:j]]
                except:
                    print('Skipping invalid row')
                    print(row)
                else:
                    evals.students.append(s)
    except IOError:
        print('Could not open evaluation file:', p)

    evals.students.sort(key = lambda s: s.name[1] + s.name[0])
    return evals


# https://html5-tutorial.net/try.html#pre0
html_head = \
'''<style type="text/css">
@media print {@page {margin:0; } body {margin: 1.6cm; }}
.tg  {border-collapse:collapse;border-spacing:0;}
.tg td{font-family:Arial, sans-serif;font-size:14px;padding:0px;border-style:solid;border-width:0px;overflow:hidden;word-break:normal;border-color:black; height:25px}
.tg .tg-box{text-align:left;vertical-align:bottom; height:100px; width:100px; border-width:2px; padding:5px}
.tg .tg-invisible-box{text-align:left;vertical-align:bottom; height:100px; width:100px; border-width:0px; padding:5px}
.tg .tg-disabled-box{text-align:left;vertical-align:bottom; background:#CCCCCC; font-size:80px; height:100px; width:100px; border-width:2px; padding:5px; text-align: center;}
.tg .tg-name{text-align:left;vertical-align:middle; font-size:18px}
.tg .tg-studentid{text-align:right;vertical-align:middle; font-size:18px}
.tg .tg-title{text-align:center;vertical-align:middle; font-size:18px}
</style>'''

html_name = '''<table class="tg" width=100%>
<col style="width:33%">
<col style="width:33%">
<col style="width:34%"><tr>
 <td class="tg-name">{}</td>
 <td class="tg-title">{} prescription</td>
 <td class="tg-studentid">{}</td>
</tr></table>'''

html_boxes = '<table class="tg"><col style="width:40%">{}{}</table>'

if __name__ == '__main__':
    main()
