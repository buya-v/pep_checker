from odoo.tests.common import TransactionCase

# Run tests only after module is installed
at_install = False
post_install = True

class TestPEP(TransactionCase):
    def setUp(self):
        super().setUp()
        self.PEP = self.env['pep.person']

    def test_unique_name_dob(self):
        vals = {'name': 'John Doe', 'date_of_birth': '1970-01-01'}
        # first create should succeed
        self.PEP.create(vals)
        # second create with same name+dob should fail due to SQL constraint
        with self.assertRaises(Exception):
            self.PEP.create(vals)
