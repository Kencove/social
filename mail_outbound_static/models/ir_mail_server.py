# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.tools.mail import email_split


class IrMailServer(models.Model):

    _inherit = "ir.mail_server"

    smtp_from = fields.Char(
        string="Email From", help="Set this in order to email from a specific address."
    )

    @api.model
    def send_email(
        self, message, mail_server_id=None, smtp_server=None, *args, **kwargs
    ):

        # Replicate logic from core to get mail server
        mail_server = None
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
        elif not smtp_server:
            mail_server = self.sudo().search([], order="sequence", limit=1)

        division_domain = False

        message_origin = message.get("X-Odoo-Objects")
        if message_origin:
            record_object, record_id = (
                message_origin.split("-")
                if len(message_origin.split("-")) == 2
                else [False, False]
            )
            if record_object and "division_id" in self.env[record_object]:
                record = self.env[record_object].browse(int(record_id))
                if record and record.division_id and record.division_id.mail_domain:
                    division_domain = record.division_id.mail_domain

        catch_all_domain = (
            self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        )
        from_address_domain = email_split(message["From"])[0].split("@")[1]

        if (
            mail_server
            and mail_server.smtp_from
            and (division_domain or catch_all_domain) != from_address_domain
        ):
            split_from = message["From"].rsplit(" <", 1)
            if len(split_from) > 1:
                email_from = "{} <{}>".format(split_from[0], mail_server.smtp_from)
            else:
                email_from = mail_server.smtp_from

            message.replace_header("From", email_from)
            bounce_alias = (
                self.env["ir.config_parameter"].sudo().get_param("mail.bounce.alias")
            )
            if not bounce_alias:
                # then, bounce handling is disabled and we want
                # Return-Path = From
                if "Return-Path" in message:
                    message.replace_header("Return-Path", email_from)
                else:
                    message.add_header("Return-Path", email_from)

        return super(IrMailServer, self).send_email(
            message, mail_server_id, smtp_server, *args, **kwargs
        )
