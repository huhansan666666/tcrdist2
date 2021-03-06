import os
import sys
import re
import random
import pandas as pd

from .paths import path_to_current_db_files
from . import util
from .all_genes import all_genes

from . import tcr_sampler
from .amino_acids import amino_acids
from .all_genes import all_genes

def find_cdr3_motif(
            clones_file             = "/Users/kmayerbl/PycharmProjects/tcrdist2/tcrdist2to3/mouse_pairseqs_v1_parsed_seqs_probs_mq20_clones.tsv",
            organism                = "mouse",
            epitopes                = ['PA'],
            chains                  = ['A','B'],
            all_tcrs                = None,         # set by self.generate_all_tcrs()
            ng_tcrs                 = None,
            min_count               = 10,
            max_ng_lines            = 5000000,
            max_motif_len           = 100,
            nsamples                = 25,
            min_expected            = .25,
            max_overlap             = 0.8,
            max_useful_expected     = 1.0,
            chi_squared_threshold   = 50.0,
            chi_squared_threshold_for_seeds = 20.0,
            min_chi_squared_increase = 25.0,
            min_extended_count_ratio = 0.6,
            use_fake_seqs            = False,
            big                      = True, # the assert statement in legacy code suggests that this must be set to True
            constant_seed            = False,
            force_random_len         = False,
            verbose                  = True,
            nofilter                 = False,
            very_verbose             = False,
            test_random              = False,
            hacking                  = False,
            unmask                   = True,
            use_groups               = True,
            begin                    = '^',
            end                      = '$',
            X                        = '[A-Z]',
            dot                      = '.',
            pseudocount              = 0.0):
    """
    find_cdr3_motif preserves the behavior of the motif finder in TCRdist v1.

    It is computationally expensive and may take up to 10 minutes to an hour to complete.

    """

    if constant_seed:
        random.seed(1)
    assert big, "big must be True to Match tcrdist v1 behavior"
    assert unmask, "unmask must be True to match tcrdist v1 behavior"
    assert use_groups, 'use_groups must be True to match tcrdist va behavior'

    groups = dict( zip( amino_acids, amino_acids ) )
    groups['k'] = '[KR]'
    groups['d'] = '[DE]'
    groups['n'] = '[NQ]'
    groups['s'] = '[ST]'
    groups['f'] = '[FYWH]'
    groups['a'] = '[AGSP]'
    groups['v'] = '[VILM]'

    if not use_groups:
        groups = dict( zip( amino_acids, amino_acids ) )

    groups[begin] = begin
    groups[end  ] = end

    if hacking:
        groups = {'E':'E','F':'F',begin:begin}


    def extend_motif( oldmotif, oldshowmotif, old_chi_squared, seqs, seq_indices, random_seqs, random_seq_indices,
                      ng_segs, ng_seq_indices, all_good_motifs, all_seen, my_max_motif_len, best_motifs ):
        """
        Recursive function invoked by find_cdr3_motif(). It update variable lists in place.

        """
        #global chi_squared_threshold

        old_count = len(seq_indices)

        normal_pad = 3
        term_pad = 4

        ## sort them in order of chisq
        extensions = []

        random_ratio = float( len(random_seqs) ) / len(seqs)
        ng_ratio = float( len(ng_seqs) ) / len(seqs)

        for c in groups:
            if c==begin or c==end:
                pad = term_pad
            else:
                pad = normal_pad
            L = len(oldmotif)+2*pad
            assert len(oldshowmotif) == len(oldmotif)
            for cpos in range(L):
                if cpos>=pad and cpos <L-pad and oldmotif[cpos-pad] != X: continue
                if c==begin and cpos>=pad:continue
                if c==end and cpos<L-pad:continue
                ## new motif?
                motif = [X]*pad + oldmotif + [X]*pad
                showmotif = [dot]*pad + oldshowmotif + [dot]*pad
                motif[cpos] = groups[c]
                showmotif[cpos] = c
                while motif[0] == X:
                    motif = motif[1:]
                    showmotif = showmotif[1:]
                while motif[-1] == X:
                    motif = motif[:-1]
                    showmotif = showmotif[:-1]

                prog = re.compile(''.join(motif))
                count=0
                for ii in seq_indices:
                    if prog.search(seqs[ii]):
                        count += 1
                if count<min_count or count < min_extended_count_ratio * old_count:
                    continue

                best_possible_chi_squared = (count-min_expected)**2/min_expected
                if best_possible_chi_squared < old_chi_squared+min_chi_squared_increase:
                    continue

                random_count=pseudocount
                for ii in random_seq_indices:
                    if prog.search(random_seqs[ii]):
                        random_count += 1
                ng_count=pseudocount
                for ii in ng_seq_indices:
                    if prog.search(ng_seqs[ii]):
                        ng_count += 1
                expected = float(random_count)/random_ratio
                ng_expected = float(ng_count)/ng_ratio

                expected_for_chi_squared = max( max( min_expected, expected ), ng_expected )
                chi_squared = (count-expected_for_chi_squared)**2/expected_for_chi_squared

                if count and count > 2*expected and count > 2*ng_expected and \
                   chi_squared > old_chi_squared+min_chi_squared_increase:
                    motif_len = len(showmotif) - showmotif.count('.')

                    if motif_len in all_seen and ''.join(showmotif) in all_seen[motif_len]:
                        if very_verbose:
                            print('repeat',motif_len,''.join(showmotif))
                        continue

                    if motif_len not in all_seen: all_seen[motif_len] = set()
                    all_seen[motif_len].add( ''.join(showmotif))

                    ### what we will eventually add to all_good_motifs
                    info_tuple = ( chi_squared, motif_len, count, -1*expected, -1*ng_expected, motif, showmotif )

                    extensions.append( ( info_tuple, prog ) )

        extensions.sort()
        extensions.reverse() ## do them in decreasing order of chi_squared

        for ( info_tuple, prog ) in extensions:
            ( chi_squared, motif_len, count, negexpected, neg_ng_expected, motif, showmotif ) = info_tuple

            ## do we really want to pursue this guy?
            new_seq_indices = []
            for ii in seq_indices:
                if prog.search(seqs[ii]):
                    new_seq_indices.append(ii)
            new_seq_indices = tuple( new_seq_indices )

            if count not in best_motifs: best_motifs[count] = {}

            best_chi_squared = best_motifs[count].get(new_seq_indices,0)

            if chi_squared<best_chi_squared:
                if very_verbose:
                    print( 'worse motif:',chi_squared,best_chi_squared,''.join(showmotif))
                continue

            best_motifs[count][new_seq_indices] = chi_squared


            if very_verbose:
                print( 'NEW {:3d} {:5.2f} {:5.2f} {:8.1f} {:15s} {:6d} {:4s} {}'\
                    .format( count, -1*negexpected, -1*neg_ng_expected,
                             chi_squared, ''.join(showmotif), len(all_seen[motif_len]),
                             epitope, ab ))
                sys.stdout.flush()


            all_good_motifs.append( info_tuple )

            if motif_len < my_max_motif_len:

                new_random_seq_indices = []
                for ii in random_seq_indices:
                    if prog.search(random_seqs[ii]):
                        new_random_seq_indices.append(ii)

                new_ng_seq_indices = []
                for ii in ng_seq_indices:
                    if prog.search(ng_seqs[ii]):
                        new_ng_seq_indices.append(ii)

                extend_motif( motif, showmotif, chi_squared, seqs, new_seq_indices,
                              random_seqs, new_random_seq_indices, ng_seqs, new_ng_seq_indices,
                              all_good_motifs, all_seen, my_max_motif_len, best_motifs )

    output_strings = [] # KMB - THIS IS FOR PANDAS OUTPUT
    output_lists = []
    for epitope in epitopes:
        #if epitope != 'NP': continue

        for ab in chains:
            if verbose:
                pass
                #Log(epitope+' '+ab)

            tcrs = all_tcrs[epitope]

            seqs = []
            seqinfos = []
            random_seqs = []
            ng_seqs = [] ## nextgen

            for ( va, ja, vb, jb, cdr3a, cdr3b, cdr3a_masked, cdr3b_masked, va_rep, ja_rep, vb_rep, jb_rep ) \
                in all_tcrs[epitope]:
                if ab=='A':
                    v_gene, j_gene, cdr3_masked, v_rep, j_rep = va, ja, cdr3a_masked, va_rep, ja_rep
                else:
                    v_gene, j_gene, cdr3_masked, v_rep, j_rep = vb, jb, cdr3b_masked, vb_rep, jb_rep

                seqs.append( cdr3_masked )
                seqinfos.append( (v_rep,j_rep ) )

                if force_random_len:
                    force_aa_length = len(cdr3_masked)
                else:
                    force_aa_length = 0

                samples = tcr_sampler.sample_tcr_sequences( organism, nsamples+use_fake_seqs, v_gene, j_gene,
                                                            force_aa_length = force_aa_length,
                                                            in_frame_only = True, no_stop_codons = True,
                                                            max_tries = 10000000, include_annotation = True )

                assert unmask ## deleted the relevant code
                for nucseq,protseq,anno in samples:
                    random_seqs.append( protseq )

                ## now add some nextgen seqs
                if v_rep in ng_tcrs[ab] and j_rep in ng_tcrs[ab][v_rep]:
                    ngl = ng_tcrs[ab][v_rep][j_rep]
                    for (cdr3,cdr3_nucseq) in random.sample( ngl, min(nsamples,len(ngl)) ):
                        ng_seqs.append( cdr3 )

            if verbose:
                pass
                #Log( '{} {} nseqs {} nrand {} nnextgen {}'\
                     #.format( epitope,ab,len(seqs),len(random_seqs),len(ng_seqs)))

            assert len(random_seqs) == nsamples * len(seqs)

            random_ratio = float( len(random_seqs) ) / len(seqs)
            ng_ratio = float( len(ng_seqs) ) / len(seqs)

            all_good_motifs = []
            all_seen = {}
            best_motifs = {}

            ## find the seed motifs
            seed_motifs = []

            #print ('\n'+ab+'seq: ').join(seqs)
            if very_verbose:
                print ( 'numseqs:',len(seqs),'numrandseqs:',len(random_seqs))

            for a in groups:
                if a== end: continue
                for b in groups:
                    if b == begin: continue
                    if a==begin or b==end:
                        maxsep = 7
                    else:
                        maxsep = 5
                    for sep in range(maxsep+1):
                        motif = [ groups[a] ]+ [X]*sep + [groups[b]]
                        showmotif = [a]+[dot]*sep+[b]

                        ## get counts for motif in random and true seqs
                        prog = re.compile(''.join(motif))
                        count=0
                        for seq in seqs:
                            if prog.search(seq):
                                count += 1
                        if count<min_count: continue
                        random_count=pseudocount
                        for seq in random_seqs:
                            if prog.search(seq):
                                random_count += 1
                        ng_count=pseudocount
                        for seq in ng_seqs:
                            if prog.search(seq):
                                ng_count += 1
                        expected = float(random_count)/random_ratio
                        ng_expected = float(ng_count)/ng_ratio

                        expected_for_chi_squared = max( max( min_expected, expected ), ng_expected )
                        chi_squared = (count-expected_for_chi_squared)**2/expected_for_chi_squared

                        if count and count >= min_count and count > 2*expected and count>2*ng_expected:

                            if chi_squared > chi_squared_threshold_for_seeds:
                                if very_verbose:
                                    print( 'newseed:',''.join(showmotif),chi_squared,expected,ng_expected)
                                    sys.stdout.flush()
                                motif_len = 2
                                info_tuple = ( chi_squared, motif_len, count, -1*expected, -1*ng_expected, motif, showmotif )

                                seed_motifs.append( ( info_tuple, prog ) )

            seed_motifs.sort()
            seed_motifs.reverse()

            if verbose:
                pass
                #Log( '{} {} nseeds {}'.format( epitope,ab,len(seed_motifs)))

            for ( info_tuple, prog ) in seed_motifs:
                ( chi_squared, motif_len, count, negexpected, neg_ng_expected, motif, showmotif ) = info_tuple

                #print 'seed:',chi_squared,''.join(showmotif),negexpected

                ## start recursive function call
                seq_indices = []
                for ii,seq in enumerate(seqs):
                    if prog.search(seq):
                        seq_indices.append(ii)
                random_seq_indices = []
                for ii,seq in enumerate(random_seqs):
                    if prog.search(seq):
                        random_seq_indices.append(ii)
                ng_seq_indices = []
                for ii,seq in enumerate(ng_seqs):
                    if prog.search(seq):
                        ng_seq_indices.append(ii)
                motif_len = len(showmotif) - showmotif.count('.')
                assert motif_len == 2 #duh

                if chi_squared > chi_squared_threshold:
                    all_good_motifs.append( ( chi_squared, 2, count, negexpected, neg_ng_expected, motif, showmotif ) )

                if motif_len not in all_seen: all_seen[motif_len] = set()
                all_seen[motif_len].add( ''.join(showmotif))

                extend_motif( motif, showmotif, chi_squared, seqs, seq_indices,
                              random_seqs, random_seq_indices, ng_seqs, ng_seq_indices,
                              all_good_motifs, all_seen, max_motif_len,
                              best_motifs )



            all_good_motifs.sort()
            all_good_motifs.reverse()

            if verbose:
                pass
                #Log( '{} {} ngood {}'.format( epitope,ab,len(all_good_motifs)))

            ## now we kill redundant guys
            seen = []

            for ( chi_squared, nfixed, count, negexpected, neg_ng_expected, motif, showmotif ) in all_good_motifs:
                expected = -1*negexpected
                ng_expected = -1*neg_ng_expected
                prog = re.compile(''.join(motif))
                indices = []
                for ii,seq in enumerate(seqs):
                    if prog.search(seq):
                        indices.append( ii )
                assert len(indices)==count

                ## check if we're redundant
                redundant = False
                max_coverage = 0
                max_cover = 0
                for iold, (old_indices,old_expected) in enumerate(seen):
                    nseen = 0
                    for i in indices:
                        if i in old_indices:
                            nseen += 1
                    my_coverage = float(nseen)/count
                    their_coverage = float(nseen)/len(old_indices)
                    if my_coverage > max_coverage:
                        max_coverage = my_coverage
                        max_cover = iold
                    if my_coverage >= max_overlap and their_coverage >= max_overlap:
                        ## give us a pass if their expected was above threshold while ours is below:
                        if max(expected,ng_expected) < max_useful_expected and old_expected > max_useful_expected:
                            pass
                        else:
                            redundant = True
                            break
                if redundant and not nofilter:
                    #print 'redundant:',showmotif,epitope,ab
                    continue
                seen.append( ( set(indices), max(expected,ng_expected) ) )

                v_counts = {}
                j_counts = {}
                for i in indices:
                    v_rep,j_rep = seqinfos[i]
                    v_counts[v_rep] = v_counts.get(v_rep,0)+1
                    j_counts[j_rep] = j_counts.get(j_rep,0)+1
                vl = [(y,x) for x,y in v_counts.items()]
                jl = [(y,x) for x,y in j_counts.items()]
                vl.sort() ; vl.reverse()
                jl.sort() ; jl.reverse()
                vtags = ','.join( ['{}:{}'.format(y,x) for x,y in vl ][:3] )
                jtags = ','.join( ['{}:{}'.format(y,x) for x,y in jl ][:3] )


                print('MOTIF\t{:4d}\t{:9.4f}\t{:9.4f}\t{:8.1f}\t{:2d}\t{:15s}\t{:4d}\t{:4d}\t{:3d}\t{:4s}\t{}\t{}\t{}\t{}'\
                    .format( count, expected, ng_expected, chi_squared, nfixed, ''.join(showmotif), len(seen),
                             max_cover+1, int(100*max_coverage),
                             epitope, ab, len(seqs), vtags, jtags ))

                sys.stdout.flush()

                string_to_output = 'MOTIF\t{:4d}\t{:9.4f}\t{:9.4f}\t{:8.1f}\t{:2d}\t{:15s}\t{:4d}\t{:4d}\t{:3d}\t{:4s}\t{}\t{}\t{}\t{}'\
                    .format( count, expected, ng_expected, chi_squared, nfixed, ''.join(showmotif), len(seen),
                             max_cover+1, int(100*max_coverage),
                             epitope, ab, len(seqs), vtags, jtags)

                list_to_output = ['MOTIF', count, expected, ng_expected, chi_squared, nfixed, ''.join(showmotif), len(seen),
                         max_cover+1, int(100*max_coverage),
                         epitope, ab, len(seqs), vtags, jtags]


                output_strings.append(string_to_output)
                output_lists.append(list_to_output)
                
    cnames = ["file_type","count", "expect_random","expect_nextgen", "chi_squared", "nfixed","showmotif", "num", "othernum", "overlap", "ep", "ab", "nseqs", "v_rep_counts", "j_rep_counts"]
    #column_names =['MOTIF','count', 'expected', 'ng_expected', 'chi_squared', 'nfixed', 'motif', 'len_seen', 'max_cover', 'max_coverage', 'epitope', 'chain', 'len_seqs','vtags','jtags']
    return pd.DataFrame(output_lists, columns = cnames )
