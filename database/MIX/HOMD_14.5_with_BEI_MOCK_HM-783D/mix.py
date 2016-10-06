import argparse
import re
from itertools import islice
from collections import OrderedDict
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from termcolor import colored

parser = argparse.ArgumentParser(description='Mix HOMD/GG database with Mock database')
parser.add_argument('--hg_fa_fp', help='HOMD/GG fasta file', required=True)
parser.add_argument('--hg_tax_fp', help='HOMD/GG taxonomy file', required=True)
parser.add_argument('--mock_fa_fp', help='Mock fasta file', required=True)
parser.add_argument('--mock_tax_fp', help='Mock taxonomy file', required=True)
parser.add_argument('-o', '--output_dir', help='Ouput dir', default='./')
args = parser.parse_args()


def match_taxonomy(hg_taxa, mock_taxa):
    # generate hg taxa set
    hg_taxa_set = set()
    with open(hg_taxa) as f:
        for line in f:
            taxa = line.strip().split('\t')[1]
            # full taxa to binomial name
            hg_taxa_set.add((' '.join(taxa.split(' ')[-2:])))

    # generate mock binomial name
    mock_taxa_set = set()
    with open(mock_taxa) as f:
        for line in f:
            taxa = line.strip().split('\t')[1]
            mock_taxa_set.add((' '.join(taxa.split(' ')[-2:])))

    # fuzzy search each mock binomial name 
    convert_map = {}
    for x in sorted(list(mock_taxa_set)):
        print(x)
        m = process.extract(x, hg_taxa_set, limit=3)
        candidates = OrderedDict(zip(list(range(len(m) + 1)), 
                                     [('treat as new taxonomy label', 0)] + m))
        if m[0][1] == 100:
            print(colored('perfect match found, coutinue to next...', 'green'))
            convert_map[x] = 'k__xxx; p__xxx; c__xxx; o__xxx; f__xxx; {}'.format(x)
        else:
            ans = None
            while ans is None:
                for key, value in candidates.items():
                    print('{}: {}'.format(key, value[0]))
                try:
                    ans = int(input(colored('No perfect match found, please enter selection:\n',
                                            'yellow')))
                    if ans not in list(range(len(m) + 1)):
                        raise ValueError()
                    elif ans == 0:
                        print(colored('treat as new taxonomy label: {}'.format(x), 'green'))
                    else:
                        convert_map[candidates[ans][0]] = 'k__xxx; p__xxx; c__xxx; o__xxx; f__xxx; {}'.format(x)
                        print(colored('map "{}" -> "{}"'.format(candidates[ans][0], x), 'green'))
                except ValueError:
                    print(colored('Unknow index, please try again...', 'red'))
                    print(x)
                    ans = None
    return convert_map

def feed_fa(input_fp, fa, prefix):
    with open(input_fp) as f:
        while True:
            next_n = list(islice(f, 2))
            if not next_n:
                break
            read_id = prefix + next_n[0].strip()[1:]
            read = next_n[1].strip()
            fa.write('>{}\n{}\n'.format(read_id, read))

def feed_tax(input_fp, tax, prefix):
    global convert_map
    with open(input_fp) as f:
        for line in f:
            index, taxa = line.strip().split('\t')
            if prefix == 'HG_':
                binomial_name = ' '.join(taxa.split(' ')[-2:])
                if binomial_name in convert_map:
                    tax.write('{}\t{}\n'.format(prefix + index, convert_map[binomial_name]))
                else:
                    tax.write('{}\t{}\n'.format(prefix + index, taxa))
            elif prefix == 'Mock_':
                tax.write('{}\t{}\n'.format(prefix + index, taxa))
            else:
                raise Exception('No matched prefix')

convert_map = match_taxonomy(args.hg_tax_fp, args.mock_tax_fp)
print()
for key, value in convert_map.items():
    print("{} -> \n{}".format(key, value))
with open(args.output_dir + '/mix.fa', 'w') as fa, \
     open(args.output_dir + '/mix.tax', 'w') as tax:

     feed_fa(args.hg_fa_fp, fa, prefix='HG_')
     feed_fa(args.mock_fa_fp, fa, prefix='Mock_') 
     feed_tax(args.hg_tax_fp, tax, prefix='HG_')
     feed_tax(args.mock_tax_fp, tax, prefix='Mock_')
