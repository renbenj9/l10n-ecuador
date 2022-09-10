from odoo.tests import common


class TestModelA(common.TransactionCase):
    def test_some_action(self):
        record = self.env['account.journal'].create(
            {
                'name': 'nametest',
                'type': 'sale',
                'l10n_latam_use_documents': True,
                'l10n_latam_internal_type': 'invoice',
                'code': 'inv'
            })
        self.assertEqual(
            record.name,
            'nametest')
