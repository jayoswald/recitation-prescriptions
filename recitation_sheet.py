#!/usr/bin/env python3
import argparse
import tempfile
import os
import csv
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', nargs='+', action='append', dest='concepts',
                        help='rubric item numbers to use.')
    parser.add_argument('--evaluations', required=True,
                        help='Gradescope quiz evaluations csv file')
    parser.add_argument('--quiz', required=True, 
                        help='name of assignment, e.g. "Quiz 1"')
    args = parser.parse_args()
    build_prescriptions(args.evaluations, args.concepts, args.quiz)


def build_prescriptions(evaluation_path, concepts, quiz_name):
    evaluations = assignment_evaluations(evaluation_path)
    all_students = evaluations.students.keys()
    prescriptions = []
    for sid, student in evaluations.students.items():
        p = prescription(concepts, quiz_name, student.full_name(), sid)
        if sid in evaluations.students:
            p.set_required_concepts(evaluations.students[sid])
        prescriptions.append(p)
    short_name = quiz_name.replace(' ', '')
    write_prescriptions('prescriptions-' + short_name, prescriptions)
    # Writes a blank prescription for the Gradescope template.
    prescriptions = [prescription(concepts, quiz_name)]
    write_prescriptions('template-' + short_name, prescriptions)


class student:
    ''' Student information containing first, last and student id .'''
    def __init__(self, first, last, sid):
        self.name = (first, last)
        self.sid = sid
        self.missed_concepts = []

    def full_name(self):
        ''' Returns student full name as "First Last" '''
        return f'{self.name[0]} {self.name[1]}'


class assignment_evaluations:
    ''' Class that reads Gradescope assignment evaluation csv file. '''
    def __init__(self, path):
        self.students = {}
        self.read_csv(path)

    def read_csv(self, path):
        ''' Reads student grades from Gradescope CSV file for the quiz evaluation. '''
        try:
            reader = csv.reader(open(path))
        except IOError:
            print(f'Could not open evaluation file: {path}')
            return None
        header = next(reader)
        # Concept rubric titles must begin with 'concept ' (case insensitive).
        concept_indices = [i for i,h in enumerate(header) if h.lower().startswith('concept ')]
        i = header.index('Submission Time') + 1
        j = header.index('Adjustment')
        for row in reader:
            if not row or row[0] in 'Point Values Rubric Numbers Rubric Type':
                continue
            try:
                s = student(row[header.index('First Name')],
                            row[header.index('Last Name')],
                            row[header.index('SID')])
                s.missed_concepts = [row[i].lower() == 'true' for i in concept_indices]
                self.students[s.sid] = s
            except:
                print('Skipping invalid row\n', row)


class prescription:
    def __init__(self, concepts, quiz_name, name='', sid=''):
        self.quiz_name = quiz_name
        self.student_name = name
        self.student_id = sid
        self.concepts = [prescription.concept(c[1:]) for c in concepts]

    def set_required_concepts(self, evaluation):
        for c, s in zip(self.concepts, evaluation.missed_concepts):
            if not s:
                for p in c.problems:
                    p.status = 'X'

    class concept:
        def __init__(self, problems):
            self.problems = [prescription.problem(p) for p in problems]

    class problem:
        def __init__(self, name):
            self.name = name
            self.status = ''


def write_prescriptions(basename, prescriptions):
    ''' Generates a PDF file where each page is the prescription for 
    a student. '''
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
                if p.status == 'X':
                    fid.write(shaded_box.format(p.name, p.status))
                else:
                    fid.write(box.format(p.name, p.status))
            fid.write(r'\\[0.5in]')
    fid.write('\end{document}')
    fid.flush()
    subprocess.call(['pdflatex', '-halt-on-error', basename], stdout=subprocess.DEVNULL)
    os.replace(basename + '.pdf', os.path.join(cwd, basename + '.pdf'))
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
\end{{minipage}} \\[10mm]'''

concept_label = r'''
\begin{{tikzpicture}} \node[minimum width=0.75in, minimum height=1in] 
{{ \textbf{{Concept {}}} }};
\end{{tikzpicture}}'''

box = r'''
\hspace{{0.5in}}\begin{{tikzpicture}}
\node[draw=none, fill=green!30, align=left, 
anchor=south west] at (-0.5in,-0.5in) {{\small{{{0}}}}};
\node[draw, minimum width=1in, minimum height=1in, very thick] 
{{\Huge{{{1}}}}};
\end{{tikzpicture}}'''

shaded_box = r'''
\hspace{{0.5in}}\begin{{tikzpicture}}
\node[draw, minimum width=1in, minimum height=1in, very thick, fill=black!20] 
{{\Huge{{{1}}}}}; \node[draw=none, fill=red!30, align=left, 
anchor=south west] at (-0.5in,-0.5in) {{\small{{{0}}}}};
\node[draw, minimum width=1in, minimum height=1in, very thick,
anchor=center] at (0, 0) {{}};
\end{{tikzpicture}}'''


if __name__ == '__main__':
    main()

