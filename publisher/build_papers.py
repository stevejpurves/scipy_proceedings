#!/usr/bin/env python
from __future__ import unicode_literals

import os
import sys
import shutil
import subprocess
import io

import conf
import options
from build_paper import build_paper
from xreftools import XrefMeta
from doitools import make_doi

output_dir = conf.output_dir
build_dir  = conf.build_dir
bib_dir    = conf.bib_dir
pdf_dir    = conf.pdf_dir
toc_conf   = conf.toc_conf
proc_conf  = conf.proc_conf
dirs       = conf.dirs
xref_conf = conf.xref_conf
papers_dir = conf.papers_dir



def paper_stats(paper_id, start):
    stats = options.cfg2dict(os.path.join(output_dir, paper_id, 'paper_stats.json'))

    # Write page number snippet to be included in the LaTeX output
    pages = stats.get('pages', 1)
    stop = start + pages - 1

    print('"%s" from p. %s to %s' % (paper_id, start, stop))
    page_number_file = os.path.join(output_dir, paper_id, 'page_numbers.tex')

    with io.open(page_number_file, 'w', encoding='utf-8') as f:
        f.write('\setcounter{page}{%s}' % start)

    # Build table of contents
    stats.update({'page': {'start': start,
                           'stop': stop},
                  'paper_id': paper_id
                 })

    return stats, stop

if __name__ == "__main__":

    start = 0
    toc_entries = []

    options.mkdir_p(pdf_dir)
    basedir = os.path.join(os.path.dirname(__file__), '..')
    
    for paper_id in dirs:
        with options.temp_cd(basedir):
            build_paper(paper_id)

        # this has a sideffect: it creates page_numbers.tex 
        stats, start = paper_stats(paper_id, start + 1)
        toc_entries.append(stats)

        # This build step uses page_numbers.tex to set the starting page number
        with options.temp_cd(basedir):
            build_paper(paper_id)

        src_pdf = os.path.join(output_dir, paper_id, 'paper.pdf')
        dest_pdf = os.path.join(pdf_dir, paper_id+'.pdf')
        shutil.copy(src_pdf, dest_pdf)

    # load metadata
    toc = {'toc': toc_entries}
    scipy_entry = options.cfg2dict(proc_conf)

    # make dois for papers, then entire proceedings
    doi_prefix = scipy_entry["proceedings"]["xref"]["prefix"]
    for paper in toc_entries:
        paper['doi'] = make_doi(doi_prefix)
    scipy_entry['proceedings']['doi'] = make_doi(doi_prefix)

    # persist metadata
    options.dict2cfg(toc, toc_conf)
    options.dict2cfg(scipy_entry, proc_conf)

    # make crossref submission file
    xref = XrefMeta(scipy_entry, toc_entries)
    xref.make_metadata()
    xref.write_metadata(xref_conf)
