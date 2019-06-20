import unittest
from tcrdist import pairwise

class test_SequencePair(unittest.TestCase):

    # Tests gaps are introduced at sequence ends
    def test_align___0(self):
        # initialize SequencePair
        sp = pairwise.SequencePair("","")
        # call align function with specific input
        self.assertTrue(sp.align("AAA","GAAAGGG", open_penalty = 3 , extend_penalty = 3).traceback.query == '-AAA---')

    # Tests that the complete longer sequence is returned
    def test_align___1(self):
        self.assertTrue(pairwise.SequencePair("AACAGQASQGNLIF", "CAGQASQGNLIF").a1 == 'AACAGQASQGNLIF')

    # Tests that the shorter sequence is returned with gaps
    def test_align___2(self):
        self.assertTrue(pairwise.SequencePair("AACAGQASQGNLIF", "CAGQASQGNLIF").a2 == '--CAGQASQGNLIF')
    # Check that SequencePair enforces strings as inputs
    def test_SequencePair___returns_TypeError(self):
        with self.assertRaises(TypeError):
            pairwise.SequencePair("CAGQASQGNLIF", 1)

    def test_SequencePair___leninput1_lt_5_returns_distance_None(self):
        self.assertTrue(pairwise.SequencePair("CAGA", "CAGQASQGNLIF").hamming_distance == None)

    def test_SequencePair___leninput2_lt_5_returns_distance_None(self):
        self.assertTrue(pairwise.SequencePair("CAGQASQGNLIF", "CAGA").hamming_distance == None)

    def test_SequencePair___returns_hamming_distance0(self):
        self.assertTrue(pairwise.SequencePair("CAGQASQGNLIF", "CAGQASQGNLIF").hamming_distance == 0)

    def test_SequencePair___returns_hamming_distance0_083(self):
        self.assertTrue(round(pairwise.SequencePair("CAGQASQGNLIF", "CAGQRSQGNLIF").hamming_distance, 3) == 0.083)

    def test_SequencePair___returns_hamming_distance0_5(self):
        self.assertTrue(pairwise.SequencePair("AAAAAAAAAA", "AAAAA").hamming_distance == 0.5)


    def test_unpack_dd_to_kkv(self):
        dd = { 'A': {'A': 1, 'B': 2, 'C': 3},
               'B': {'B': 4, 'C': 5},
               'C': {'C': 6}
             }
        expected = {'key1': ['A', 'A', 'A', 'B', 'B', 'C'],
        'key2': ['A', 'B', 'C', 'B', 'C', 'C'],
        'value': [1, 2, 3, 4, 5, 6]}

        kkv = pairwise.unpack_dd_to_kkv(dd)
        self.assertTrue(kkv == expected)


    def test_apply_pairwise_distance___returns_hamming_values(self):
        """
        this test defines distance function within the test.
        It is explicit because the Hamming dist could be subbed with other Methods
        in the future.
        """
        sequences = ["CAGQASQGNLIF","CAGQASQGNLIF","CAGQASQGNLIFA", \
        "CAGQASQGNLIAA","CAGQASQGNLIFAAA","CAGQASQGNLIFAAAAA"]
        # define it explicitly here since this is test for hamming values
        def my_distance_wrapper(a,b):
            return(float(pairwise.SequencePair(a, b).hamming_distance) )

        d = pairwise.apply_pairwise_distance(sequences,
        pairwise_distance_function = my_distance_wrapper)

        kkv = pairwise.unpack_dd_to_kkv(dd = d)
        a = kkv['value'][0:5]
        b = [0.0, 0.13333333333333333, 0.23529411764705882, 0.15384615384615385, 0.0]
        # round to third decimal place
        self.assertTrue(map(lambda p: round(p, 3), a) == map(lambda p: round(p, 3), b) )

    def test_apply_pairwise_distance___returns_correct_key1(self):

        sequences = ["CAGQASQGNLIF","CAGQASQGNLIF","CAGQASQGNLIFA", \
        "CAGQASQGNLIAA","CAGQASQGNLIFAAA","CAGQASQGNLIFAAAAA"]
        d = pairwise.apply_pairwise_distance(sequences)
        kkv = pairwise.unpack_dd_to_kkv(dd = d)
        a = kkv['key1'][0:5]
        b =['CAGQASQGNLIAA','CAGQASQGNLIAA','CAGQASQGNLIAA','CAGQASQGNLIF','CAGQASQGNLIF']
        self.assertTrue(a == b)

    def test_apply_pairwise_distance___gets_correct_key2(self):
        sequences = ["CAGQASQGNLIF","CAGQASQGNLIF","CAGQASQGNLIFA", \
        "CAGQASQGNLIAA","CAGQASQGNLIFAAA","CAGQASQGNLIFAAAAA"]
        d = pairwise.apply_pairwise_distance(sequences)
        kkv = pairwise.unpack_dd_to_kkv(dd = d)
        a = kkv['key2'][0:5]
        b =['CAGQASQGNLIAA','CAGQASQGNLIFAAA','CAGQASQGNLIFAAAAA','CAGQASQGNLIAA','CAGQASQGNLIF']
        self.assertTrue(a == b)


if __name__ == '__main__':
    unittest.main()