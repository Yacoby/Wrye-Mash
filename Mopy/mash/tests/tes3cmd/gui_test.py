import unittest
import os

from ...tes3cmd import gui

class TestCleaner(unittest.TestCase):
    def getOutput(self, fn):
        c = gui.OutputParserMixin()
        fn = os.path.join(os.path.dirname(__file__), fn)
        return c.ParseOutput(open(fn).read()) 

    def testParse1(self):
        stats, output = self.getOutput('output.imclean.txt')

        expectedStats = ( 'duplicate object instance:     3\n'
                        + 'duplicate record:     2\n'
                        + 'redundant CELL.AMBI:     1\n'
                        + 'redundant CELL.WHGT:     2\n')

        expectedOutput = ( 'Cleaned duplicate record (BOOK): chargen statssheet\n'
                         + 'Cleaned duplicate record (DOOR): chargen exit door\n'
                         + 'Cleaned duplicate object instance (CharGen_cabindoor FRMR: 6034) from CELL: bitter coast region (-1, -9)\n'
                         + 'Cleaned duplicate object instance (Imperial Guard FRMR: 63431) from CELL: seyda neen (-2, -9)\n'
                         + 'Cleaned duplicate object instance (flora_bc_tree_02 FRMR: 24458) from CELL: seyda neen (-2, -9)\n'
                         + 'Cleaned redundant WHGT from CELL: imperial prison ship\n'
                         + 'Cleaned redundant AMBI,WHGT from CELL: seyda neen, census and excise office\n')
        self.assertEqual(stats, expectedStats)
        self.assertEqual(output, expectedOutput)

    def testParse2(self):
        stats, output = self.getOutput('output.tribclean.txt')
        
        expectedStats = ( 'Evil-GMST Bloodmoon:    61\n'
                        + 'Evil-GMST Tribunal:     5\n'
                        + 'duplicate record:  1479\n'
                        + 'junk-CELL:    14\n'
                        + 'redundant CELL.AMBI:     7\n'
                        + 'redundant CELL.WHGT:     7\n')

        self.assertEqual(stats, expectedStats)
        self.assertEqual(output, '')

    def testParse3(self):
        stats, output = self.getOutput('output.notmodified.txt')

        self.assertEqual(stats, 'Not modified')
        self.assertEqual(output, '')
