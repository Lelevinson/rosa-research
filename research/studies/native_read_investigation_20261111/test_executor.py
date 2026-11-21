import unittest
from unittest.mock import patch
from executor import AIMD, command, normalize, run_batch

class ExecutorTests(unittest.TestCase):
    def test_denies_mutators_injection_and_relative_names(self):
        for family, name in [('set','/x'),('service','/x;true'),('node','--help'),('topic','x')]:
            with self.assertRaises(ValueError):
                command(family,name)

    def test_all_arguments_validated_before_any_dispatch(self):
        with patch('executor.read_one') as reader:
            with self.assertRaises(ValueError):
                run_batch('node',['/ok','/bad name'],'fixed4')
            reader.assert_not_called()

    def test_aimd_drop_rtt_and_app_limited_guard(self):
        limiter=AIMD()
        limiter.limit=4
        limiter.update(.1,False,1)
        self.assertEqual(limiter.limit,4)
        limiter.update(6,False,4)
        self.assertEqual(limiter.limit,3)
        limiter.update(.1,True,3)
        self.assertEqual(limiter.limit,2)
        limiter.update(.1,False,2)
        self.assertEqual(limiter.limit,3)

    def test_comparison_preserves_duplicate_lines(self):
        self.assertNotEqual(normalize('a\na'),normalize('a'))

if __name__=='__main__':
    unittest.main()
