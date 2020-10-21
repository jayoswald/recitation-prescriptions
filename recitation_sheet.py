#!/usr/bin/env python3
import argparse
import tempfile
import os
import re
import csv
import subprocess
import multiprocessing
import shutil

def main():
    parser = argparse.ArgumentParser(description = 'todo.')
    parser.add_argument('-c', nargs='+', action='append', dest='concepts',
                        help='rubric item numbers to use.')
    parser.add_argument('--evaluations', required=True,
                        help='path to Gradescope csv file')
    parser.add_argument('--quiz', required=True, 
                        help='name of assignment, e.g. "Quiz 1"')
    parser.add_argument('--grades', default=None, 
                        help='path to Gradescope grades')
    args = parser.parse_args()

    evaluations = assignment_evaluations(args.evaluations)

    if args.grades:
        gradescope = gradescope_grades(args.grades)
        output_path = '{}-results.pdf'.format(args.quiz.replace(' ', ''))
        all_students = gradescope.all_student_ids()
    else:
        gradescope = None
        output_path = '{}-prescriptions.pdf'.format(args.quiz.replace(' ', ''))
        all_students = evaluations.students.keys()

    prescriptions = []
    for sid in all_students:
        name = gradescope.student_name(sid)
        p = prescription(args.concepts, name, sid=sid, quiz_name=args.quiz)
        if sid in evaluations.students:
            p.set_required_concepts(evaluations.students[sid])
        if gradescope:
            p.update_from_gradescope(gradescope)
        prescriptions.append(p)


    name = args.quiz.replace(' ', '')
    write_prescriptions('prescriptions-' + name, prescriptions)
    prescriptions = [prescription(args.concepts, quiz_name = args.quiz)]
    write_prescriptions('template-' + name, prescriptions)


class student:
    ''' Student information containing first, last and student id .'''
    def __init__(self, first, last, sid):
        self.name = (first, last)
        self.sid = sid

class assignment_evaluations:
    ''' Class that reads the Gradescope assignment evaluation csv file. '''
    def __init__(self, path):
        try:
            reader = csv.reader(open(path))
            header = next(reader)
        except IOError:
            print('Could not open evaluation file:', p)
        i, j = header.index('Submission Time') + 1, header.index('Adjustment')
        self.rubric_names = header[i:j]
        self.students = {}
        for row in reader:
            try:
                s = student(row[header.index('First Name')],
                            row[header.index('Last Name')],
                            row[header.index('SID')])
                s.missed_concepts = [x.lower() == 'true' for x in row[i:j]]
                self.students[s.sid] = s
            except:
                if row and 'Rubric Type' not in row:
                    print('Skipping invalid row\n', row)


class gradescope_grades:
    ''' Reads the master Gradescope grades. '''
    def __init__(self, path):
        try:
            reader = csv.reader(open(path))
            self.header = next(reader)
        except IOError:
            print('Could not open evaluation file:', p)
        sid_column = self.header.index('SID')
        self.data = {row[sid_column]:row for row in reader}


    def all_student_ids(self):
        return self.data.keys()


    def student_name(self, sid):
        first = self.data[sid][self.header.index('First Name')]
        last = self.data[sid][self.header.index('Last Name')]
        return first + ' ' + last


    def problem_grade(self, sid, quiz_name, problem_name):
        name = 'Recitation {} [{}]'.format(
            quiz_name.split()[-1], problem_name.upper())

        if name in self.header:
            score = self.data[sid][self.header.index(name)]
            if not score:
                return 'S'
            elif float(score) == 0.0:
                return 'N'
            elif float(score) > 0.0:
                return 'Y'
            else:
                return '?'
        else:
            print('Warning, recitation problem', problem_name,
                   'not found for', quiz_name)
            return None
            

class prescription:
    def __init__(self, concepts, name = '', sid = '', quiz_name = ''):
        self.quiz_name = quiz_name
        self.student_name = name
        self.student_id = sid
        self.concepts = [prescription.concept(c[1:]) for c in concepts]

    def set_required_concepts(self, evaluation):
        for c, s in zip(self.concepts, evaluation.missed_concepts):
            if not s:
                for p in c.problems:
                    p.status = 'X'

    def update_from_gradescope(self, gradescope):
        for c in self.concepts:
            for p in c.problems:
                if not p.status == 'X':
                    p.status = gradescope.problem_grade(
                        self.student_id, self.quiz_name, p.name)

    class concept:
        def __init__(self, problems):
            self.problems = [prescription.problem(p) for p in problems]

    class problem:
        def __init__(self, name):
            self.name = name
            self.status = ''


def write_prescriptions(basename, prescriptions):
    cwd = os.getcwd()
    tmp = tempfile.TemporaryDirectory()
    os.chdir(tmp.name)

    fid = open(basename + '.tex', 'w')
    fid.write(header)

    for s in prescriptions:
        fid.write('\\newpage\n\\noindent')

        name, sid = s.student_name, s.student_id
        if name == '' and sid == '':
            name, sid = r'\quad', r'\quad'

        fid.write(page_header.format(name, s.quiz_name + ' prescriptions', sid))
        for i,c in enumerate(s.concepts):
            fid.write(concept_label.format(i+1))
            for p in c.problems:
                fid.write(box.format(p.name, p.status))
            fid.write(r'\\[0.5in]')
    fid.write('\end{document}')
    fid.flush()

    subprocess.call(['pdflatex', '-halt-on-error', basename], stdout=subprocess.DEVNULL)
    shutil.move(basename + '.pdf', os.path.join(cwd, basename + '.pdf'))
    os.chdir(cwd)


header = r'''\documentclass[12pt]{article}
\usepackage[letterpaper, margin=1in]{geometry}
\usepackage{tikz}
\usepackage{times}
\pagestyle{empty}
\newcommand\HUGE{\@setfontsize\Huge{38}{47}} 
\begin{document}'''

page_header = r'''
\begin{{minipage}}{{0.3\linewidth}}{}\end{{minipage}}
\begin{{minipage}}{{0.3\linewidth}}\centering {}\end{{minipage}}
\begin{{minipage}}{{0.3\linewidth}}
  \begin{{flushright}}{}\end{{flushright}}
\end{{minipage}}
\\[10mm]'''

concept_label = r'''
\begin{{tikzpicture}}
  \node[minimum width=0.75in, minimum height=1in] 
    {{ \textbf{{Concept {}}} }};
\end{{tikzpicture}}'''

box = r'''
\hspace{{0.5in}}\begin{{tikzpicture}}
  \node[draw=none, fill=cyan!30, align=left, 
        anchor=south west] at (-0.5in,-0.5in) {{\small{{{0}}}}};
  \node[draw, minimum width=1in, minimum height=1in, very thick] 
        {{\Huge{{{1}}}}};
\end{{tikzpicture}}'''


if __name__ == '__main__':
    main()
