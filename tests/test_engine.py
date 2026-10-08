import unittest

import numpy as np

from lca_tool.cli import read_bom
from lca_tool.engine import ModelError, solve, unit_factor


class TestEngine(unittest.TestCase):
    def test_classroom_two_process_example(self):
        A = [[1500, -3000], [-0.01, 0.1]]
        B = [[20, 10]]
        C = [[1]]
        s, g, h = solve(A, B, C, [1, 0])
        self.assertAlmostEqual(float(g[0]), 0.0175, places=12)
        self.assertAlmostEqual(float(h[0]), 0.0175, places=12)
        np.testing.assert_allclose(np.asarray(A) @ s, [1, 0], atol=1e-12)

    def test_singular_rejected(self):
        with self.assertRaises(ModelError):
            solve([[1, 1], [2, 2]], [[1, 1]], [[1]], [1, 0])

    def test_units(self):
        self.assertEqual(unit_factor("g", "kg"), 0.001)
        self.assertEqual(unit_factor("kWh", "MJ"), 3.6)
        with self.assertRaises(ModelError):
            unit_factor("USD", "kg")

    def test_bom(self):
        rows = read_bom(__import__("pathlib").Path("data/source/classroom/kettle-bom.csv"))
        self.assertAlmostEqual(sum(float(r["finished_mass_g"]) for r in rows), 860.8)


if __name__ == "__main__":
    unittest.main()
