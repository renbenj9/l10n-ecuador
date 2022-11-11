import logging
from datetime import timedelta

from odoo import _
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .test_edi_common import TestL10nECEdiCommon

_logger = logging.getLogger(__name__)


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nClDte(TestL10nECEdiCommon):
    def test_l10n_ec_out_credit_note_configuration(self):
        # intentar validar una nota de credito sin tiene configurado correctamente los datos
        credit_note = self._l10n_ec_prepare_edi_credit_note()
        with self.assertRaises(UserError):
            credit_note.action_post()

    def test_l10n_ec_credit_note_wrong_certificate(self):
        """Test para firmar una factura con un certificado inválido"""
        self._setup_edi_company_ec()
        # Cambiar la contraseña del certificado de firma electrónica
        self.certificate.password = "invalid"
        credit_note = self._l10n_ec_prepare_edi_credit_note(auto_post=True)
        self.assertEqual("posted", credit_note.state)
        edi_doc = credit_note._get_edi_document(self.edi_format)
        with self.assertLogs(
            "odoo.addons.l10n_ec_account_edi.models.account_edi_format",
            level=logging.ERROR,
        ):
            edi_doc._process_documents_web_services(with_commit=False)
        self.assertFalse(edi_doc.edi_content)
        self.assertTrue(edi_doc.error)

    def test_l10n_ec_out_credit_note_sri(self):
        """Crear credit_note electrónica, con la configuración correcta"""
        # Configurar los datos previamente
        self._setup_edi_company_ec()
        # Compañia no obligada a llevar contabilidad
        self._l10n_ec_edi_company_no_account()
        credit_note = self._l10n_ec_prepare_edi_out_credit_note(
            use_payment_term=False, auto_post=True
        )
        # Añadir pago total a la factura
        self.generate_payment(
            credit_note_ids=credit_note.ids, journal=self.journal_cash
        )
        self.assertEqual(credit_note.payment_state, "paid")
        edi_doc = credit_note._get_edi_document(self.edi_format)
        edi_doc._process_documents_web_services(with_commit=False)
        self.assertEqual(credit_note.state, "posted")
        self.assertTrue(edi_doc.l10n_ec_xml_access_key)
        self.assertEqual(
            credit_note.l10n_ec_xml_access_key, edi_doc.l10n_ec_xml_access_key
        )
        self.assertEqual(credit_note.l10n_ec_authorization_date, False)
        # Agregar fecha de autorización y cambiar de estado
        edi_doc.write(
            {"l10n_ec_authorization_date": self.current_date, "state": "sent"}
        )
        self.assertEqual(
            credit_note.l10n_ec_authorization_date, edi_doc.l10n_ec_authorization_date
        )
        # Envio de email
        try:
            credit_note.action_credit_note_sent()
            mail_sended = True
        except UserError as e:
            _logger.warning(e.name)
            mail_sended = False
        self.assertTrue(mail_sended)
        # TODO: validar que se autorice en el SRI con una firma válida

    def test_l10n_ec_out_credit_note_back_sri(self):
        # Crear factura con una fecha superior a la actual
        # para que el sri me la devuelva y no se autoriza
        self._setup_edi_company_ec()
        credit_note = self._l10n_ec_prepare_edi_credit_note()
        credit_note.credit_note_date += timedelta(days=10)
        credit_note.action_post()
        edi_doc = credit_note._get_edi_document(self.edi_format)
        # Asignar el archivo xml básico para que lo encuentre y lo actualice
        edi_doc.attachment_id = self.attachment.id
        with self.assertLogs(
            "odoo.addons.l10n_ec_account_edi.models.account_edi_document",
            level=logging.INFO,
        ) as cm:
            edi_doc._process_documents_web_services(with_commit=False)
        self.assertEqual(cm.records[0].args[1], _("DEVUELTA"))
        self.assertEqual(credit_note.state, "posted")
        self.assertTrue(edi_doc.l10n_ec_xml_access_key)
        self.assertTrue(edi_doc.error)

    def test_l10n_ec_out_credit_note_with_foreign_client(self):
        # Factura con cliente sin identificación para que no se valide el XML
        self._setup_edi_company_ec()
        credit_note = self._l10n_ec_prepare_edi_credit_note(
            partner=self.partner_passport, auto_post=True
        )
        edi_doc = credit_note._get_edi_document(self.edi_format)
        # Error en el archivo xml
        with self.assertLogs(
            "odoo.addons.l10n_ec_account_edi.models.account_edi_format",
            level=logging.ERROR,
        ):
            edi_doc._process_documents_web_services(with_commit=False)
        self.assertIn(_("EDI Error creating xml file"), edi_doc.error)
        # Enviar contexto para presentar clave de acceso de xml erroneo
        credit_note.button_draft()
        credit_note.action_post()
        with self.assertLogs(
            "odoo.addons.l10n_ec_account_edi.models.account_edi_document",
            level=logging.ERROR,
        ):
            edi_doc.with_context(
                l10n_ec_xml_call_from_cron=True
            )._process_documents_web_services(with_commit=False)
            self.assertIn(_("ARCHIVO NO CUMPLE ESTRUCTURA XML"), edi_doc.error)

    def test_l10n_ec_out_credit_note_with_payments(self):
        """Crear factura electronica con 2 pagos"""
        self._setup_edi_company_ec()
        credit_note = self._l10n_ec_prepare_edi_credit_note(auto_post=True)
        # 2 Pagos para el total de la factura
        amount = credit_note.amount_total / 2
        # Pago con diario efectivo
        self.generate_payment(
            credit_note=credit_note.ids, journal=self.journal_cash, amount=amount
        )
        # Pago con diario banco por defecto
        self.generate_payment(credit_note_ids=credit_note.ids, amount=amount)
        edi_doc = credit_note._get_edi_document(self.edi_format)
        edi_doc._process_documents_web_services(with_commit=False)
        self.assertEqual(credit_note.state, "posted")
        self.assertEqual(credit_note.payment_state, "paid")
        self.assertTrue(edi_doc.l10n_ec_xml_access_key)

    def test_l10n_ec_credit_note_default_values_form(self):
        """Test prueba campos computados y valores por defecto
        en formulario de Factura de cliente"""
        self._setup_edi_company_ec()
        journal = self.journal_sale.copy({"name": "Invoices Journal"})
        self.assertTrue(self.AccountMove._fields["l10n_latam_internal_type"].store)
        form = self._l10n_ec_create_form_move(
            move_type="out_invoice", internal_type="invoice", partner=self.partner_cf
        )
        self.assertIn(form.journal_id, journal + self.journal_sale)
        self.assertRecordValues(
            form.journal_id,
            [
                {
                    "type": "sale",
                    "l10n_latam_use_documents": True,
                }
            ],
        )
        self.assertEqual(form.credit_note_filter_type_domain, "sale")
        self.assertEqual(journal + self.journal_sale, form.suitable_journal_ids[:])
        for journal in form.suitable_journal_ids[:]:
            self.assertRecordValues(
                journal,
                [
                    {
                        "type": "sale",
                        "l10n_latam_use_documents": True,
                    }
                ],
            )
        self.assertEqual(form.l10n_latam_document_type_id.internal_type, "credit_note")
        for document in form.l10n_latam_available_document_type_ids[:]:
            self.assertEqual(document.internal_type, "credit_note")
        credit_note = form.save()
        self.assertTrue(credit_note.l10n_latam_internal_type, "credit_note")

    def test_l10n_ec_credit_note_default_journal_form(self):
        """Test prueba en formulario de factura, sin diarios registrados"""
        self.journal_sale.unlink()
        credit_note_model = self.AccountMove.with_context(
            default_move_type="out_invoice", internal_type="credit_note"
        )
        with self.assertRaises(UserError):
            Form(credit_note_model)

    def test_l10n_ec_validate_lines_credit_note(self):
        """Validaciones de cantidad y valor total en 0 en lineas de facturas"""
        self._setup_edi_company_ec()
        credit_note = self._l10n_ec_prepare_edi_credit_note()
        with Form(credit_note) as form:
            with form.credit_note_line_ids.edit(0) as line:
                line.quantity = 0
        with self.assertRaises(UserError):
            credit_note.action_post()
